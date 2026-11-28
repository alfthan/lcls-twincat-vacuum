import io, uuid

CRLF = "\r\n"

def read(p):
    with open(p, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8-sig")
    return text

def write(p, text):
    with open(p, "wb") as f:
        f.write(b"\xef\xbb\xbf" + text.encode("utf-8"))

def sub_once(text, old, new, label):
    count = text.count(old)
    assert count == 1, "%s: expected 1 occurrence, found %d" % (label, count)
    return text.replace(old, new)

# ---------------------------------------------------------------- Constants.TcGVL
p = "L2SIVacuum/GVLs/Constants.TcGVL"
t = read(p)
old = (
    "VAR_GLOBAL CONSTANT" + CRLF +
    "    gc_iSizeOfGGOArray : INT := 50;" + CRLF +
    "    gc_GaugeValidState :\tINT := 4;" + CRLF +
    "END_VAR" + CRLF
)
new = (
    "VAR_GLOBAL CONSTANT" + CRLF +
    "    gc_iSizeOfGGOArray : INT := 50;" + CRLF +
    "    gc_GaugeValidState :\tINT := 4;" + CRLF +
    "" + CRLF +
    "    (* Pressure setpoint limits, TORR. The span is the vendor span published by the BP_SP / IP_SP" + CRLF +
    "       pytmc pragmas of ST_PTM (LOPR 0 / HOPR 1000); the configured caps are the defaults a pump" + CRLF +
    "       function block applies to its pressure setpoints until a site tightens them per instance. *)" + CRLF +
    "    gc_rPumpPressureSPMin : REAL := 0.0;            // Lowest pressure setpoint a pump accepts, TORR" + CRLF +
    "    gc_rPumpPressureSPMax : REAL := 1000.0;         // Highest pressure setpoint a pump accepts, TORR" + CRLF +
    "    gc_rPumpBackingPressureSPMax : REAL := 3.0;     // Default configured cap on the backing pressure setpoint, TORR" + CRLF +
    "    gc_rPumpForelinePressureSPMax : REAL := 3.0;    // Default configured cap on the foreline pressure setpoint, TORR" + CRLF +
    "END_VAR" + CRLF
)
t = sub_once(t, old, new, "Constants.TcGVL global constants")
write(p, t)

# ---------------------------------------------------------------- FB_Pump.TcPOU
p = "L2SIVacuum/POUs/Functions/Pumps/FB_Pump.TcPOU"
t = read(p)

header = (
    "(* Base function block for every vacuum pump." + CRLF +
    "   Owns the behaviour all pumps share: the diagnostic logger instance, the previous-state and edge" + CRLF +
    "   detection the concrete pump blocks use, the persistent setpoint storage and the validation of" + CRLF +
    "   requested pressure setpoints. Concrete pump blocks extend it and call ACT_Logger and" + CRLF +
    "   ACT_Persistent from their own implementation." + CRLF +
    "   Objectives:" + CRLF +
    "   - one place for shared pump diagnostics, persistent data plumbing and setpoint validation" + CRLF +
    "   Usage:" + CRLF +
    "   - extend this block (FUNCTION_BLOCK FB_xxx EXTENDS FB_Pump); do not instantiate it directly" + CRLF +
    "   History:" + CRLF +
    "   2026-11-28  taio-generic-0: header comment added and M_ValidatePressureSP added so a requested" + CRLF +
    "               pressure setpoint is validated before it reaches a pump (audit finding #1207). *)" + CRLF
)
t = sub_once(t, "FUNCTION_BLOCK FB_Pump" + CRLF, header + "FUNCTION_BLOCK FB_Pump" + CRLF, "FB_Pump header")

guid = str(uuid.uuid4())
method = (
    "    <Method Name=\"M_ValidatePressureSP\" Id=\"{" + guid + "}\">" + CRLF +
    "      <Declaration><![CDATA[(* Validates a requested pressure setpoint and only lets a usable value through." + CRLF +
    "   The request is checked against the configured limits of the pump and against the vendor's physical" + CRLF +
    "   span (gc_rPumpPressureSPMin / gc_rPumpPressureSPMax). A value outside the resulting range is clamped" + CRLF +
    "   into it and logged as a warning; a value that is not a number, or a request that cannot be validated" + CRLF +
    "   because the configured limits are inverted, is rejected and logged as an error." + CRLF +
    "   io_rSetpoint is written only when the request is accepted, so a rejected request leaves the previous" + CRLF +
    "   setpoint in place and nothing unusable reaches the pump." + CRLF +
    "   Returns TRUE when the request was accepted (possibly clamped), FALSE when it was rejected." + CRLF +
    "   Usage: call it from the setpoint setter of a concrete pump block, passing the pump interface struct" + CRLF +
    "   member as io_rSetpoint, and from the cyclic persistence action to keep an EPICS-writable member in range." + CRLF +
    "   History:" + CRLF +
    "   2026-11-28  taio-generic-0: created for audit finding #1207 (validated pressure setpoint setters). *)" + CRLF +
    "METHOD PROTECTED M_ValidatePressureSP : BOOL" + CRLF +
    "VAR_INPUT" + CRLF +
    "    i_rRequested : REAL;        // Requested setpoint, TORR" + CRLF +
    "    i_rConfigMin : REAL;        // Configured lower limit of this setpoint, TORR" + CRLF +
    "    i_rConfigMax : REAL;        // Configured upper limit of this setpoint, TORR" + CRLF +
    "    i_sSpName : T_MaxString;    // Setpoint name used in the diagnostic message" + CRLF +
    "END_VAR" + CRLF +
    "VAR_IN_OUT" + CRLF +
    "    io_rSetpoint : REAL;        // Setpoint of the device interface struct; written only when accepted" + CRLF +
    "END_VAR" + CRLF +
    "VAR" + CRLF +
    "    rMin : REAL;                // Effective lower limit: configured limit kept inside the vendor span, TORR" + CRLF +
    "    rMax : REAL;                // Effective upper limit: configured limit kept inside the vendor span, TORR" + CRLF +
    "END_VAR" + CRLF +
    "]]></Declaration>" + CRLF +
    "      <Implementation>" + CRLF +
    "        <ST><![CDATA[(* Effective limits: the configured limit, kept inside the vendor's physical span *)" + CRLF +
    "rMin := MAX(i_rConfigMin, gc_rPumpPressureSPMin);" + CRLF +
    "rMax := MIN(i_rConfigMax, gc_rPumpPressureSPMax);" + CRLF +
    "" + CRLF +
    "(* A limit pair that leaves no valid range cannot validate anything: reject and report the configuration *)" + CRLF +
    "IF rMax < rMin THEN" + CRLF +
    "    fbLogger(sMsg := CONCAT(i_sSpName, ' setpoint rejected: the configured limits are inverted.')," + CRLF +
    "             eSevr := TcEventSeverity.Error);" + CRLF +
    "    M_ValidatePressureSP := FALSE;" + CRLF +
    "    RETURN;" + CRLF +
    "END_IF" + CRLF +
    "" + CRLF +
    "IF i_rRequested > rMax THEN" + CRLF +
    "    (* Above the limits: clamp into the valid range, then report *)" + CRLF +
    "    io_rSetpoint := rMax;" + CRLF +
    "    fbLogger(sMsg := CONCAT(i_sSpName, ' setpoint clamped to the upper limit.')," + CRLF +
    "             eSevr := TcEventSeverity.Warning);" + CRLF +
    "    M_ValidatePressureSP := TRUE;" + CRLF +
    "ELSIF i_rRequested < rMin THEN" + CRLF +
    "    (* Below the limits: clamp into the valid range, then report *)" + CRLF +
    "    io_rSetpoint := rMin;" + CRLF +
    "    fbLogger(sMsg := CONCAT(i_sSpName, ' setpoint clamped to the lower limit.')," + CRLF +
    "             eSevr := TcEventSeverity.Warning);" + CRLF +
    "    M_ValidatePressureSP := TRUE;" + CRLF +
    "ELSIF (i_rRequested >= rMin) AND (i_rRequested <= rMax) THEN" + CRLF +
    "    (* In range: accept the request as it was made *)" + CRLF +
    "    io_rSetpoint := i_rRequested;" + CRLF +
    "    M_ValidatePressureSP := TRUE;" + CRLF +
    "ELSE" + CRLF +
    "    (* Not above, below or inside the limits, so the request is not a number (NaN). Reject it and" + CRLF +
    "       leave the previous setpoint in place so that nothing unusable is persisted or sent to the pump *)" + CRLF +
    "    fbLogger(sMsg := CONCAT(i_sSpName, ' setpoint rejected: the requested value is not a number.')," + CRLF +
    "             eSevr := TcEventSeverity.Error);" + CRLF +
    "    M_ValidatePressureSP := FALSE;" + CRLF +
    "END_IF]]></ST>" + CRLF +
    "      </Implementation>" + CRLF +
    "    </Method>" + CRLF
)
t = sub_once(t, "  </POU>", method + "  </POU>", "FB_Pump method insert")
write(p, t)

print("step1 ok, new method guid", guid)
