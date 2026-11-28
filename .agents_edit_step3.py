CRLF = "\r\n"

def read(p):
    return open(p, "rb").read().decode("utf-8-sig")

def write(p, text):
    open(p, "wb").write(b"\xef\xbb\xbf" + text.encode("utf-8"))

def sub_once(text, old, new, label):
    count = text.count(old)
    assert count == 1, "%s: expected 1 occurrence, found %d" % (label, count)
    return text.replace(old, new)

OLD_SCRATCH = (
    "    rBackingSPValidated : REAL; // Backing pressure setpoint accepted by M_ValidatePressureSP, TORR" + CRLF
)
NEW_SCRATCH = (
    "    rBackingSPValidated : REAL; // Backing pressure setpoint accepted by M_ValidatePressureSP, TORR" + CRLF +
    "    xBackingSPValid : BOOL;     // TRUE when M_ValidatePressureSP accepted the backing pressure setpoint" + CRLF
)

OLD_CYCLE = (
    "rBackingSPRequest := iq_stPTM.rBackingPressureSP;" + CRLF +
    "IF M_ValidatePressureSP(" + CRLF +
    "        i_rRequested := rBackingSPRequest," + CRLF +
    "        i_rConfigMin := i_rMinBackingPressure," + CRLF +
    "        i_rConfigMax := i_rMaxBackingPressure," + CRLF +
    "        i_sSpName := 'backing pressure'," + CRLF +
    "        io_rSetpoint := rBackingSPValidated) THEN" + CRLF +
    "    iq_stPTM.rBackingPressureSP := rBackingSPValidated;" + CRLF +
    "END_IF" + CRLF
)
NEW_CYCLE = (
    "rBackingSPRequest := iq_stPTM.rBackingPressureSP;" + CRLF +
    "xBackingSPValid := M_ValidatePressureSP(" + CRLF +
    "    i_rRequested := rBackingSPRequest," + CRLF +
    "    i_rConfigMin := i_rMinBackingPressure," + CRLF +
    "    i_rConfigMax := i_rMaxBackingPressure," + CRLF +
    "    i_sSpName := 'backing pressure'," + CRLF +
    "    io_rSetpoint := rBackingSPValidated);" + CRLF +
    "IF xBackingSPValid THEN" + CRLF +
    "    iq_stPTM.rBackingPressureSP := rBackingSPValidated;" + CRLF +
    "END_IF" + CRLF
)

for p in [
    "L2SIVacuum/POUs/Functions/Pumps/FB_PTM_Pfeiffer.TcPOU",
    "L2SIVacuum/POUs/Functions/Pumps/FB_PTM_TurboDrive.TcPOU",
]:
    t = read(p)
    t = sub_once(t, OLD_SCRATCH, NEW_SCRATCH, p + " scratch")
    t = sub_once(t, OLD_CYCLE, NEW_CYCLE, p + " cycle validation")
    write(p, t)
    print("restructured", p)
