"""One-off editing helper for the latched-fault task (deleted after use)."""
import sys

ROOT = "L2SIVacuum/POUs/"


def load(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def rep(s, old, new, path, expect=1):
    n = s.count(old)
    assert n == expect, "%s: expected %d occurrence(s), found %d for %r" % (
        path, expect, n, old[:80])
    return s.replace(old, new)


def edit(path, reps):
    s = load(path)
    for old, new in reps:
        s = rep(s, old, new, path)
    save(path, s)
    print("edited", path)


NL = "\r\n"

# ---------------------------------------------------------------- FB_TBOOL_ADS
p = ROOT + "ADS/FB_TBOOL_ADS.TcPOU"
edit(p, [
    ("(* The variable values are read via ADS using the symbol name*)" + NL,
     "(* The variable values are read via ADS using the symbol name*)" + NL +
     "(* Fault handling: bError is latched and is cleared only by the acknowledge input i_xAck*)" + NL),
    ("    iWatchdog:UDINT;//The watchdog variable name written to by the remote plc" + NL + "END_VAR",
     "    iWatchdog:UDINT;//The watchdog variable name written to by the remote plc" + NL +
     "    i_xAck : BOOL; //Acknowledge/reset of the latched bError fault: the only way bError is cleared" + NL +
     "END_VAR"),
    ("    bError: BOOL;" + NL + "END_VAR",
     "    bError: BOOL; //Latched fault: set by an ADS read error or a watchdog trip, cleared only by i_xAck" + NL +
     "END_VAR"),
    ("    xFirstPass: BOOL:= true;" + NL,
     "    xFirstPass: BOOL:= true;" + NL +
     "    xErrorLatched : BOOL; //Latched fault, driven from the ADS read error and the watchdog trip" + NL +
     "    rtAck : R_TRIG; //Rising edge of the acknowledge input i_xAck" + NL),
    ("bError:= fb_Read.bError OR fb_CheckWatchdog.bWatchdog;" + NL +
     "tErrorPresent(CLK:=bError);" + NL + NL +
     "IF (fb_Read.bError OR fb_CheckWatchdog.bWatchdog) THEN" + NL +
     "    bBool := FALSE; // If there is an error in connection the signal turns to FALSE" + NL +
     "END_IF;",
     "(*Latched fault: an ADS read error or a watchdog trip sets the latch and it stays set across cycles." + NL +
     "It is cleared only by the acknowledge input i_xAck, and only while both fault sources are healthy again.*)" + NL +
     "IF (fb_Read.bError OR fb_CheckWatchdog.bWatchdog) THEN" + NL +
     "    xErrorLatched := TRUE;" + NL +
     "END_IF" + NL + NL +
     "rtAck(CLK:= i_xAck);" + NL +
     "IF rtAck.Q AND NOT (fb_Read.bError OR fb_CheckWatchdog.bWatchdog) THEN" + NL +
     "    xErrorLatched := FALSE;" + NL +
     "END_IF" + NL + NL +
     "bError := xErrorLatched;" + NL +
     "tErrorPresent(CLK:= bError);" + NL + NL +
     "IF xErrorLatched THEN" + NL +
     "    bBool := FALSE; // While the fault is latched the signal is held at the safe state FALSE" + NL +
     "END_IF;"),
])

# --------------------------------------------------- FB_TGCC_ADS / FB_TPIP_ADS
for rel in ("Functions/Gauges/Interfaces/FB_TGCC_ADS.TcPOU",
            "Functions/Pumps/Interfaces/FB_TPIP_ADS.TcPOU"):
    p = ROOT + rel
    edit(p, [
        ("    iWatchdog:UDINT;//The watchdog variable name written to by the remote plc" + NL + "END_VAR",
         "    iWatchdog:UDINT;//The watchdog variable name written to by the remote plc" + NL +
         "    i_xAck : BOOL; //Acknowledge/reset of the latched bError fault: the only way bError is cleared" + NL +
         "END_VAR"),
        ("    bError: BOOL;" + NL + "END_VAR",
         "    bError: BOOL; //Latched fault: set by an ADS read error or a watchdog trip, cleared only by i_xAck" + NL +
         "END_VAR"),
        ("    xFirstPass: BOOL:= true;" + NL,
         "    xFirstPass: BOOL:= true;" + NL +
         "    xErrorLatched : BOOL; //Latched fault, driven from the ADS read error and the watchdog trip" + NL +
         "    rtAck : R_TRIG; //Rising edge of the acknowledge input i_xAck" + NL),
        ("bError:= fb_Read_VG.bError OR fb_CheckWatchdog.bWatchdog;" + NL +
         "tErrorPresent(CLK:=bError);" + NL + NL +
         "IF (fb_Read_VG.bError OR fb_CheckWatchdog.bWatchdog) THEN" + NL +
         "IG.xPRESS_OK := FALSE;" + NL +
         "END_IF;",
         "(*Latched fault: an ADS read error or a watchdog trip sets the latch and it stays set across cycles." + NL +
         "It is cleared only by the acknowledge input i_xAck, and only while both fault sources are healthy again.*)" + NL +
         "IF (fb_Read_VG.bError OR fb_CheckWatchdog.bWatchdog) THEN" + NL +
         "    xErrorLatched := TRUE;" + NL +
         "END_IF" + NL + NL +
         "rtAck(CLK:= i_xAck);" + NL +
         "IF rtAck.Q AND NOT (fb_Read_VG.bError OR fb_CheckWatchdog.bWatchdog) THEN" + NL +
         "    xErrorLatched := FALSE;" + NL +
         "END_IF" + NL + NL +
         "bError := xErrorLatched;" + NL +
         "tErrorPresent(CLK:= bError);" + NL + NL +
         "IF xErrorLatched THEN" + NL +
         "IG.xPRESS_OK := FALSE; // While the fault is latched the readback is held not-OK" + NL +
         "END_IF;"),
    ])

# ---------------------------------------------------------------- FB_TVGC_ADS
p = ROOT + "Functions/Valves/Interfaces/FB_TVGC_ADS.TcPOU"
edit(p, [
    ("    iWatchdog:UDINT;//The watchdog variable name written to by the remote plc" + NL + "END_VAR",
     "    iWatchdog:UDINT;//The watchdog variable name written to by the remote plc" + NL +
     "    i_xAck : BOOL; //Acknowledge/reset of the latched bError fault: the only way bError is cleared" + NL +
     "END_VAR"),
    ("    bError:BOOL;" + NL + "END_VAR",
     "    bError:BOOL; //Latched fault: set by an ADS read error or a watchdog trip, cleared only by i_xAck" + NL +
     "END_VAR"),
    ("    xFirstPass: bool:= true;" + NL,
     "    xFirstPass: bool:= true;" + NL +
     "    xErrorLatched : BOOL; //Latched fault, driven from the ADS read error and the watchdog trip" + NL +
     "    rtAck : R_TRIG; //Rising edge of the acknowledge input i_xAck" + NL),
    ("bError:= fb_Read_VGC.bError OR fb_CheckWatchdog.bWatchdog;" + NL + NL + "ACT_Logger();",
     "(*Latched fault: an ADS read error or a watchdog trip sets the latch and it stays set across cycles." + NL +
     "It is cleared only by the acknowledge input i_xAck, and only while both fault sources are healthy again.*)" + NL +
     "IF (fb_Read_VGC.bError OR fb_CheckWatchdog.bWatchdog) THEN" + NL +
     "    xErrorLatched := TRUE;" + NL +
     "END_IF" + NL + NL +
     "rtAck(CLK:= i_xAck);" + NL +
     "IF rtAck.Q AND NOT (fb_Read_VGC.bError OR fb_CheckWatchdog.bWatchdog) THEN" + NL +
     "    xErrorLatched := FALSE;" + NL +
     "END_IF" + NL + NL +
     "bError := xErrorLatched;" + NL +
     "tErrorPresent(CLK:= bError);" + NL + NL +
     "ACT_Logger();"),
])

# ------------------------------------------------------------ FB_ADS_WATCHDOG
p = ROOT + "ADS/FB_ADS_WATCHDOG.TcPOU"
edit(p, [
    ("    sVarName : string;// the variable name of the watchdog on the remote plc." + NL + "END_VAR",
     "    sVarName : string;// the variable name of the watchdog on the remote plc." + NL +
     "    i_xAck : BOOL; //Acknowledge/reset of the latched bError fault: the only way bError is cleared" + NL +
     "END_VAR"),
    ("    bError:BOOL;" + NL + "END_VAR",
     "    bError:BOOL; //Latched fault: set by an ADS write error, cleared only by i_xAck" + NL +
     "END_VAR"),
    ("    xFirstPass: BOOL:= true;" + NL,
     "    xFirstPass: BOOL:= true;" + NL +
     "    xErrorActive : BOOL; //Live ADS write error reported by fb_WriteWatchdog" + NL +
     "    xErrorLatched : BOOL; //Latched fault, driven from xErrorActive" + NL +
     "    rtAck : R_TRIG; //Rising edge of the acknowledge input i_xAck" + NL),
    ("    bError=> bError," + NL + "    nErrorId=> );" + NL + NL + NL + "(*Error*)" + NL,
     "    bError=> xErrorActive," + NL +
     "    nErrorId=> );" + NL + NL + NL +
     "(*Error*)" + NL +
     "(*Latched fault: an ADS write error sets the latch and it stays set across cycles. It is cleared only" + NL +
     "by the acknowledge input i_xAck, and only while the write path reports healthy again.*)" + NL +
     "IF xErrorActive THEN" + NL +
     "    xErrorLatched := TRUE;" + NL +
     "END_IF" + NL + NL +
     "rtAck(CLK:= i_xAck);" + NL +
     "IF rtAck.Q AND NOT xErrorActive THEN" + NL +
     "    xErrorLatched := FALSE;" + NL +
     "END_IF" + NL + NL +
     "bError := xErrorLatched;" + NL),
])

print("ADS group done")
