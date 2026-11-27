"""One-shot edit script: make the Ebara PTM manual override time-qualified, self-clearing
and non-bypassing (conv_eeb5d87743fc / audit finding #566, task #324).

Rewrites the POU files with exact string replacements, preserving CRLF line endings.
"""
import uuid
import io

BASE = "L2SIVacuum/POUs/Functions/Pumps/"

OVRD_POLICY = """
 Manual override policy (conv_eeb5d87743fc - an override is time-qualified, self-clearing and never
 a bypass of safety interlocks):
 - ST_EbaraPTM.i_xOverride (EPICS OVRD_ON) is only a *request*. It is honoured only after it has been
   held continuously for the qualification time tOvrd (tonOvrd), so a blip cannot raise an override.
 - The override clears itself after the configured maximum duration tOvrdMax (tonOvrdMax) unless the
   operator drops and re-raises the request, so it can never be left on indefinitely.
 - The override is ANDed with the interlock permit iq_stPTM.xExtRunOk. It can drop the vacuum-logic
   command, but it can never run the pump while the interlocks are not satisfied; an override request
   the interlock refuses is logged at Warning severity.
 History: 2026-11-27 Scirix agent (task #324) - removed the interlock bypass, added the override
          qualification (tonOvrd/tOvrd) and self-clearing (tonOvrdMax/tOvrdMax) timers."""

OVRD_VARS = """    (* Manual override: qualified, self-clearing and gated by the interlock permit *)
    tonOvrd : TON;                  (* Override qualification timer: the request must be held for tOvrd *)
    tonOvrdMax : TON;               (* Override duration timer: an active override expires after tOvrdMax *)
    rtOvrdExpired : R_TRIG;         (* Rising edge of tonOvrdMax.Q, used for the self-clear and the log entry *)
    tOvrd : TIME := T#10S;          (* Override qualification time: the request must persist this long before it is honoured *)
    tOvrdMax : TIME := T#5M;        (* Maximum time an active override stays on before it clears itself *)
    xOvrdQualified : BOOL;          (* The request is qualified and has not expired yet *)
    xOvrdActive : BOOL;             (* Effective override: qualified AND not expired. Only ever ANDed with the permit, never instead of it *)
    xOvrdExpired : BOOL;            (* Latched after tOvrdMax; a dropped request (i_xOverride FALSE) re-arms the override *)
    xOvrdDenied : R_TRIG;           (* Rising edge of an override request the interlock refuses, for one-shot logging *)
"""

OVRD_ACTION_TEMPLATE = """    <Action Name="ACT_Override" Id="{{{guid}}}">
      <Implementation>
        <ST><![CDATA[(* Manual override handling (conv_eeb5d87743fc: an override is time-qualified, self-clearing and
   never a bypass of safety interlocks).
   - Qualification: i_xOverride (EPICS OVRD_ON) must be held continuously for tOvrd (tonOvrd), which
     protects against blips.
   - Self-clearing: once honoured the override expires after tOvrdMax (tonOvrdMax). The operator asks
     for a new one by dropping and re-raising i_xOverride; a dropped request re-arms the timer.
   - No interlock bypass: xOvrdActive is only ever ANDed with the interlock permit by the supervisory
     section, so the override can drop the vacuum-logic command but can never run the pump while the
     interlocks are not satisfied.
*)

(* A dropped request re-arms the override, so the operator can request a fresh one *)
IF NOT iq_stPTM.i_xOverride THEN
    xOvrdExpired := FALSE;
END_IF

//Qualification timer: the request must persist for tOvrd before it is honoured
tonOvrd(IN:= iq_stPTM.i_xOverride AND NOT xOvrdExpired, PT:= tOvrd);
xOvrdQualified := tonOvrd.Q AND iq_stPTM.i_xOverride AND NOT xOvrdExpired;

//Self-clearing duration: an active override never stays on indefinitely
tonOvrdMax(IN:= xOvrdQualified, PT:= tOvrdMax);
rtOvrdExpired(CLK:= tonOvrdMax.Q);
IF rtOvrdExpired.Q THEN
    xOvrdExpired := TRUE;
    //Log
    fbLogger(sMsg:='Override cleared: maximum override duration elapsed', eSevr:=TcEventSeverity.Warning);
END_IF
xOvrdActive := xOvrdQualified AND NOT xOvrdExpired;

//Log an override request that the interlock refuses: the override never replaces the permit
xOvrdDenied(CLK:= xOvrdActive AND NOT iq_stPTM.xExtRunOk);
IF xOvrdDenied.Q THEN
    fbLogger(sMsg:='Override request refused, pump interlock not satisfied, pump stays stopped.', eSevr:=TcEventSeverity.Warning);
END_IF]]></ST>
      </Implementation>
    </Action>
"""


def read(path):
    with io.open(path, "rb") as handle:
        return handle.read().decode("utf-8")


def write(path, text):
    with io.open(path, "wb") as handle:
        handle.write(text.encode("utf-8"))


def replace_once(text, old, new, label):
    # normalise the search strings to CRLF to match the on-disk files
    old_crlf = old.replace("\r\n", "\n").replace("\n", "\r\n")
    new_crlf = new.replace("\r\n", "\n").replace("\n", "\r\n")
    count = text.count(old_crlf)
    if count != 1:
        raise SystemExit("%s: expected 1 match, found %d" % (label, count))
    return text.replace(old_crlf, new_crlf, 1)


def patch_file(path, header_anchor, header_replacement, var_anchor, body_anchor,
               body_replacement):
    text = read(path)
    # 1. header comment
    text = replace_once(text, header_anchor, header_replacement, path + " header")
    # 2. override VAR block
    text = replace_once(text, var_anchor, var_anchor + "\r\n" + OVRD_VARS, path + " vars")
    # 3. supervisory section
    text = replace_once(text, body_anchor, body_replacement, path + " body")
    # 4. ACT_Override action
    action = OVRD_ACTION_TEMPLATE.format(guid=str(uuid.uuid4()).upper())
    text = replace_once(text, "  </POU>", action + "  </POU>", path + " action")
    write(path, text)
    print("patched " + path)


# ---------------------------------------------------------------- FB_PTM_Ebara_010M
path = BASE + "FB_PTM_Ebara_010M.TcPOU"
patch_file(
    path,
    header_anchor=""" Turns off pump in the event of errors/ warnings. Provides interlocking interface.
TESTMARKER*)""",
    header_replacement=""" Turns off pump in the event of errors/ warnings. Provides interlocking interface.
""" + OVRD_POLICY + " *)",
    var_anchor="    TOF_SetSpeed: TON :=(PT:=T#1S);",
    body_anchor="""(* Simple protection reset *)
iq_stPtm.xExtRunOk:= i_xExtILKOk AND NOT iq_stPTM.i_xFault;
iq_stPTM.q_xProtection:= TRUE;//iq_stPTM.xExtRunOk;
(*soft IO mapping*)
ACT_IO();

(* Basic pump supervisory section *)
    (* If override mode, ignore everything else *)
IF iq_stPTM.i_xOverride THEN""",
    body_replacement="""(* Simple protection reset *)
iq_stPtm.xExtRunOk:= i_xExtILKOk AND NOT iq_stPTM.i_xFault;
iq_stPTM.q_xProtection:= TRUE;//iq_stPTM.xExtRunOk;
(*soft IO mapping*)
ACT_IO();

(* Manual override handling: qualification, self-clearing and refused-request logging *)
ACT_Override();

(* Basic pump supervisory section *)
    (* If the qualified override is active AND the interlock permit (xExtRunOk) is satisfied, the
       operator's run command drives the pump. The override never bypasses the interlock: the permit
       is part of this condition, so a lost permit falls through to the fault/hysteresis branches. *)
IF xOvrdActive AND iq_stPTM.xExtRunOk THEN""",
)

# ---------------------------------------------------------------- FB_PTM_Ebara_011M
path = BASE + "FB_PTM_Ebara_011M.TcPOU"
patch_file(
    path,
    header_anchor="""(* This function block does basic controls FOR the Ebara Turbo pump connected to the ETC011M Controller.
 Turns off pump in the event of errors/ warnings. Provides interlocking interface.*)""",
    header_replacement="""(* This function block does basic controls FOR the Ebara Turbo pump connected to the ETC011M Controller.
 Turns off pump in the event of errors/ warnings. Provides interlocking interface.
""" + OVRD_POLICY + " *)",
    var_anchor="    TOF_SetSpeed: TON := (PT:=T#1S);",
    body_anchor="""(* Simple protection reset *)
iq_stPtm.xExtRunOk:= i_xExtILKOk;
iq_stPTM.q_xProtection := TRUE;//iq_stPTM.xExtRunOk;

(*soft IO mapping*)
ACT_IO();

(* Basic pump supervisory section *)
    (* If override mode, ignore everything else *)
IF iq_stPTM.i_xOverride THEN""",
    body_replacement="""(* Simple protection reset *)
iq_stPtm.xExtRunOk:= i_xExtILKOk;
iq_stPTM.q_xProtection := TRUE;//iq_stPTM.xExtRunOk;

(*soft IO mapping*)
ACT_IO();

(* Manual override handling: qualification, self-clearing and refused-request logging *)
ACT_Override();

(* Basic pump supervisory section *)
    (* If the qualified override is active AND the interlock permit (xExtRunOk) is satisfied, the
       operator's run command drives the pump. The override never bypasses the interlock: the permit
       is part of this condition, so a lost permit falls through to the fault/hysteresis branches. *)
IF xOvrdActive AND iq_stPTM.xExtRunOk THEN""",
)

# ---------------------------------------------------------------- FB_PTM_Ebara (legacy)
path = BASE + "FB_PTM_Ebara.TcPOU"
text = read(path)
# header
text = replace_once(
    text,
    """(* Ebara ETC control FB
Scott Stubbs & Alex W.
*)""",
    """(* Ebara ETC control FB
Scott Stubbs & Alex W.

""" + OVRD_POLICY + """
*)""",
    path + " header",
)
# logger (this legacy block does not extend FB_Pump, so it owns its logger)
text = replace_once(
    text,
    """VAR
    TOF_START: TOF := (PT:=T#0.5S); //Manual states momentary switches need to be closed for >= 0.3s""",
    """VAR
    (* Shared logger: the override self-clearing events are reported through it *)
    fbLogger : FB_LogMessage := (eSubsystem:=E_SubSystem.VACUUM);
""" + OVRD_VARS + """    TOF_START: TOF := (PT:=T#0.5S); //Manual states momentary switches need to be closed for >= 0.3s""",
    path + " vars",
)
# body
text = replace_once(
    text,
    """(* Simple protection reset *)
IF iq_stPTM.xExtRunOk THEN
    iq_stPTM.q_xProtection:=TRUE;
END_IF

(* Basic pump supervisory section *)
    (* If override mode, ignore everything else *)
IF iq_stPTM.i_xOverride THEN""",
    """(* Simple protection reset *)
IF iq_stPTM.xExtRunOk THEN
    iq_stPTM.q_xProtection:=TRUE;
END_IF

(* Manual override handling: qualification, self-clearing and refused-request logging *)
ACT_Override();

(* Basic pump supervisory section *)
    (* If the qualified override is active AND the interlock permit (xExtRunOk) is satisfied, the
       operator's momentary start/stop switches drive the pump. The override never bypasses the
       interlock: the permit is part of this condition, so a lost permit falls through to the
       fault branch. *)
IF xOvrdActive AND iq_stPTM.xExtRunOk THEN""",
    path + " body",
)
action = OVRD_ACTION_TEMPLATE.format(guid=str(uuid.uuid4()).upper())
text = replace_once(text, "  </POU>", action + "  </POU>", path + " action")
write(path, text)
print("patched " + path)
