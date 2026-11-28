CRLF = "\r\n"

def read(p):
    return open(p, "rb").read().decode("utf-8-sig")

def write(p, text):
    open(p, "wb").write(b"\xef\xbb\xbf" + text.encode("utf-8"))

def sub_once(text, old, new, label):
    count = text.count(old)
    assert count == 1, "%s: expected 1 occurrence, found %d" % (label, count)
    return text.replace(old, new)

OLD = (
    "IF xBackingSPValid THEN" + CRLF +
    "    iq_stPTM.rBackingPressureSP := rBackingSPValidated;" + CRLF +
    "END_IF" + CRLF
)
NEW = (
    "IF xBackingSPValid THEN" + CRLF +
    "    iq_stPTM.rBackingPressureSP := rBackingSPValidated;" + CRLF +
    "ELSE" + CRLF +
    "    (* An unusable value must not stay in the interface struct either (a value persisted before the" + CRLF +
    "       validation existed): fall back to the configured lower limit, the safe direction for the pump *)" + CRLF +
    "    iq_stPTM.rBackingPressureSP := i_rMinBackingPressure;" + CRLF +
    "END_IF" + CRLF
)

for p in [
    "L2SIVacuum/POUs/Functions/Pumps/FB_PTM_Pfeiffer.TcPOU",
    "L2SIVacuum/POUs/Functions/Pumps/FB_PTM_TurboDrive.TcPOU",
]:
    t = read(p)
    t = sub_once(t, OLD, NEW, p + " reject fallback")
    write(p, t)
    print("fallback added", p)
