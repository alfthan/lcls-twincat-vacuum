"""Scan-by-scan model of the patched FB_PTM_Ebara_010M supervisory + override logic.

TwinCAT XAE is not available in this sandbox, so the patched ST statements are replayed here
with a simple TON model to check the four required properties of conv_eeb5d87743fc.
"""


class TON(object):
    def __init__(self, pt=0.0):
        self.IN = False
        self.PT = pt
        self.ET = 0.0
        self.Q = False

    def call(self, IN, PT, dT):
        self.IN = IN
        self.PT = PT
        if not IN:
            self.ET = 0.0
            self.Q = False
        else:
            self.ET = min(self.ET + dT, self.PT) if self.PT > 0 else 0.0
            self.Q = self.ET >= self.PT
        return self.Q


class R_TRIG(object):
    def __init__(self):
        self.M = False
        self.Q = False

    def call(self, CLK):
        self.Q = CLK and not self.M
        self.M = CLK
        return self.Q


class Ebara010M(object):
    """Mirror of the patched FB_PTM_Ebara_010M statements (override + supervisory section)."""

    def __init__(self):
        self.tonOvrd = TON()
        self.tonOvrdMax = TON()
        self.rtOvrdExpired = R_TRIG()
        self.xOvrdDenied = R_TRIG()
        self.tOvrd = 10.0
        self.tOvrdMax = 300.0
        self.xOvrdQualified = False
        self.xOvrdActive = False
        self.xOvrdExpired = False
        # struct state (ST_EbaraPTM)
        self.i_xOverride = False
        self.xRunSW = False
        self.i_xFault = False
        self.q_RunDO = False
        self.q_xProtection = False
        self.logs = []

    def log(self, msg):
        self.logs.append(msg)

    def call(self, i_xExtILKOk, dT):
        # iq_stPtm.xExtRunOk:= i_xExtILKOk AND NOT iq_stPTM.i_xFault;
        xExtRunOk = i_xExtILKOk and not self.i_xFault
        # --- ACT_Override()
        if not self.i_xOverride:
            self.xOvrdExpired = False
        self.tonOvrd.call(self.i_xOverride and not self.xOvrdExpired, self.tOvrd, dT)
        self.xOvrdQualified = self.tonOvrd.Q and self.i_xOverride and not self.xOvrdExpired
        self.tonOvrdMax.call(self.xOvrdQualified, self.tOvrdMax, dT)
        self.rtOvrdExpired.call(self.tonOvrdMax.Q)
        if self.rtOvrdExpired.Q:
            self.xOvrdExpired = True
            self.log("Override cleared: maximum override duration elapsed")
        self.xOvrdActive = self.xOvrdQualified and not self.xOvrdExpired
        self.xOvrdDenied.call(self.xOvrdActive and not xExtRunOk)
        if self.xOvrdDenied.Q:
            self.log("Override request refused, pump interlock not satisfied, pump stays stopped.")
        # --- supervisory section
        if self.xOvrdActive and xExtRunOk:
            self.q_RunDO = bool(self.xRunSW)
        elif self.i_xFault or (not xExtRunOk):
            self.q_RunDO = False
            self.xRunSW = False
        elif self.xRunSW and xExtRunOk:
            self.q_RunDO = True
        if not self.xRunSW:
            self.q_RunDO = False


DT = 0.01  # 10 ms task

# 1. An override never runs the pump while the interlock is not satisfied, not even once.
fb = Ebara010M()
fb.i_xOverride = True
fb.xRunSW = True
ran_without_ilk = []
for _ in range(int(400 / DT)):  # 400 s with the interlock unsatisfied
    fb.call(i_xExtILKOk=False, dT=DT)
    if fb.q_RunDO:
        ran_without_ilk.append(True)
print("1 no-bypass (ILK FALSE): qualified=%s q_RunDO ever TRUE=%s denied-logged=%s"
      % (fb.tonOvrd.Q, bool(ran_without_ilk), "Override request refused" in " ".join(fb.logs)))
assert not ran_without_ilk
assert fb.xOvrdExpired, "override must clear itself even while the interlock is unsatisfied"

# 2. Qualification: the override is honoured only after the request has been held for tOvrd.
fb = Ebara010M()
fb.i_xOverride = True
fb.xRunSW = True
first_active = None
for n in range(int(60 / DT)):
    fb.call(i_xExtILKOk=True, dT=DT)
    if fb.xOvrdActive and first_active is None:
        first_active = n * DT
print("2 qualification: override first honoured at t=%.2fs (tOvrd=%.1fs)"
      % (first_active, fb.tOvrd))
assert first_active is not None and first_active >= fb.tOvrd
assert first_active <= fb.tOvrd + 2 * DT

# 3. Self-clearing: the override expires after tOvrdMax with the request still raised.
fb = Ebara010M()
fb.i_xOverride = True
fb.xRunSW = True
expired_at = None
for n in range(int(400 / DT)):
    fb.call(i_xExtILKOk=True, dT=DT)
    if fb.xOvrdExpired and expired_at is None:
        expired_at = n * DT
print("3 self-clear: expired at t=%.2fs (tOvrd+tOvrdMax=%.1fs) active=%s"
      % (expired_at, fb.tOvrd + fb.tOvrdMax, fb.xOvrdActive))
assert expired_at is not None and expired_at <= fb.tOvrd + fb.tOvrdMax + 3 * DT
assert not fb.xOvrdActive

# 4. Losing the interlock while the override is active stops the pump at once.
fb = Ebara010M()
fb.i_xOverride = True
fb.xRunSW = True
for _ in range(int(15 / DT)):
    fb.call(i_xExtILKOk=True, dT=DT)
assert fb.q_RunDO
fb.call(i_xExtILKOk=False, dT=DT)
print("4 permit lost while overriding: q_RunDO=%s xRunSW=%s" % (fb.q_RunDO, fb.xRunSW))
assert not fb.q_RunDO and not fb.xRunSW

# 5. Normal (no override) behaviour is unchanged: run only with the interlock satisfied.
fb = Ebara010M()
fb.xRunSW = True
fb.call(i_xExtILKOk=False, dT=DT)
assert not fb.q_RunDO and not fb.xRunSW
fb.xRunSW = True
fb.call(i_xExtILKOk=True, dT=DT)
print("5 normal logic: run without ILK=%s, run with ILK=%s" % (False, fb.q_RunDO))
assert fb.q_RunDO

# 6. A dropped request re-arms the override (no permanent lockout after an expiry).
fb = Ebara010M()
fb.i_xOverride = True
fb.xRunSW = True
for _ in range(int(320 / DT)):
    fb.call(i_xExtILKOk=True, dT=DT)
assert fb.xOvrdExpired
fb.i_xOverride = False
fb.call(i_xExtILKOk=True, dT=DT)
assert not fb.xOvrdExpired
fb.i_xOverride = True
for _ in range(int(11 / DT)):
    fb.call(i_xExtILKOk=True, dT=DT)
print("6 re-arm after a drop: xOvrdActive=%s" % fb.xOvrdActive)
assert fb.xOvrdActive

print("ALL MODEL CHECKS PASSED")
