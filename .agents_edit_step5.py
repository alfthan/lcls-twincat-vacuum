import uuid

CRLF = "\r\n"
p = "L2SIVacuum/UnitTests/Pumps/FB_PTM_Test.TcPOU"

def read(p):
    return open(p, "rb").read().decode("utf-8-sig")

def write(p, text):
    open(p, "wb").write(b"\xef\xbb\xbf" + text.encode("utf-8"))

def sub_once(text, old, new, label):
    count = text.count(old)
    assert count == 1, "%s: expected 1 occurrence, found %d" % (label, count)
    return text.replace(old, new)

t = read(p)

# 1. instance of the pump block under test
t = sub_once(
    t,
    "    fb_TwisTorr: FB_PTM_TwisTorr;" + CRLF +
    "    fb_PTM_Ebara_010M:FB_PTM_Ebara_010M;" + CRLF,
    "    fb_TwisTorr: FB_PTM_TwisTorr;" + CRLF +
    "    fb_PTM_Ebara_010M:FB_PTM_Ebara_010M;" + CRLF +
    "    fb_Pfeiffer: FB_PTM_Pfeiffer; // Pump block whose validated setpoint setters are tested" + CRLF,
    "FB_PTM_Test instance",
)

# 2. call the new test method
t = sub_once(
    t,
    "M_PTM_EBARA();" + CRLF + "cycle:=cycle+1;",
    "M_PTM_EBARA();" + CRLF + "M_ValidatedSetpoint();" + CRLF + "cycle:=cycle+1;",
    "FB_PTM_Test call",
)

# 3. the test method itself
guid = str(uuid.uuid4())
method = (
    "    <Method Name=\"M_ValidatedSetpoint\" Id=\"{" + guid + "}\">" + CRLF +
    "      <Declaration><![CDATA[(* Exercises the validated setpoint setters of FB_PTM_Pfeiffer: a request above the" + CRLF +
    "   configured backing pressure limit has to be clamped to that limit before it reaches the pump" + CRLF +
    "   interface struct, and has to be reported as accepted." + CRLF +
    "   History:" + CRLF +
    "   2026-11-28  taio-generic-0: created for audit finding #1207 (validated pressure setpoint setters). *)" + CRLF +
    "METHOD M_ValidatedSetpoint" + CRLF +
    "VAR" + CRLF +
    "    Expected : REAL;   // Expected setpoint after validation, TORR" + CRLF +
    "    Actual : REAL;     // Setpoint the pump interface struct holds, TORR" + CRLF +
    "    xAccepted : BOOL;  // TRUE when the setter accepted the request" + CRLF +
    "END_VAR" + CRLF +
    "]]></Declaration>" + CRLF +
    "      <Implementation>" + CRLF +
    "        <ST><![CDATA[TEST('PTM_Pfeiffer_SetBackingSP_Clamped');" + CRLF +
    "(* The configured limit is tighter than the requested value, so the request has to be clamped to it *)" + CRLF +
    "fb_Pfeiffer(i_xExtILKOk := TRUE, i_rMaxBackingPressure := 1.0, iq_stPTM => );" + CRLF +
    "xAccepted := fb_Pfeiffer.M_SetBackingSP(i_fBackingPressureSP := 5.0);" + CRLF +
    "fb_Pfeiffer(i_xExtILKOk := TRUE, i_rMaxBackingPressure := 1.0, iq_stPTM => );" + CRLF +
    "IF( cycle = 3) THEN" + CRLF +
    "    Expected := 1.0;" + CRLF +
    "    Actual := fb_Pfeiffer.iq_stPTM.rBackingPressureSP;" + CRLF +
    "    AssertEquals_REAL(Expected, Actual, 0.001, 'PTM Pfeiffer backing SP was not clamped to the configured limit');" + CRLF +
    "    AssertTrue(xAccepted, 'PTM Pfeiffer clamped backing SP was not reported as accepted');" + CRLF +
    "    TEST_FINISHED_NAMED('PTM_Pfeiffer_SetBackingSP_Clamped');" + CRLF +
    "END_IF" + CRLF +
    "" + CRLF +
    "TEST('PTM_Pfeiffer_SetForelineSP_Clamped');" + CRLF +
    "(* The same validation applies to the foreline setpoint *)" + CRLF +
    "xAccepted := fb_Pfeiffer.M_SetForelineSP(i_fForelinePressureSP := 5.0);" + CRLF +
    "fb_Pfeiffer(i_xExtILKOk := TRUE, i_rMaxForelinePressure := 0.5, iq_stPTM => );" + CRLF +
    "IF( cycle = 3) THEN" + CRLF +
    "    Expected := 0.5;" + CRLF +
    "    Actual := fb_Pfeiffer.iq_stPTM.rForelineSP;" + CRLF +
    "    AssertEquals_REAL(Expected, Actual, 0.001, 'PTM Pfeiffer foreline SP was not clamped to the configured limit');" + CRLF +
    "    AssertTrue(xAccepted, 'PTM Pfeiffer clamped foreline SP was not reported as accepted');" + CRLF +
    "    TEST_FINISHED_NAMED('PTM_Pfeiffer_SetForelineSP_Clamped');" + CRLF +
    "END_IF]]></ST>" + CRLF +
    "      </Implementation>" + CRLF +
    "    </Method>" + CRLF
)
t = sub_once(t, "  </POU>", method + "  </POU>", "FB_PTM_Test method")

write(p, t)
print("test added to", p, "guid", guid)
