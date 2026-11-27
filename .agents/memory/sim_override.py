"""Cycle-level simulation of the FB_VRC_NO_FFO close/override logic after the fix.

Mirrors the ST statements one-for-one so the safety properties can be checked
without a TwinCAT runtime.
"""


class TON:
    def __init__(self):
        self.q = False
        self.et = 0

    def __call__(self, in_, pt, dt):
        if in_:
            self.et = min(self.et + dt, pt)
            self.q = self.et >= pt
        else:
            self.et = 0
            self.q = False
        return self.q


class RTRIG:
    def __init__(self):
        self.m = False
        self.q = False

    def __call__(self, clk):
        self.q = clk and not self.m
        self.m = clk
        return self.q


class Valve:
    def __init__(self, t_ovrd=10_000, t_ovrd_max=300_000):
        self.pv_xCLS_SW = False          # EPICS CLS_SW
        self.pv_xOvrdCls = False         # EPICS FORCE_CLS
        self.xCLS_OK = False             # close interlock (i_xExtILK_OK)
        self.q_xCLS_DO = False
        self.q_xOPN_DO = True
        self.xOvrdClsActive = False
        self.tonOvrd = TON()
        self.tonOvrdMax = TON()
        self.tonDelOK = TON()
        self.rtOK = RTRIG()
        self.tOvrd = t_ovrd
        self.tOvrdMax = t_ovrd_max
        self.logs = []

    def scan(self, dt, i_xExtILK_OK, i_xOverrideMode, first=False):
        if first:
            self.pv_xCLS_SW = False

        self.xCLS_OK = i_xExtILK_OK

        # Qualify the manual close override request
        self.tonOvrd(self.pv_xOvrdCls and i_xOverrideMode, self.tOvrd, dt)
        self.xOvrdClsActive = self.tonOvrd.q

        # Drop a stale request while the global override mode is off
        if not i_xOverrideMode:
            self.pv_xOvrdCls = False

        # A qualified override self-clears after tOvrdMax
        self.tonOvrdMax(self.xOvrdClsActive, self.tOvrdMax, dt)
        if self.tonOvrdMax.q:
            self.xOvrdClsActive = False
            self.pv_xOvrdCls = False
            self.pv_xCLS_SW = True
            self.logs.append('Close override expired')

        # Release the override once the close permission has been TRUE for tOvrd
        self.tonDelOK(self.xCLS_OK, self.tOvrd, dt)
        self.rtOK(self.tonDelOK.q)
        if self.rtOK.q and self.pv_xOvrdCls:
            self.xOvrdClsActive = False
            self.pv_xOvrdCls = False
            self.pv_xCLS_SW = True
            self.logs.append('Override expired')

        # Reset the close request when the interlock is not satisfied, unless a
        # qualified override is holding it
        if not self.xCLS_OK and not self.xOvrdClsActive:
            self.pv_xCLS_SW = False

        # Actuation - the close interlock stays authoritative
        self.q_xCLS_DO = self.xCLS_OK and (self.pv_xCLS_SW or self.xOvrdClsActive)
        self.q_xOPN_DO = not self.q_xCLS_DO
        return self.q_xCLS_DO


DT = 10  # ms


def run(cycles, drive, **kw):
    """drive(t, v) emulates the operator/EPICS side before each scan."""
    v = Valve(**kw)
    trace = []
    for i in range(cycles):
        t = i * DT
        ilk, mode = drive(t, v)
        q = v.scan(DT, ilk, mode, first=(i == 0))
        trace.append(dict(t=t, q_cls=q, active=v.xOvrdClsActive,
                          request=v.pv_xOvrdCls, sw=v.pv_xCLS_SW, q_opn=v.q_xOPN_DO))
    return v, trace


# A: operator forces CLS while the close interlock is FALSE for the first 20 s.
#    The valve must never be driven closed against the interlock, must close once the
#    interlock permits, and the override must then be released on its own.
def drive_a(t, v):
    if t < 25_000:                 # operator holds FORCE_CLS
        v.pv_xOvrdCls = True
    if t < 1_000:                  # operator also asks to close
        v.pv_xCLS_SW = True
    return (t >= 20_000, True)     # close interlock FALSE for the first 20 s


v, tr = run(40_000 // DT, drive_a)
assert all(not r['q_cls'] for r in tr if r['t'] < 20_000), 'closed against the interlock'
assert any(r['active'] for r in tr), 'override never qualified'
assert any(r['q_cls'] for r in tr if r['t'] >= 20_000), 'valve never closed once permitted'
assert all(r['q_cls'] for r in tr if r['t'] >= 31_000), 'close command torn away on release'
assert v.pv_xOvrdCls is False and not v.xOvrdClsActive, 'override not released'
print('A ok: interlock never bypassed, closed once permitted, override released;', v.logs)

# B: interlock held FALSE forever - the override must not stay on indefinitely.
v, tr = run(120_000 // DT, lambda t, v: (v.__setattr__('pv_xOvrdCls', True) or (False, True)),
            t_ovrd_max=30_000)
assert not v.xOvrdClsActive and v.pv_xOvrdCls is False, 'override still active'
assert all(not r['q_cls'] for r in tr), 'closed against the interlock'
print('B ok: override expired after tOvrdMax, close output stayed FALSE;', v.logs)

# C: a request shorter than the qualification time never takes effect.
def drive_c(t, v):
    v.pv_xOvrdCls = t < 5_000       # less than tOvrd = 10 s
    v.pv_xCLS_SW = True
    return (False, True)


v, tr = run(20_000 // DT, drive_c)
assert not any(r['active'] for r in tr), 'unqualified override was honoured'
print('C ok: unqualified (blip) request ignored')

# D: dropping the global override mode releases the request.
v = Valve(t_ovrd=100)
for i in range(30):
    v.pv_xOvrdCls = True
    v.scan(DT, False, True, first=(i == 0))
assert v.xOvrdClsActive, 'never qualified'
for i in range(5):
    v.scan(DT, False, False)
assert not v.xOvrdClsActive and v.pv_xOvrdCls is False
print('D ok: override released when override mode drops')

# E: the old behaviour being fixed - a request held with the interlock FALSE must not
#    reach the close output at any point.
v, tr = run(600_000 // DT, lambda t, v: (v.__setattr__('pv_xOvrdCls', True) or (False, True)),
            t_ovrd=100, t_ovrd_max=50_000)
assert not any(r['q_cls'] for r in tr), 'close output asserted without the interlock'
print('E ok: 10 min of override with the interlock held FALSE never asserts q_xCLS_DO')

print('all simulations passed')
