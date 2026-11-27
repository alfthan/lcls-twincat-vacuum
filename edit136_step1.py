"""Task #136 step 1: extend the block-specific interface structs."""
from edit136_lib import apply, load, save

# ---------------------------------------------------------------- ST_VGC_2S
st_vgc_2s_new = '''
(* Command / permit data of the 2-setpoint gate valve. These used to be
   separate VAR_INPUTs of FB_VGC_2S; they live in the interface struct so the
   whole command/status set travels through one VAR_IN_OUT reference. *)
    {attribute 'pytmc' := '
    pv: Dis_DPIlk;
    field: ZNAM ILK ACTIVE ;
    field: ONAM ILK DISABLED ;
    io: io;
    '}
    xDis_DPIlk\t:\tBOOL := FALSE;\t// Command: disable the differential-pressure interlock
    {attribute 'pytmc' := '
    pv: EPS_OK;
    field: ZNAM NOT OK ;
    field: ONAM OK ;
    io: io;
    '}
    xEPS_OK\t:\tBOOL := TRUE;\t// Permit: external EPS interlock satisfied
    {attribute 'pytmc' := '
    pv: PMPS_ILK_OK;
    field: ZNAM NOT OK ;
    field: ONAM OK ;
    io: io;
    '}
    xPMPS_ILK_OK\t:\tBOOL;\t// Permit: external PMPS interlock satisfied
    {attribute 'pytmc' := '
    pv: MPS_FAULT_OK;
    field: ZNAM MPS FAULT ;
    field: ONAM MPS OK ;
    io: i;
    '}
    xMPS_OK\t:\tBOOL;\t// Status: MPS fast-fault OK for this valve
'''
apply('L2SIVacuum/DUTs/Valves/ST_VGC_2S.TcDUT', [
    ('\nEND_STRUCT\nEND_TYPE', st_vgc_2s_new + 'END_STRUCT\nEND_TYPE'),
])

# ------------------------------------------------------------------- ST_VFS
st_vfs_new = '''
(* Interface signals that used to be individual AT%I*/AT%Q* terminals of
   FB_VFS / FB_VFS_Interface. They are members of the interface struct so the
   caller links struct members and the block declares no terminals at all. *)
    {attribute 'pytmc' := '
    pv: PRESS_OK;
    field: ZNAM OFF ;
    field: ONAM ON ;
    io: i;
    \'}
    xPRESS_OK\t:\tBOOL;\t// Status: pressure OK bit published to veto/interlock consumers
    {attribute 'pytmc' := '
    pv: MPS_FAULT_OK;
    field: ZNAM MPS FAULT ;
    field: ONAM MPS OK ;
    io: i;
    \'}
    xMPS_OK\t\t:\tBOOL;\t// Status: MPS fast-fault OK, TRUE while open and untriggered
    {attribute 'pytmc' := '
    pv: PMPS_ILK_OK;
    field: ZNAM NOT OK ;
    field: ONAM OK ;
    io: io;
    \'}
    xPMPS_OK\t:\tBOOL;\t// Permit: external PMPS interlock satisfied
    i_xPress_OK\t:\tBOOL;\t// Permit: fast pressure sensor OK (link to the gauge xPRESS_OK)
    i_xVetoValveOpenDO\t:\tBOOL;\t// Veto valve open command readback
    i_xVetoValveClosed\t:\tBOOL;\t// Veto valve closed limit switch
    q_xClose_A\t:\tBOOL;\t// Redundant fast close command A
    q_xClose_B\t:\tBOOL;\t// Redundant fast close command B
    q_xClose_C\t:\tBOOL;\t// Redundant fast close command C
'''
apply('L2SIVacuum/DUTs/Valves/ST_VFS.TcDUT', [
    ('    xCLS_SW AT%Q*:BOOL; (*external open signal e.g epics*)',
     '    xCLS_SW : BOOL; (*external close signal e.g epics*)'),
    ('\nEND_STRUCT\nEND_TYPE', st_vfs_new + 'END_STRUCT\nEND_TYPE'),
])

# ------------------------------------------------- sibling of FB_Gauge struct
gauge_if = '''(* Interface struct for the generic gauge base block FB_Gauge.
   ST_VG is the block-specific gauge interface: it already carries the
   command bits (xHV_SW, xAutoOn) and the status (rPRESS, xPRESS_OK, xAT_VAC,
   eState, ...) of a gauge, so FB_Gauge reuses it instead of inventing a
   second gauge structure.

   History
   2026-11-27  Interface refactor: introduced so FB_Gauge carries its complete
               command/status set in one VAR_IN_OUT struct.
*)
TYPE ST_Gauge_Interface EXTENDS ST_VG:
STRUCT
END_STRUCT
END_TYPE'''
path = 'L2SIVacuum/DUTs/Gauges/ST_Gauge_Interface.TcDUT'
template = '''\ufeff<?xml version="1.0" encoding="utf-8"?>
<TcPlcObject Version="1.1.0.1">
  <DUT Name="ST_Gauge_Interface" Id="{7c1f8d2a-5b64-4f43-9f0e-2f0f2b6f6a11}">
    <Declaration><![CDATA[%s]]></Declaration>
  </DUT>
</TcPlcObject>
''' % gauge_if
open(path, 'wb').write(template.replace('\n', '\r\n').encode('utf-8'))
print('wrote', path)

# --------------------------------------------------------------- ST_VFS_2OO3
text, _ = load('L2SIVacuum/DUTs/Valves/ST_VFS_2OO3.TcDUT')
save('L2SIVacuum/DUTs/Valves/ST_VFS_2OO3.TcDUT', text, True)
print('normalised DUTs/Valves/ST_VFS_2OO3.TcDUT to BOM + CRLF')

# ------------------------------------------------------------------- plcproj
apply('L2SIVacuum/L2SIVacuum.plcproj', [
    ('    <Compile Include="DUTs\\Valves\\ST_VFS.TcDUT">\n      <SubType>Code</SubType>\n    </Compile>\n',
     '    <Compile Include="DUTs\\Valves\\ST_VFS.TcDUT">\n      <SubType>Code</SubType>\n    </Compile>\n'
     '    <Compile Include="DUTs\\Valves\\ST_VFS_2OO3.TcDUT">\n      <SubType>Code</SubType>\n    </Compile>\n'),
    ('    <Compile Include="DUTs\\Gauges\\ST_VG.TcDUT">\n      <SubType>Code</SubType>\n    </Compile>\n',
     '    <Compile Include="DUTs\\Gauges\\ST_VG.TcDUT">\n      <SubType>Code</SubType>\n    </Compile>\n'
     '    <Compile Include="DUTs\\Gauges\\ST_Gauge_Interface.TcDUT">\n      <SubType>Code</SubType>\n    </Compile>\n'),
])
