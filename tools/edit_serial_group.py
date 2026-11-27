"""One-off editing helper for the latched-fault task (deleted after use)."""
ROOT = "L2SIVacuum/POUs/Serial drivers/"
NL = "\r\n"


def load(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def rep(s, old, new, path, expect=1):
    n = s.count(old)
    assert n == expect, "%s: expected %d, found %d for %r" % (path, expect, n, old[:90])
    return s.replace(old, new)


def edit(path, reps):
    s = load(path)
    for old, new, *exp in reps:
        s = rep(s, old, new, path, exp[0] if exp else 1)
    save(path, s)
    print("edited", path)


ACK_HEAD = (
    "(* Fault acknowledge/reset: the latched faults are cleared only here, and only from a known-safe state," + NL +
    "   i.e. with no transaction in progress and the execute input released. A new command never clears them. *)" + NL +
    "rtAck(CLK:= i_xAck);" + NL +
    "IF rtAck.Q THEN" + NL +
    "    xAckPending := TRUE;" + NL +
    "END_IF" + NL +
    "IF xAckPending AND NOT i_xExecute AND ((iStep = 0) OR (iStep = 100) OR (iStep = 9000)) THEN" + NL +
    "    xAckPending := FALSE;" + NL +
    "    q_xError := FALSE;" + NL +
    "    q_xTimeout := FALSE;" + NL +
    "    q_sResult := '';" + NL +
    "    IF iStep = 9000 THEN" + NL +
    "        iStep := 0;" + NL +
    "    END_IF" + NL +
    "END_IF" + NL + NL +
    "(* rising edge trigger *)" + NL +
    "rtExecute(CLK:= i_xExecute);" + NL
)

ACK_VARS = (
    "    rtAck: R_TRIG; //Rising edge of the acknowledge input i_xAck" + NL +
    "    xAckPending: BOOL; //Acknowledge received, cleared when the block is in a known-safe state" + NL
)

ACK_INPUT = (
    "    /// Acknowledge/reset of the latched q_xError and q_xTimeout faults" + NL +
    "    i_xAck: BOOL;" + NL
)

# ------------------------------------------------------- FB_TD400Transaction
p = ROOT + "Pumps/Oerlikon TD400/FB_TD400Transaction.TcPOU"
edit(p, [
    ("(* This function block performs serial transactions with an Oerlikon TD20 *)" + NL,
     "(* This function block performs serial transactions with an Oerlikon TD20 *)" + NL +
     "(* Fault handling: q_xError and q_xTimeout are latched and are cleared only by the acknowledge" + NL +
     "   input i_xAck, never by a new execute edge. q_xErrorActive/q_xTimeoutActive report the current" + NL +
     "   transaction only, so the calling state machine keeps working while a fault stays latched. *)" + NL),
    ("    i_tTimeOut: TIME := TIME#1s0ms;" + NL + "END_VAR",
     "    i_tTimeOut: TIME := TIME#1s0ms;" + NL + ACK_INPUT + "END_VAR"),
    ("    q_xDone: BOOL;" + NL +
     "    q_xError: BOOL;" + NL +
     "    q_xTimeout: BOOL;" + NL +
     "    q_sResult: STRING(MAX_STRING_LENGTH);" + NL,
     "    q_xDone: BOOL;" + NL +
     "    /// Latched error: set when a transaction fails, cleared only by i_xAck from a known-safe state" + NL +
     "    q_xError: BOOL;" + NL +
     "    /// Latched timeout: set when the device does not reply in time, cleared only by i_xAck" + NL +
     "    q_xTimeout: BOOL;" + NL +
     "    /// TRUE while the current transaction is failed (not latched: drives the calling state machine)" + NL +
     "    q_xErrorActive: BOOL;" + NL +
     "    /// TRUE while the current transaction timed out (not latched)" + NL +
     "    q_xTimeoutActive: BOOL;" + NL +
     "    q_sResult: STRING(MAX_STRING_LENGTH);" + NL),
    ("    rtExecute: R_TRIG;" + NL + "    iStep: INT;" + NL,
     "    rtExecute: R_TRIG;" + NL +
     "    iStep: INT;" + NL + ACK_VARS),
    ("(* rising edge trigger *)" + NL +
     "rtExecute(CLK:= i_xExecute);" + NL +
     "IF rtExecute.Q THEN" + NL +
     "    q_xDone\t:= FALSE;" + NL +
     "    q_xError := FALSE;" + NL +
     "    q_xTimeout := FALSE;" + NL +
     "    q_sResult:= '';" + NL,
     ACK_HEAD +
     "IF rtExecute.Q THEN" + NL +
     "    q_xDone\t:= FALSE;" + NL +
     "    q_xErrorActive := FALSE;" + NL +
     "    q_xTimeoutActive := FALSE;" + NL +
     "    q_sResult:= '';" + NL),
    ("            q_xTimeout := TRUE;" + NL,
     "            q_xTimeout := TRUE;" + NL + "            q_xTimeoutActive := TRUE;" + NL),
    ("        q_xError := TRUE;" + NL,
     "        q_xError := TRUE;" + NL + "        q_xErrorActive := TRUE;" + NL),
])

# ------------------------------------------------------- FB_LVC4000Transaction
p = ROOT + "LVDT/MacroSensors/FB_LVC4000Transaction.TcPOU"
edit(p, [
    ("    i_sParam: T_MAXSTRING;" + NL + "END_VAR",
     "    i_sParam: T_MAXSTRING;" + NL + ACK_INPUT + "END_VAR"),
    ("    q_xDone: BOOL;" + NL +
     "    q_sResponseData: STRING;" + NL +
     "    q_xError: BOOL;" + NL +
     "    q_xTimeout: BOOL;" + NL,
     "    q_xDone: BOOL;" + NL +
     "    q_sResponseData: STRING;" + NL +
     "    /// Latched error: set when a transaction fails, cleared only by i_xAck from a known-safe state" + NL +
     "    q_xError: BOOL;" + NL +
     "    /// Latched timeout: set when the device does not reply in time, cleared only by i_xAck" + NL +
     "    q_xTimeout: BOOL;" + NL +
     "    /// TRUE while the current transaction is failed (not latched: drives the calling state machine)" + NL +
     "    q_xErrorActive: BOOL;" + NL +
     "    /// TRUE while the current transaction timed out (not latched)" + NL +
     "    q_xTimeoutActive: BOOL;" + NL),
    ("    rtExecute: R_TRIG;" + NL + "    iStep: INT;" + NL,
     "    rtExecute: R_TRIG;" + NL +
     "    iStep: INT;" + NL + ACK_VARS),
    ("(* rising edge trigger *)" + NL +
     "rtExecute(CLK:= i_xExecute);" + NL +
     "IF rtExecute.Q THEN" + NL +
     "    q_xDone\t:= FALSE;" + NL +
     "    q_sResponseData := '';" + NL +
     "    q_xError := FALSE;" + NL +
     "    //q_xTimeout := FALSE;" + NL,
     ACK_HEAD +
     "IF rtExecute.Q THEN" + NL +
     "    q_xDone\t:= FALSE;" + NL +
     "    q_sResponseData := '';" + NL +
     "    q_xErrorActive := FALSE;" + NL +
     "    q_xTimeoutActive := FALSE;" + NL),
    ("            q_xTimeout := TRUE;" + NL + "            iStep := 9000;",
     "            q_xTimeout := TRUE;" + NL + "            q_xTimeoutActive := TRUE;" + NL + "            iStep := 9000;"),
    ("            q_xTimeout := FALSE; //no timeout",
     "            q_xTimeoutActive := FALSE; //no timeout"),
    ("    9000:" + NL + "        q_xError := TRUE;" + NL,
     "    9000:" + NL + "        q_xError := TRUE;" + NL + "        q_xErrorActive := TRUE;" + NL),
])

# --------------------------------------------------- FB_TD400SerialDriver
p = ROOT + "Pumps/Oerlikon TD400/FB_TD400SerialDriver.TcPOU"
s = load(p)
s = rep(s, "    i_wControlWord: WORD;" + NL + "END_VAR",
        "    i_wControlWord: WORD;" + NL + ACK_INPUT + "END_VAR", p)
s = rep(s, "(* rising edge trigger *)" + NL + "rtExecute(CLK:= i_xExecute);",
        "(* Forward the acknowledge/reset of the latched command faults to the transaction block *)" + NL +
        "fbTD400Transaction.i_xAck := i_xAck;" + NL + NL +
        "(* rising edge trigger *)" + NL + "rtExecute(CLK:= i_xExecute);", p)
s = rep(s, "fbTD400Transaction.q_xError", "fbTD400Transaction.q_xErrorActive", p, 8)
s = rep(s, "q_xTimeout := fbTD400Transaction.q_xTimeout;",
        "q_xTimeout := fbTD400Transaction.q_xTimeoutActive;", p)
save(p, s)
print("edited", p)

# -------------------------------------------------- FB_LVC4000SerialDriver
p = ROOT + "LVDT/MacroSensors/FB_LVC4000SerialDriver.TcPOU"
edit(p, [
    ("    i_tTimeOut: TIME := TIME#1s0ms;" + NL + "END_VAR",
     "    i_tTimeOut: TIME := TIME#1s0ms;" + NL + ACK_INPUT + "END_VAR"),
    ("(* rising edge trigger *)" + NL + "rtExecute(CLK:= i_xExecute);",
     "(* Forward the acknowledge/reset of the latched command faults to the transaction block *)" + NL +
     "fbtrans.i_xAck := i_xAck;" + NL + NL +
     "(* rising edge trigger *)" + NL + "rtExecute(CLK:= i_xExecute);"),
    ("ELSIF fbtrans.q_xError THEN", "ELSIF fbtrans.q_xErrorActive THEN"),
    ("iq_stLVC4000.xTimeout := fbtrans.q_xTimeout;",
     "iq_stLVC4000.xTimeout := fbtrans.q_xTimeoutActive;"),
])

print("transaction/driver group done")
