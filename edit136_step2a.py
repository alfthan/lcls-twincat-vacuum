"""Task #136 step 2a: FB_VGC_2S -> single VAR_IN_OUT ST_VGC_2S interface."""
import re
from edit136_lib import apply, qualify_map, replace_once

PATH = 'L2SIVacuum/POUs/Functions/Valves/FB_VGC_2S.TcPOU'

NEW_INOUT = '''VAR_IN_OUT
    (* Single command/status interface of this valve. The caller owns the
       struct instance and links its members to the field I/O, so the block
       exposes neither a VAR_OUTPUT struct nor individual AT%I*/AT%Q* terminals.
       Commands (OPN_SW, ALM_RST, FORCE_OPN, Dis_DPIlk) and permits (EXT_OK,
       EPS_OK, PMPS_ILK_OK, OVRD_ON) all live in this struct. *)
    iq_stValve    :    ST_VGC_2S;
    io_fbFFHWO    :    FB_HardwareFFOutput;
    fbArbiter: FB_Arbiter();
END_VAR
VAR_INPUT
    (*Upstream Gauge, usually ion gauge*)
    i_stUSG : ST_VG;
    (*Downstream Gauge, usually ion gauge*)
    i_stDSG : ST_VG;
    i_xIsAperture:BOOL :=FALSE; // Set tp True if this is an Aperture Valve, the MPS Fault will trip only when moving.
    i_sDevName : T_MaxString :=  'VGC'; // Device name for diagnostic
    i_nTransitionRootID: UDINT; //A unique transition Root ID that is equal to or greater than 1000
END_VAR
'''

NEW_IO = '''    (* The field I/O is wired by the caller onto the interface-struct members
       i_xOpnLS, i_xClsLS and q_xOPN_DO, so no terminals are declared here. *)
    (* Latched copy of the alarm-reset command, see the body *)
    xResetPulse : BOOL;
'''

NEW_ACT_IO = '''(* The caller links the interface-struct members to the field I/O, so there is
   no terminal mapping left to do here. Only the diagnostic device names are
   published into the interface struct. *)
iq_stValve.sDevName := i_sDevName;
iq_stValve.sIlkUSDeviceName := i_stUSG.sPath;
iq_stValve.sIlkDSDeviceName := i_stDSG.sPath;
'''

BODY_MAP = {
    'i_xExt_OK': 'iq_stValve.xEXT_OK',
    'i_xEXT_OK': 'iq_stValve.xEXT_OK',
    'i_xDis_DPIlk': 'iq_stValve.xDis_DPIlk',
    'i_xPMPS_OK': 'iq_stValve.xPMPS_ILK_OK',
    'i_xOverrideMode': 'iq_stValve.xOverrideMode',
    'i_xOpnLS': 'iq_stValve.i_xOpnLS',
    'i_xClsLS': 'iq_stValve.i_xClsLS',
    'q_xOPN_DO': 'iq_stValve.q_xOPN_DO',
    'xMPS_OK': 'iq_stValve.xMPS_OK',
}


def edit(text):
    # 1. Collapse the three declaration sections into one VAR_IN_OUT + VAR_INPUT.
    text, n = re.subn(
        r'VAR_IN_OUT\n\nEND_VAR\nVAR_INPUT\n.*?\nEND_VAR\nVAR_OUTPUT\n.*?\nEND_VAR\nVAR_IN_OUT\n'
        r'    io_fbFFHWO    :    FB_HardwareFFOutput;\n    fbArbiter: FB_Arbiter\(\);\nEND_VAR\n',
        NEW_INOUT, text, count=1, flags=re.S)
    assert n == 1, 'declaration regions not found'

    # 2. Drop the individual AT%I*/AT%Q* terminals.
    text, n = re.subn(r'    \(\*IO\*\)\n(?:[^\n]*\n)*?[^\n]*q_xOPN_DO\tAT%Q\*: BOOL;\n',
                      NEW_IO, text, count=1)
    assert n == 1, 'AT terminal block not found'

    # 3. Re-point every command/status reference at the interface struct.
    text = qualify_map(text, BODY_MAP)

    # 4. Replace the terminal-mapping action.
    text, n = re.subn(r'(<Action Name="ACT_IO".*?<ST><!\[CDATA\[).*?(\]\]>)',
                      lambda m: m.group(1) + NEW_ACT_IO + m.group(2), text,
                      count=1, flags=re.S)
    assert n == 1, 'ACT_IO action not found'

    # 5. Latch the reset command and feed it to the fast-fault output.
    text = replace_once(
        text,
        'fbFSInit( CLK := TRUE, Q => xFirstPass);\n(*IO Mapping*)\nACT_IO();',
        'fbFSInit( CLK := TRUE, Q => xFirstPass);\n'
        '(* Latched reset command: ACT_ResetAlarms clears the struct member later in\n'
        '   this cycle, so the fast-fault output needs the copy taken here. *)\n'
        'xResetPulse := iq_stValve.pv_xAlmRst;\n'
        '(*IO Mapping*)\nACT_IO();')
    text = replace_once(
        text,
        'FFO(i_xOK := iq_stValve.xMPS_OK,\n    i_xReset := i_xReset,',
        'FFO(i_xOK := iq_stValve.xMPS_OK,\n    i_xReset := xResetPulse,')

    # 6. Header note about the interface refactor.
    text = replace_once(
        text,
        '(*This function block also implements PMPS and EPS interlocks, as well as Fast MPS trigger*)',
        '(*This function block also implements PMPS and EPS interlocks, as well as Fast MPS trigger*)\n'
        '(* History: 2026-11-27 all command/status data of this valve was consolidated into the\n'
        '   single VAR_IN_OUT ST_VGC_2S interface struct (audit finding #1019); the permits and\n'
        '   the DP-interlock disable moved from individual VAR_INPUTs into that struct. *)')
    return text


apply(PATH, edit)
