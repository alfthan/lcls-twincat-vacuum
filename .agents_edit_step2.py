import uuid

CRLF = "\r\n"

def read(p):
    with open(p, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8-sig")

def write(p, text):
    with open(p, "wb") as f:
        f.write(b"\xef\xbb\xbf" + text.encode("utf-8"))

def sub_once(text, old, new, label):
    count = text.count(old)
    assert count == 1, "%s: expected 1 occurrence, found %d" % (label, count)
    return text.replace(old, new)

LIMIT_INPUTS_TEMPLATE = (
    "    {ILK} : BOOL; // Connect to external interlock logic, TRUE if not used." + CRLF +
    "    // Configured limits of the pressure setpoints, TORR. The setters clamp or reject against these" + CRLF +
    "    // limits and never against anything outside the vendor span declared in Constants." + CRLF +
    "    i_rMinBackingPressure : REAL := gc_rPumpPressureSPMin;          // Configured lower limit, backing pressure" + CRLF +
    "    i_rMaxBackingPressure : REAL := gc_rPumpBackingPressureSPMax;   // Configured upper limit, backing pressure" + CRLF +
    "    i_rMinForelinePressure : REAL := gc_rPumpPressureSPMin;         // Configured lower limit, foreline pressure" + CRLF +
    "    i_rMaxForelinePressure : REAL := gc_rPumpForelinePressureSPMax; // Configured upper limit, foreline pressure" + CRLF +
    "END_VAR"
)

SCRATCH_VARS = (
    "    // Scratch for the cyclic validation of the EPICS-writable backing pressure setpoint" + CRLF +
    "    rBackingSPRequest : REAL;   // Backing pressure setpoint read from the pump interface struct, TORR" + CRLF +
    "    rBackingSPValidated : REAL; // Backing pressure setpoint accepted by M_ValidatePressureSP, TORR" + CRLF
)

CYCLE_VALIDATION = (
    "(*The backing pressure setpoint of the interface struct is also writable from EPICS, so validate the" + CRLF +
    "  struct value before it is persisted or handed on to the pump*)" + CRLF +
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

PERSIST_ANCHOR = "(*Check if a new value has been written in the structure variable copy it to the persistent variable*)"


def setter_method(name, guid, sp_member, cfg_min, cfg_max, sp_name, req_var, doc):
    return (
        "    <Method Name=\"" + name + "\" Id=\"{" + guid + "}\">" + CRLF +
        "      <Declaration><![CDATA[(* " + doc[0] + CRLF +
        "   " + doc[1] + CRLF +
        "   " + doc[2] + CRLF +
        "   " + doc[3] + CRLF +
        "   Returns TRUE when the request was accepted (possibly clamped), FALSE when it was rejected. *)" + CRLF +
        "METHOD PUBLIC " + name + " : BOOL" + CRLF +
        "VAR_INPUT" + CRLF +
        "    " + req_var + " : REAL;    // Requested " + sp_name + " setpoint, TORR" + CRLF +
        "END_VAR" + CRLF +
        "]]></Declaration>" + CRLF +
        "      <Implementation>" + CRLF +
        "        <ST><![CDATA[" + name + " := M_ValidatePressureSP(" + CRLF +
        "    i_rRequested := " + req_var + "," + CRLF +
        "    i_rConfigMin := " + cfg_min + "," + CRLF +
        "    i_rConfigMax := " + cfg_max + "," + CRLF +
        "    i_sSpName := '" + sp_name + "'," + CRLF +
        "    io_rSetpoint := " + sp_member + ");]]></ST>" + CRLF +
        "      </Implementation>" + CRLF +
        "    </Method>" + CRLF
    )


def old_setter(name, guid, sp_member, req_var):
    return (
        "    <Method Name=\"" + name + "\" Id=\"{" + guid + "}\">" + CRLF +
        "      <Declaration><![CDATA[METHOD PUBLIC " + name + CRLF +
        "VAR_INPUT" + CRLF +
        "    " + req_var + " : REAL;" + CRLF +
        "END_VAR" + CRLF +
        "]]></Declaration>" + CRLF +
        "      <Implementation>" + CRLF +
        "        <ST><![CDATA[" + sp_member + " := " + req_var + ";]]></ST>" + CRLF +
        "      </Implementation>" + CRLF +
        "    </Method>" + CRLF
    )


PUMP_DOC_BACKING = [
    "Writes the requested backing pressure setpoint into the pump interface struct, but only after",
    "M_ValidatePressureSP has checked it against the configured limits and the vendor's physical span:",
    "an out-of-range request is clamped and logged, a request that is not a number is rejected and the",
    "previous setpoint is kept, so no unusable value is persisted or sent to the pump.",
]
PUMP_DOC_FORELINE = [
    "Writes the requested foreline pressure setpoint into the pump interface struct, but only after",
    "M_ValidatePressureSP has checked it against the configured limits and the vendor's physical span:",
    "an out-of-range request is clamped and logged, a request that is not a number is rejected and the",
    "previous setpoint is kept, so no unusable value is persisted or sent to the pump.",
]

targets = [
    {
        "path": "L2SIVacuum/POUs/Functions/Pumps/FB_PTM_Pfeiffer.TcPOU",
        "sp": "iq_stPTM",
        "ilk": "i_xExtIlkOK",
        "scratch_anchor": "VAR" + CRLF + "    TOF_RESET: TON :=(PT:=T#1S);" + CRLF,
        "scratch_new": "VAR" + CRLF + SCRATCH_VARS + "    TOF_RESET: TON :=(PT:=T#1S);" + CRLF,
        "backing_guid": "a5df0061-e4fb-441a-a9e9-98e9e90ee6b0",
        "foreline_guid": "157f114f-64d3-46b9-ada2-19219f6cb020",
    },
    {
        "path": "L2SIVacuum/POUs/Functions/Pumps/FB_PTM_TurboDrive.TcPOU",
        "sp": "iq_stPtm",
        "ilk": "i_xExtILKOk",
        "scratch_anchor": "VAR" + CRLF + CRLF + "    xRunOk\t:\tBOOL;" + CRLF,
        "scratch_new": "VAR" + CRLF + CRLF + SCRATCH_VARS + "    xRunOk\t:\tBOOL;" + CRLF,
        "backing_guid": "6e065065-68e3-4f57-924c-8e7bfc981276",
        "foreline_guid": "f4ff84d2-f083-48f5-8918-754ad96e89ec",
    },
]


for tg in targets:
    p = tg["path"]
    sp = tg["sp"]
    t = read(p)

    # 1. configured limit inputs
    ilk = tg["ilk"]
    t = sub_once(
        t,
        "    " + ilk + " : BOOL; // Connect to external interlock logic, TRUE if not used." + CRLF + "END_VAR",
        LIMIT_INPUTS_TEMPLATE.format(ILK=ilk),
        p + " limit inputs",
    )

    # 2. validation scratch variables
    t = sub_once(t, tg["scratch_anchor"], tg["scratch_new"], p + " scratch vars")

    # 3. cyclic validation of the EPICS-writable struct member
    t = sub_once(t, PERSIST_ANCHOR, CYCLE_VALIDATION + PERSIST_ANCHOR, p + " cyclic validation")

    # 4. validated setters
    t = sub_once(
        t,
        old_setter("M_SetBackingSP", tg["backing_guid"], sp + ".rBackingPressureSP", "i_fBackingPressureSP"),
        setter_method(
            "M_SetBackingSP", tg["backing_guid"], sp + ".rBackingPressureSP",
            "i_rMinBackingPressure", "i_rMaxBackingPressure", "backing pressure",
            "i_fBackingPressureSP", PUMP_DOC_BACKING,
        ),
        p + " M_SetBackingSP",
    )
    t = sub_once(
        t,
        old_setter("M_SetForelineSP", tg["foreline_guid"], sp + ".rForelineSP", "i_fForelinePressureSP"),
        setter_method(
            "M_SetForelineSP", tg["foreline_guid"], sp + ".rForelineSP",
            "i_rMinForelinePressure", "i_rMaxForelinePressure", "foreline pressure",
            "i_fForelinePressureSP", PUMP_DOC_FORELINE,
        ),
        p + " M_SetForelineSP",
    )

    write(p, t)
    print("updated", p)
