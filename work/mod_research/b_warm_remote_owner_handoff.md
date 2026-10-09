# Retained B owner: remote reservation to actual bridge and local sample

`b_warm_remote_owner.py` supplies the previously missing concrete callback
behind `RemoteGuestCompletion`. It keeps one warm Resident, one real
`WorldLifecycle`, one `BootstrapRulesBridge`/`WarmRulesBridge`, one process reader
and the same original B `RoomConnection`. It does not copy A's Room or
PeriodCoordinator, construct another bank owner, install a guard, attach a
process, or launch the game.

## Caller wiring

The caller first establishes the original native Resident, installed rules
port/lifecycle and actual external execution/input boundary using their existing
approved paths. Then create one owner and retain it for both checkpoints:

```python
from b_warm_adapter_key import load_key
from b_warm_remote_owner import RetainedRemoteOwner

key = load_key(private_key_path)  # Existing protected local file, no default key.
owner = RetainedRemoteOwner(
    existing_bootstrap_bridge, existing_B_control, key,
    scope=authenticated_scope,
    read_birth=read_actual_process_birth,
    observe_loaded=lambda request: retained_capture.capture_loaded(
        request, side='B', expected_ruler=selected_B_ruler),
    prepare_rules=retained_factory.prepare_rules,
    guard_check=existing_lifecycle_guard,
    on_hold=retain_existing_guard_and_invalidate_ready,
)

# Repeat only for the next distinct received checkpoint, using the same owner.
result = owner.apply(received_checkpoint, typed_native_request, typed_profile)
```

`retained_capture` and `retained_factory` can be the actual
`RemoteRulesWorldCapture`/`RemoteRulesFactory`. Bound callbacks retain their
Python owner references. The native request's epoch remains a locally chosen
generation identity, independent of the room wire epoch. The owner does not
construct an epoch or fill in a pretend target viewer. Fresh profiles remain
the existing typed local-capture responsibility.

The guard must be the identical callable already installed in
`WorldLifecycle._guard`. Its contract remains **return exactly None on verified
success, otherwise raise**, including repeated checks across the full operation.
`on_hold(reason)` likewise returns None or raises; a hold-callback error is
retained in `owner.hold_error`. `_verify_held()` converts the strict guard's
successful completion to the frozen remote client's boolean contract; it does
not establish an engine lock. Do not supply an empty callback in production.

## Concrete path and retained state

Before sending a remote begin, the owner checks the fixed bridge/lifecycle/
Resident/reader/control object graph, current PID and birth from `read_birth`,
image hash/base, current native rule Config's room/forces/districts/rules digest,
wire scope/epoch/attachment/period lineage, and actual old planning world/viewer/
profile-before date twice. It rejects replacement of the retained graph or an
unexpected root/world before requesting a host load intent.

`RemoteGuestCompletion` commits the actual SQLite reservation. Its local callback
is now `owner.apply_received(...)`, which requires the exact active transaction
objects and passes that reservation to actual `FormalBootstrapReceivedApply`
(or ordinary `ReceivedApply` for a plain Warm bridge). Those existing modules
perform real intent/file checks and call the actual bridge. The bridge restores
old rules, backs up and stages the received file, holds the actual Windows file
lease during warm load, observes the new world and prepares/installs a new
ResidentPort. Native behavior is supplied by the caller's existing warm and rule
ports, not reimplemented by this owner.

The owner calls the existing complete two-table `world.sample` before the
diagnostic ACK and again after its reply; both shared payload and binding must
remain identical. The resulting actual native completion and fresh sample feed
the remote client's existing signed compact witness and formal loaded path.
The diagnostic ACK is still not formal loaded. Sessions, samples, history,
three rule generations and both bank receipts remain retained; nothing resets
between period 1/bank 0 and period 2/bank 1.

After formal success only the local expected epoch, period and B attachment are
advanced from the paired authority reply and real completed Journal. Input is
not released. Any exception latches the whole owner HELD and calls its hold
port. This includes loss of a formal reply after A already advanced: the rules,
native receipts and completed Journal remain retained, and the owner never
loads again. Native load failure retains INTENT; the inherited bridge invokes
abort while the file lease remains held. File release does not prove native
drain. This module does not unload/reset modules or clear claims.

## Date semantics and remaining native boundary

The frozen `RemoteCompletionRoom` tests cover B waiting at the previous date
until A's new file arrives. The explicit `SettledRemoteCompletionRoom` tests
also cover an ordinary second correction whose truthful `profile.before` equals
the target date. The old rule Config remains immutable; its actual fresh export
advances in date, and existing ResidentPort restore accepts that date change.
The owner needs no date rewriting or permissive fallback for this case.

Neither test proves that a real independent B simulation retains the required
root/world and planning identities. If those change unexpectedly, `_before`
rejects; this owner does not silently rebind old rules. Actual game callbacks,
event handling and the guard that spans old-rule restore through new-rule
installation remain external dependencies. The current controlled no-new-command
diagnostic is not a substitute for the strict guard contract. The code does not
add a whole-world proof or global input implementation and must not be described
as an actual two-game runtime already running.

## Verification

Command from repo: `py -3 work/mod_research/b_warm_remote_owner_test.py`.

Final private result:
`../mod_research/b_warm_remote_owner_runs/20261009-201548-243238/result.json`

SHA256 `6af4ec2e7e9ecd3e13aaf684ae813cb39dcef41a0c0b6fe77972bd0c82a10056`.
6/6 PASS; 36 source hashes and 127 artifact hashes independently rechecked.

1. Same owner/Resident/lifecycle/reader: actual TLS receipt and Journal flow,
   bootstrap source12→target2 then ordinary bank1, protocol periods 1→2→3,
   original ResidentPort/WorldLifecycle predicates, three retained rule ports,
   two actual Windows backups, and diagnostic ACK plus formal loaded.
2. Formal reply deliberately lost after A accepted: A advances once while B's
   whole owner is HELD, retaining its two rule generations and completed Journal;
   another call performs no native replay.
3. Native load double fails: actual Windows writer exclusion is verified during
   abort, Journal remains INTENT, no ACK/loaded, no retry.
4. Changed process birth: refused before A creates an intent or B stages/loads.
5. Existing guard raises: refused before A creates an intent or B loads; hold
   callback invoked.
6. Explicit Settled room, same owner and actual bridge chain: second pre-load
   date equals target date; old immutable Config is retained while the fixture's
   fresh current export advances. Real restore predicates and bank1 succeed.

Native Save/load, game memory, rule publication and held boundary are explicit
test doubles. Real ResidentPort, WorldLifecycle, file staging, SQLite and TLS
execute unchanged. This composition suite keeps both TLS seats in one test
process; the separate frozen remote-completion suite covers a distinct B
process. Do not combine those claims into a new cross-process native-game run.
No game/Steam/UI, debugger or live patch was touched. No user action is needed
to run this offline suite.

The earlier `201352-086888` 5/5 result is retained before adding the settled-date
case. No test failed in this module's runs; prior artifacts were not rewritten.
Production source was unchanged between the two runs. Final source hashes:

- `b_warm_remote_owner.py`:
  `ee71f34aeb252a1f27fd4365e590a0bbfac9bf3b6658f025b3580fedaffe9cf9`
- `b_warm_remote_owner_test.py`:
  `8fa336cdbfce9eb3d3896d97a3e5540178bc69e70000e99a3fc6457dadd1137b`

Sibling review found no blocker in this bounded owner path. Root owns public
docs, integration and commit/push; no frozen predecessor was edited.
