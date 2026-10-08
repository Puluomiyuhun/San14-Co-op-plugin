# Planning input interlock: same Owner, fresh bounded consumers

2026-10-08. Offline only: no game discovery/access, Steam, UI, current saves, live scripts or Git operations. All fixture children exited. Frozen predecessors were not edited.

## What is implemented

The previous Ready worker observed only the real User suppression callback. The new native Controller coordinates that same retained `a_reward_save_owner` User/Save Owner with the existing upstream Game/global UI/direct-panel Gate. It installs no additional hook and does not create a second User Owner.

Link `planning_input_interlock_gate.cpp` **instead of** `a_save_upstream_gate.cpp`, with `planning_input_interlock.cpp`. The gate successor keeps the predecessor's publication/source/exception logic and adds `MatchesOwner`: it checks its retained exact Save Owner pointer, native binding, base/root/world, current root->world and the actual pinned source bytes. `planning_input_interlock_gate.h` is the same class ABI with this additional method. Do not link both Gate implementations. Existing reward Owner, bridge, owned replay and storage sources are unchanged.

The Controller additionally reads the actual four published vtable slots from the real hook reports; cached HookSet publication flags alone are insufficient. Source conflict never overwrites the foreign slot. Retained world address, date and viewer are pinned; a same-address new date is not the same planning boundary.

API in `planning_input_interlock.h`:

- `Initialize(Config)`: exact Owner/Gate pair, healthy clean reports, trusted current execution thread, immutable binding/world. One retained lifecycle; no network-provided addresses.
- `Request(value, revision, duplicate)`: coordinates existing User ReadyFence and Game Gate Hold. External Ready revision is mapped to a separately advancing actual Gate revision (the Gate can already have revision 1). Identical duplicate does not advance either revision; stale/conflicting requests refuse. Save/reward queue/active/hold/error/uncertain states refuse.
- `BeginObservation(revision)`, then actual published Game and User callbacks, then `EndObservation(revision)`: fresh reports must show one Game FINALLY, one suppressed global UI, one suppressed panel, one suppressed User FINALLY, and zero original User start/return increments, no forwarding/error/abnormal/cleanup changes, no active/queued scope and unchanged identity/revisions. There is no callback-counter input from the caller. Methods are pinned to the trusted execution thread; the caller still owns scheduling of these actual callbacks. The deltas are the existing bridges' aggregate counters, not new per-thread event receipts. Apply this API only inside a trusted scope that already binds/schedules the Game and User sources on the intended owner thread and excludes concurrent reuse of those same observed slots. The Controller does not itself establish that production scheduler exclusion; it cannot infer it from a total of one. The owned worker is serial and invokes both callbacks itself.
- `Snapshot`: reports current native facts; identity/revision/slot changes or non-clean state clear previous coverage. This is a point read, not a continuous all-thread lock.
- `AuthorizeFullBoundary`: always rejects and returns the fixed unresolved mask. No caller boolean or mask can fill the unknown sources.

Closing fences User first, then requests Gate hold; opening releases Gate first while User remains fenced. Partial failure is terminal `uncertain`, with no false rollback or successful observation. There is no automatic release/retry or source restoration. Existing Gate sticky failure can stop its Save Owner and transparently forward originals; **terminal fault is not a promise that physical inputs remain globally stopped**. Neither the old modules nor this Controller provide that guarantee.

## Coverage and remaining writers

`coverage=7` means only User (1), global UI in the observed Game scope (2), and that Game's direct panel consumer (4). It is earned from the current physical callbacks, never from the setter.

`missing=31` permanently records WindowMessages (1), RootConversion (2), DeviceCaches (4), ExternalConsumers (8), BackgroundWriters (16). WndProc/message conversions, keyboard/mouse/controller device polling, Root cache conversion, direct external consumers and asynchronous world/report writers have not become covered here. Suppression of raw User skips its whole body; no original-User-return Save evidence is fabricated. A real Save must leave the Ready fence through a separately coordinated lifecycle; full save admission and producer drainage remain unresolved.

`allInputHeld`, `roomReady`, `saveAuthorized`, `nativeGameplayEnabled` are always false. This component cannot authorize actual simulation, a full-input Ready boundary or a production checkpoint. It is a concrete bounded interlock and a hard refusal for the remaining scope, not complete pause support.

## One planning-period scope; no hidden reset

This Controller pins the date and viewer at initialization. The existing reward `Bind` is one-time, and its `ph::Binding` period/epoch are immutable. Therefore this is a single planning-period scope, not a reusable cross-turn session. A same-address next date invalidates the old evidence. Creating another Controller cannot legitimize reuse: nonzero existing Ready revision is refused by Initialize. No reset, old-claim deletion or attachment reuse is supplied. A formal retire/rebind successor for the Owner/reward lane, with actual source/world lifecycle, is still required before consecutive turns can use this component. This limit is separate from whether ordinary old Game/User callbacks keep executing.

## Persistent owned worker

Use the final run directory as cwd, with `reward.dll` and `checkpoint_planning_hold.dll` beside the executable:

```text
fixture.exe worker <exclusive-scratch> d3f36ec70d858c14c0d83ceaef567f7e8dabcb0dece1debc309b2ffc04d1b327
fixture.exe worker-b <other-scratch> d3f36ec70d858c14c0d83ceaef567f7e8dabcb0dece1debc309b2ffc04d1b327
```

The two persistent worlds retain the previous fixture's forces 12 and 2, viewer 12/2, fixture ruler 500, resources and owned native reward replay. They are two self-built processes, not two games. Business effects, Game/User/Save implementations and source snippets remain explicit fixture doubles; publication, bridge/TLS/SEH, exact owner identity, deep reward replay and native reports execute for real in the owned process.

JSON-lines `sample`, `reward`, `close`, `ready_fence(value,revision)` and `fence_sample(revision)` remain compatible. `fence_sample` now dispatches real Game, then real User, within the Controller observation window. Setter replies—including duplicate setters after a prior successful observation—always have `observed=false`, `observed_revision=0`, `input_coverage_mask=0` and per-observation deltas 0. Internal duplicate requests need not erase prior receipt history; a new fresh sample is still required by the caller. `input_observation` is an absolute historical serial, not evidence that the setter observed anything.

New response fields:

- `input_coverage_mask` (7 only for successful observed reply), `input_missing_mask` (31).
- `input_interlock_uncertain`, `input_interlock_error`, `input_gate_revision`, `input_observation`.
- `game_finally_delta`, `global_ui_suppressed_delta`, `panel_suppressed_delta` (each 1 for this successful observation, otherwise 0).
- Explicit `save_authorized=false`, alongside the prior false all-input/room/full-world/gameplay fields.

The old User evidence retains `user_native_started_delta=0`, `user_native_returned_delta=0`, `user_finally_delta=1`, `held_delta=1`. Root may conservatively project this into its previous signed User-only Ready schema while retaining the expanded bounded facts locally; it must not silently promote old signatures to cover additional sources.

## Verification

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<local private mod_research directory>'
py -3 work/mod_research/planning_input_interlock_test.py
```

Requires MSVC/MASM, private `checkpoint_push_profile.h` and the predecessor PlanningHold library/DLL. The runner only builds production objects and self-owned fixtures; it does not discover or attach to a game.

Final `planning_input_interlock_runs/20261008-201256-271268/result.json`: **18/18 PASS**, 54 source hashes unchanged and independently rechecked. Schema `san14.planning-input-interlock-owned.v1`.

- Ten new direct cases: missing Game, missing User, wrong thread, wrong retained Owner, gate revision drift before/after observation, same-address date change, actual published User slot replacement, explicit full-scope refusal and explicit release with real original User/UI/panel forwarding.
- Six predecessor Ready conflict cases: queued reward, actual Save, active reward callback, uncertain cancellation, world change, and original User callback not mistaken for suppression.
- Two persistent worker views: real reward, setter/duplicate, repeated fresh Game+User samples, stale/conflicting setters, blocked command, explicit release and next real reward.
- Production Gate and Controller compile without fixture macros. The persistent worker and its callbacks are owned fixture execution, not a production bootstrap.

Result SHA256: `93b429181400491be4922741c66fe762f9140253f0996e43afd03b35e584c9d1`.
Fixture SHA256: `d3f36ec70d858c14c0d83ceaef567f7e8dabcb0dece1debc309b2ffc04d1b327`.
Production library SHA256: `2e3d3b56756cc499006d8c8a56d22b649e230337970a4039b3bdc09a81937d52`.
The result also records PlanningHold/reward DLL hashes and all source hashes.

Retained intermediate records:

1. `200830-336065`: 14/15; release test wrongly compared the forwarded original User sentinel to the suppression return 0. Changed only the fixture to use the existing original-return validator.
2. `201006-263680`: 15/15; then added post-observation gate/date drift tests and explicit result scope flags.
3. `201057-790320`: 17/17; self-review then added real slot reread and its replacement negative test.
4. `201217-582431`: production compiled; fixture compile rejected volatile pointer passed to VirtualProtect. Explicit fixture-only cast corrected; no runtime case ran.
5. `201256-271268`: final 18/18; all frozen predecessor source hashes remain unchanged.

Next: root integrates the source-pinned extended worker port with the existing real TLS/two-journal Ready tests. Production scheduler/bootstrap, full input and writer closure, actual Save/Load continuity and real games remain separate requirements. No user action is requested by this offline change.
