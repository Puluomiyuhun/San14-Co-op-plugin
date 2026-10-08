# Held checkpoint: native pipe and explicit planning/save phase identity

Status: production build PASS; flow 6/6 PASS, zero skipped. All work is offline:
owned Windows child, diagnostic files and real loopback TLS. No game, Steam,
current save, UI, live installer or debugger. Frozen predecessors are unchanged.

## What is connected

`a_save_held_ipc.*` is an explicit successor to the frozen pipe Server. It keeps
wire ABI/client, kernel peer identity, PID/secret authentication, monotonic sequence,
consume-before-submit, exact artifact matching, and shutdown behavior. Config now
requires trusted Submit and Copy callbacks together (and the existing permit).
Callbacks are configured by the host, never supplied by the network. There is no
fallback to ordinary Owner Submit and no production game-thread marshaler yet.

The owned fixture links `planning_checkpoint_save_owner.cpp`, `_gate.cpp`,
`_interlock.cpp` and `planning_checkpoint_save.cpp` instead of their predecessors.
It runs the pipe on its own initialized main thread. The callbacks actually call
held Submit, the diagnostic User/Save path and held Copy; Ready/Gate remain held
at revision 1. Missing Copy is refused before opening; ordinary Submit still
refuses Ready. This is one diagnostic native save, not two game periods.

`checkpoint_planning_save_link.py` captures complete A planning scope, attachment
and contract before RUNNING. Under Room then Coordinator locks it verifies the
same epoch/period/start date, no pending event, seal and cut; it consumes its one
attempt before native reservation. The checkpoint date must be next_node(start).
Its immutable context distinguishes old planning identity from saved end date.
It grants no save, full-input or simulation authority and cannot mint next epoch.

## Important remaining composition gap

The prior `a_save_period_ipc` native fixture started local period 1 at day 11,
whereas its network coordinator started day 1 and published a day-11 checkpoint.
That exercised transfer, not an integrated native simulation/date transition.
With full Session scope the planning Controller is pinned to day 1. After actual
simulation, day 11 cannot simply reuse that observation or impersonate period 2:
network period 2 exists only after B has loaded and reconciliation completed.

This turn makes both dates explicit, and fixes saving under Ready for the
**current native date**. The flow deliberately initializes the native primitive
at day 11 while retaining a separate network day-1 scope. It records
`native_post_simulation_phase_composed=false`. Next implement an explicit native
post-simulation boundary under the original epoch, then integrate full Session,
known input hold, production game-thread scheduling and actual save coordination.
Do not loosen old date guards or fabricate the next scope to pass the test.

## Reproduction and evidence

From repository root with existing private fixture inputs:

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research'
py -3 work/mod_research/a_save_held_ipc_build.py
py -3 work/mod_research/a_save_held_ipc_flow_test.py --build-run work/mod_research/a_save_held_ipc_build_runs/20261008-223842-685108
```

Use the newly produced build-run on another machine; the recorded path identifies
this result only. Build uses 64 pinned sources; flow pins 17 plus build identity.

- Build: `a_save_held_ipc_build_runs/20261008-223842-685108/result.json`, SHA-256
  `b76e427d7166126997350ababbb8b7d79444347438df49a54e8581ee8745737f`.
- Flow: `a_save_held_ipc_flow_runs/20261008-223928-954673/result.json`, SHA-256
  `fef018201ede58abe893bc3886b38dec52684d36071a3fa68a1fcbf2aef3a738`.
- Native fixture SHA-256
  `2899f49d1c32fe9d95b3ae12438c157fd8b7a1015baeb62123a6e00402826db7`.

Three protocol tests cover planning-only capture, scope/attachment/event changes,
and consuming a failed reservation attempt. Three owned-pipe scenarios cover:
actual held native Save/Copy through TLS into guest SQLite STAGED/reopen; native
cut mismatch denied before Save; shutdown during permit with no backend call.
The successful save is 32 diagnostic bytes. B loaded is an explicit model input;
only that later input advances network epoch. Owned children and listeners close.
No root build/flow failure occurred; underlying held-save initial 19/22 failure
and its fix remain in that module's handoff. Cross-review found no blockers in
pipe preservation, lock order or phase mapping. Real save/load and full writer
exclusion remain unproved.
