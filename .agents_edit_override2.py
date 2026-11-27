"""Follow-up edits: tidy the override VAR placement / header blank line and add the override
test coverage to FB_PTM_Test.TcPOU (task #324).
"""
import io

BASE = "L2SIVacuum/POUs/Functions/Pumps/"
TEST = "L2SIVacuum/UnitTests/Pumps/FB_PTM_Test.TcPOU"

OVRD_VARS_LINES = [
    "    (* Manual override: qualified, self-clearing and gated by the interlock permit *)",
    "    tonOvrd : TON;                  (* Override qualification timer: the request must be held for tOvrd *)",
    "    tonOvrdMax : TON;               (* Override duration timer: an active override expires after tOvrdMax *)",
    "    rtOvrdExpired : R_TRIG;         (* Rising edge of tonOvrdMax.Q, used for the self-clear and the log entry *)",
    "    tOvrd : TIME := T#10S;          (* Override qualification time: the request must persist this long before it is honoured *)",
    "    tOvrdMax : TIME := T#5M;        (* Maximum time an active override stays on before it clears itself *)",
    "    xOvrdQualified : BOOL;          (* The request is qualified and has not expired yet *)",
    "    xOvrdActive : BOOL;             (* Effective override: qualified AND not expired. Only ever ANDed with the permit, never instead of it *)",
    "    xOvrdExpired : BOOL;            (* Latched after tOvrdMax; a dropped request (i_xOverride FALSE) re-arms the override *)",
    "    xOvrdDenied : R_TRIG;           (* Rising edge of an override request the interlock refuses, for one-shot logging *)",
]
OVRD_VARS = "\r\n".join(OVRD_VARS_LINES) + "\r\n"


def read(path):
    with io.open(path, "rb") as handle:
        return handle.read().decode("utf-8")


def write(path, text):
    with io.open(path, "wb") as handle:
        handle.write(text.encode("utf-8"))


def rep(text, old, new, label):
    old_crlf = old.replace("\r\n", "\n").replace("\n", "\r\n")
    new_crlf = new.replace("\r\n", "\n").replace("\n", "\r\n")
    count = text.count(old_crlf)
    if count != 1:
        raise SystemExit("%s: expected 1 match, found %d" % (label, count))
    return text.replace(old_crlf, new_crlf, 1)


def move_block(path, anchor, label):
    """Remove the override VAR block and re-insert it right after `anchor`."""
    text = read(path)
    if text.count(OVRD_VARS) != 1:
        raise SystemExit("%s: override VAR block not found exactly once" % label)
    text = text.replace(OVRD_VARS, "", 1)
    text = rep(text, anchor, anchor + OVRD_VARS, label)
    write(path, text)
    print("tidied " + path)


# --- 011M: move the override VAR block down beside the other state variables
move_block(BASE + "FB_PTM_Ebara_011M.TcPOU", "    i_iADCBits : UINT := 12;\r\n", "011M vars")

# --- FB_PTM_Ebara: move the block below the TOF timers, drop the duplicated blank line
move_block(BASE + "FB_PTM_Ebara.TcPOU", "    TOF_RESET: TOF :=(PT:=T#0.5S);\r\n", "Ebara vars")
path = BASE + "FB_PTM_Ebara.TcPOU"
text = read(path)
text = rep(text, "Scott Stubbs & Alex W.\r\n\r\n\r\n Manual override policy",
           "Scott Stubbs & Alex W.\r\n\r\n Manual override policy", path + " header")
write(path, text)

# --- FB_PTM_Test: call the new override test method and add it
text = read(TEST)
text = rep(text, "M_PTM_EBARA();\r\ncycle:=cycle+1;", "M_PTM_EBARA();\r\nM_Override();\r\ncycle:=cycle+1;",
           "test body")

OVERRIDE_METHOD = """    <Method Name="M_Override" Id="{c4f1a2d7-6b39-4e51-9f0c-2d8b7a5e9c31}">
      <Declaration><![CDATA[METHOD M_Override
VAR_INPUT
END_VAR
]]></Declaration>
      <Implementation>
        <ST><![CDATA[(* Manual override policy coverage (conv_eeb5d87743fc / audit finding #566):
   a manual override is time-qualified, self-clearing and never a bypass of the safety interlock.
   fb_PTM_Ebara_010M is the compiled Ebara PTM block that owns ST_EbaraPTM.i_xOverride. *)

(* An override must never run the pump while the interlock permit is not satisfied *)
TEST('PTM_EBARA_Override_NoILK');
fb_PTM_Ebara_010M.tOvrd := T#0S; //qualify immediately, no wait inside the test
fb_PTM_Ebara_010M.tOvrdMax := T#5M;
fb_PTM_Ebara_010M.xOvrdExpired := FALSE;
fb_PTM_Ebara_010M.iq_stPTM.i_xOverride := TRUE;
fb_PTM_Ebara_010M.iq_stPTM.xRunSW := TRUE;
fb_PTM_Ebara_010M(i_xExtILKOk:= FALSE, iq_stPTM=> );
AssertFalse(fb_PTM_Ebara_010M.iq_stPTM.q_RunDO, 'PTM EBARA override ran the pump with the interlock not satisfied');
TEST_FINISHED_NAMED('PTM_EBARA_Override_NoILK');

(* With the interlock permit satisfied the qualified override still runs the pump *)
TEST('PTM_EBARA_Override_ILK_OK');
fb_PTM_Ebara_010M.tOvrd := T#0S;
fb_PTM_Ebara_010M.tOvrdMax := T#5M;
fb_PTM_Ebara_010M.xOvrdExpired := FALSE;
fb_PTM_Ebara_010M.iq_stPTM.i_xOverride := TRUE;
fb_PTM_Ebara_010M.iq_stPTM.xRunSW := TRUE;
fb_PTM_Ebara_010M(i_xExtILKOk:= TRUE, iq_stPTM=> );
AssertTrue(fb_PTM_Ebara_010M.xOvrdActive, 'PTM EBARA override was not qualified with the interlock OK');
AssertTrue(fb_PTM_Ebara_010M.iq_stPTM.q_RunDO, 'PTM EBARA override did not run the pump with the interlock OK');
TEST_FINISHED_NAMED('PTM_EBARA_Override_ILK_OK');

(* A qualified override clears itself once tOvrdMax has elapsed *)
TEST('PTM_EBARA_Override_SelfClear');
fb_PTM_Ebara_010M.tOvrd := T#0S;
fb_PTM_Ebara_010M.tOvrdMax := T#0S; //expire the override duration immediately, no wait inside the test
fb_PTM_Ebara_010M.xOvrdExpired := FALSE;
fb_PTM_Ebara_010M.iq_stPTM.i_xOverride := TRUE;
fb_PTM_Ebara_010M.iq_stPTM.xRunSW := TRUE;
fb_PTM_Ebara_010M(i_xExtILKOk:= TRUE, iq_stPTM=> );
AssertTrue(fb_PTM_Ebara_010M.xOvrdExpired, 'PTM EBARA override did not self-clear after tOvrdMax');
AssertFalse(fb_PTM_Ebara_010M.xOvrdActive, 'PTM EBARA override stayed active after tOvrdMax');
TEST_FINISHED_NAMED('PTM_EBARA_Override_SelfClear');

//Restore the production timing values and drop the retained request
fb_PTM_Ebara_010M.tOvrd := T#10S;
fb_PTM_Ebara_010M.tOvrdMax := T#5M;
fb_PTM_Ebara_010M.iq_stPTM.i_xOverride := FALSE;
fb_PTM_Ebara_010M.iq_stPTM.xRunSW := FALSE;
fb_PTM_Ebara_010M(i_xExtILKOk:= TRUE, iq_stPTM=> );]]></ST>
      </Implementation>
    </Method>
"""
text = rep(text, "  </POU>", OVERRIDE_METHOD + "  </POU>", "test method")
write(TEST, text)
print("patched " + TEST)
