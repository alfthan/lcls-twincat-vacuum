"""Cycle-accurate simulation of the FB_VRC_DA override section after the task #345 change.

Mirrors scan order exactly:
  safe-condition resets -> release when override mode off -> tonOvrd qualification
  -> duration expiry (with timer resets) -> output evaluation -> fault path
TON semantics: IN FALSE resets Q/ET in the same call.
"""
CYCLE = 0.01            # 10 ms task
T_OVRD = 10.0           # tOvrd
T_OVRD_MAX = 30 * 60.0  # tOvrdMaxDuration


class TON:
    def __init__(self, pt):
        self.pt = pt
        self.q = False
        self.et = 0.0
        self.start = None

    def __call__(self, in_, now):
        if not in_:
            self.q = False
            self.et = 0.0
            self.start = None
            return
        if self.start is None:
            self.start = now
        self.et = now - self.start
        self.q = self.et >= self.pt - 1e-9


class VrcDaOverride:
    """The override-relevant part of FB_VRC_DA (pv_xOPN_SW / pv_xCLS_SW held FALSE)."""

    def __init__(self):
        self.tonDelOK = TON(T_OVRD)
        self.tonDelCLS = TON(T_OVRD)
        self.tonOvrd = TON(T_OVRD)
        self.tonOvrdMax = TON(T_OVRD_MAX)
        self.log = []
        self.ovrd_opn = False
        self.ovrd_cls = False

    def scan(self, now, i_OPN_OK, i_CLS_OK, i_xOverrideMode, ovrd_opn, ovrd_cls):
        # EPICS writes the io field only on a put; None means "leave the retained value alone"
        if ovrd_opn is not None:
            self.ovrd_opn = ovrd_opn
        if ovrd_cls is not None:
            self.ovrd_cls = ovrd_cls

        # --- safe-condition reset, open direction (level triggered) ---
        self.tonDelOK(i_OPN_OK, now)
        if self.tonDelOK.q and self.ovrd_opn:
            self.ovrd_opn = False
            self.log.append((round(now, 3), 'open override cleared, open permit restored'))

        # --- safe-condition reset, close direction ---
        self.tonDelCLS(i_CLS_OK, now)
        if self.tonDelCLS.q and self.ovrd_cls:
            self.ovrd_cls = False
            self.log.append((round(now, 3), 'close override cleared, close permit restored'))

        # --- release while the plant-wide override mode is off ---
        if not i_xOverrideMode:
            self.ovrd_opn = False
            self.ovrd_cls = False

        # --- qualification timer ---
        self.tonOvrd(self.ovrd_opn or self.ovrd_cls, now)

        # --- duration expiry ---
        self.xOvrdInEffect = self.tonOvrd.q and i_xOverrideMode
        self.tonOvrdMax(self.xOvrdInEffect, now)
        if self.tonOvrdMax.q:
            self.xOvrdInEffect = False
            if self.ovrd_opn or self.ovrd_cls:
                self.ovrd_opn = False
                self.ovrd_cls = False
                self.tonOvrd(False, now)        # reset: a still-written request must re-qualify
                self.tonOvrdMax(False, now)     # reset: ... with a full duration window
                self.log.append((round(now, 3), 'override expired after configured duration'))

        # --- outputs ---
        self.q_xOPN_DO = self.xOvrdInEffect and self.ovrd_opn
        self.q_xCLS_DO = self.xOvrdInEffect and self.ovrd_cls
        return self.q_xOPN_DO, self.q_xCLS_DO


def run(scenario, duration, fb=None):
    fb = fb or VrcDaOverride()
    out = (False, False)
    t = 0.0
    while t < duration:
        opn_ok, cls_ok, mode, req_opn, req_cls = scenario(t, fb)
        out = fb.scan(t, opn_ok, cls_ok, mode, req_opn, req_cls)
        t += CYCLE
    return fb, out


def report(title, fb, out, duration):
    print('--- %s (state at t=%.0fs)' % (title, duration))
    print('    q_xOPN_DO=%s q_xCLS_DO=%s pv_xOvrdOpn=%s pv_xOvrdCls=%s'
          % (out[0], out[1], fb.ovrd_opn, fb.ovrd_cls))
    print('    clear events: %d' % len(fb.log))
    for ts, msg in fb.log[:4]:
        print('      t=%.2fs %s' % (ts, msg))


# 1. FORCE_OPN written once while the open permit is withheld: qualified, drives open,
#    self-clears after the configured 30 min even though nobody clears it.
def s1(t, fb):
    return (False, True, True, (True if t < 0.02 else None), None)


fb, out = run(s1, 31 * 60)
report('1. request written once, permit never restored', fb, out, 31 * 60)
assert [m for _, m in fb.log] == ['override expired after configured duration'], fb.log
assert 1805 < fb.log[0][0] < 1815, fb.log[0][0]
assert not out[0] and not fb.ovrd_opn, 'output still driven after expiry'

# 2. Override open, permit restored at 60 s -> clears 10 s later (documented de-qualification).
def s2(t, fb):
    return (t >= 60, True, True, (True if t < 0.02 else None), None)


fb, out = run(s2, 120)
report('2. permit restored at 60 s', fb, out, 120)
assert [m for _, m in fb.log] == ['open override cleared, open permit restored'], fb.log
assert 69 < fb.log[0][0] < 72, fb.log[0][0]
assert not out[0]

# 3. A permit blip shorter than tOvrd must not clear the override.
def s3(t, fb):
    return (70 <= t < 74, True, True, (True if t < 0.02 else None), None)


fb, out = run(s3, 100)
report('3. 4 s permit blip', fb, out, 100)
assert not fb.log, 'a short permit blip cleared the override'
assert out[0], 'qualified override no longer drives the output'

# 4. Qualification: the override must not act before tOvrd (10 s).
fb = VrcDaOverride()
first_open = None
t = 0.0
while t < 20:
    o = fb.scan(t, False, True, True, True, False)
    if o[0] and first_open is None:
        first_open = t
    t += CYCLE
print('--- 4. first cycle with q_xOPN_DO TRUE: t=%.2fs' % first_open)
assert first_open is not None and 9.9 <= first_open <= 10.2, first_open

# 5. Close override symmetric, cleared by the close permit.
def s5(t, fb):
    return (True, t >= 30, True, None, (True if t < 0.02 else None))


fb, out = run(s5, 60)
report('5. close override, close permit restored at 30 s', fb, out, 60)
assert fb.log and fb.log[-1][1] == 'close override cleared, close permit restored', fb.log
assert not out[1]

# 6. Stale request released when the plant-wide override mode drops.
def s6(t, fb):
    return (False, True, t < 30, (True if t < 0.02 else None), None)


fb, out = run(s6, 60)
report('6. override mode dropped at 30 s', fb, out, 60)
assert not fb.ovrd_opn and not fb.ovrd_cls
assert not out[0] and not out[1]

# 7. Pathological case: EPICS keeps re-writing the request every scan. The override must still
#    expire (fresh 10 s qualification + 30 min window per attempt) and must not flood the log.
def s7(t, fb):
    return (False, True, True, True, False)


fb, out = run(s7, 65 * 60)
report('7. request re-written every scan, permit never restored', fb, out, 65 * 60)
expiries = [ts for ts, m in fb.log if m == 'override expired after configured duration']
assert len(expiries) == 2, expiries
assert 1805 < expiries[0] < 1815 and 3615 < expiries[1] < 3625, expiries
# The re-written request legitimately starts a new (requalified) window, but the log must stay quiet
assert len(fb.log) == 2

print('\nALL SCENARIOS PASSED')
