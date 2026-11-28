# Fast shutter (VFS) interlock contract

Scope: `FB_VFS` and `FB_VFS_2OO3` (`L2SIVacuum/POUs/Functions/Valves/`), the soft-IO interfaces
`FB_VFS_Interface` / `FB_VFS_2OO3Interface`, and the PMPS split between the fast shutter and the gate
valve that guards the same vacuum section (`FB_VGC`).

This page states what the fast shutter function blocks **do** enforce, and — equally important — what they
do **not** enforce, so that an integrator does not wire an interlock to an input that has no effect.

## Why the fast shutter is separate

The fast shutter logic runs in its own virtual PLC task bound to the FAST I/O portion of the EtherCAT bus
so the shutter can be scanned much faster than the rest of the vacuum I/O (tested with a PLC task base
time of 50 us). Everything that needs an arbiter, a beam-rate transition or a multi-second qualification
therefore lives in the slow valve logic (`FB_VGC`), not here.

## What `FB_VFS` enforces

Close interlock (evaluated once per cycle):

| Condition | Effect |
| --- | --- |
| `i_xTrigger` TRUE (CC gauge fast TTL output) | shutter is driven closed |
| `i_xPress_OK` FALSE (gauge not connected) | shutter is driven closed |
| `i_xExt_OK` FALSE (general external permit lost) | shutter is driven closed |
| `i_xCLS_SW` TRUE (external/EPICS close command) | shutter is driven closed |
| `xVeto` TRUE (veto valve closed, `i_xVeto_Enable` set) | **close interlock is vetoed**, no close from the three conditions above |
| `tonOvrd.Q AND i_xOverrideMode` | close interlock is overridden for the qualified override window |

The close pulse (`q_xClose_A/B/C`) is held until the close limit switch `i_xClsLS` is made or the
`CloseTimer` (`T#20MS`) expires.

Open path: a rising edge on `i_xOPN_SW` with `xOPN_OK` TRUE and the shutter not yet open drives
`q_xOPN_DO`; `q_xOPN_DO` is released when `i_xOpnLS` has been made for `OpenTimDur` (`T#2S`). The
qualified override (`tonOvrd.Q AND i_xOverrideMode`) can also open the shutter.

Fast (MPS) fault: `q_xMPS_OK := i_xOpnLS AND ((NOT i_xTrigger AND i_xPress_OK) OR xVeto) AND NOT i_xCLS_SW`
is fed to `FB_FastFault` (`fbFF`, type code `16#1010`, device name from `i_sDevName`, auto reset). An
open shutter that is no longer reported open therefore trips the MPS fast fault output.

Neighbour coordination: `q_xVAC_FAULT_OK` is TRUE when the shutter is open and neither triggered nor in
external fault. Neighbouring gate valves link their own `i_xExt_OK` to this output, so a shutter fault
closes the gate valve.

Diagnostics: `q_eVFS_State` (`E_VGC`) reports `Triggered`, `Vac_Fault`, `Cls_Timeout`, `Opn_Timeout` or
`At_Vac`; move timeouts are `T#0.5S` (close) and `T#10S` (open).

`FB_VFS_2OO3` behaves the same way with a two-out-of-three gauge vote: the trigger `xTrigger` is TRUE
when at least two of the three CC gauge fast TTL inputs triggered (or at least two gauges are no longer
connected), and the close interlock is `xTrigger OR NOT i_xExt_OK`. Per-gauge fault counters
(`q_nFltCount_IG*`) are provided for diagnostics.

## What `FB_VFS` does **not** enforce: PMPS

**PMPS (personnel machine protection) is not evaluated by `FB_VFS` or `FB_VFS_2OO3`.**

Both blocks declare `i_xPMPS_OK`, but the variable is not read anywhere in the implementation, and it
has no influence on the close interlock, on `q_xMPS_OK`/`fbFF`, or on `q_xVAC_FAULT_OK`. The input is
retained only for call compatibility and is marked `{attribute 'obsolete'}` so that a caller connecting a
PMPS permit to it gets a compiler warning instead of silent, non-functional protection.

PMPS arbitration cannot run in the fast task: it needs `BeamParameterTransitionManager` plus
`FB_Arbiter` and a transition timeout, which is why it is implemented in the gate valve
(`FB_VGC.i_xPMPS_OK` → `ACT_PMPS`). `FB_VGC` requests the beam transition for the device, gates opening
of the gate valve on `xPMPS_OK`, and drops the open command when the permit/`xOPN_OK` conditions are lost.

### Wiring PMPS for a fast shutter line

To have PMPS protection on a fast shutter line, wire it where it is actually evaluated:

1. Wire the PMPS permit/arbiter result to the `FB_VGC` gate valve that guards the same vacuum section:
   `FB_VGC.i_xPMPS_OK` (TRUE = no PMPS interlock required).
2. Give that `FB_VGC` its arbiter instance (`fbArbiter`), transition root ID (`i_nTransitionRootID`) and
   device name (`i_sDevName`) so `ACT_PMPS` can request the beam-rate transition.
3. Link `FB_VGC.i_xExt_OK` to this shutter's `q_xVAC_FAULT_OK` so a shutter fault also closes the gate
   valve, and link the shutter's `q_xMPS_OK` through `FB_VFS_Interface.i_xMPS_OK` for the MPS display.
4. Leave `FB_VFS.i_xPMPS_OK` unwired. It has no effect; a shutter is neither closed nor fast-faulted on
   PMPS loss alone.

## Wiring checklist for `FB_VFS`

| Signal | Wire to |
| --- | --- |
| `i_xTrigger` | fast TTL output of the CC gauge controller (fixed I/O link) |
| `i_xPress_OK` | `IG.xPRESS_OK` of the same gauge, so a disconnected gauge closes the shutter |
| `i_xExt_OK` | general external permit for the section |
| `i_xVeto_Enable`, `i_xVetoValveOpenDO`, `i_xVetoValveClosed` | the veto valve guarding this shutter |
| `io_fbFFHWO` | `FB_HardwareFFOutput` instance of the fast fault chain |
| `i_xVAC_FAULT_Reset` | fast-fault reset (`FF_Reset`) |
| `i_xOverrideMode` / `i_xOverrideOpen` | global override bit / per-device override request (10 s qualification) |
| `i_xPMPS_OK` | **not used** — see above |

## Known limitations

- `i_xPMPS_OK` has no effect in `FB_VFS` / `FB_VFS_2OO3` (documented above; the input is deprecated).
- Neither fast shutter block has a TcUnit test under `L2SIVacuum/UnitTests/Valves/` yet.

## History

- 2025-11-28: document created while reconciling the PMPS contract of `FB_VFS`
  (`i_xPMPS_OK` declared but never evaluated, stale "check if PMPS" and "first PLC pass vented state"
  comments).
