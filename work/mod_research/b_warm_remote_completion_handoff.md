# Authenticated remote partial completion

The missing link was real: `b_warm_projection.TrustedProjection`,
`b_warm_bootstrap_protocol.BootstrapProjection` and
`CheckpointJournal.apply_to_coordinator` require a local `PeriodCoordinator`.
Their prior TLS tests still held A/B callbacks in one Python process.
`b_warm_room`'s `warm_load_diagnostic_ack` never calls `loaded()`; neither the
local named-pipe `checkpoint_session_channel` nor ReadyBarrier's process-local
action identities supplied a remote replacement.

`b_warm_remote_completion.py` now supplies that explicit successor. A alone
keeps its existing real coordinator, artifact service and immutable Save bytes.
B keeps its real downloaded files, bootstrap/ordinary SQLite journal and local
native owner. B does not construct or copy A's Room or Coordinator.

## Wiring

Use `RemoteCompletionRoom` where A previously constructed `WarmRoom`. After
both control seats and the initial coordinator are bound, trusted local startup
calls:

```python
room.enroll_adapter(
    adapter_key,  # 32 nonzero random bytes, provisioned privately to B's owner
    host_sampler=lambda profile, receipt_key: fresh_A_sample(profile, receipt_key),
    verify_held=check_actual_A_boundary,
    host_receipt_key=lambda: current_actual_A_Save_receipt_key,
    source_kind='LOCAL_NATIVE_PROVIDER',
)
```

On B, retain one `RemoteGuestCompletion(control, adapter_key,
verify_held=check_actual_B_boundary)`. Per received checkpoint:

```python
remote.apply(
    received, profile,
    guest_before=read_actual_old_attachment_viewer_boundary,
    apply_received=lambda permit: retained_local_owner.apply_received(
        received, request, profile, reservation=permit),
)
```

The local callback returns `{'completion': actual_accepted_Resident_completion,
'sample': fresh_b_warm_world_sample}`. This callback must retain the local
execution/input boundary and real native/rules lifetimes. The networking class
does not manufacture either. Scope and native epoch remain separate.

The read-only `warm_rules_binding` TLS action accepts no extra fields, only the
current B control connection, and returns the existing immutable scope with
native permission false. It checks the actual Room/Coordinator binding,
connections and held/closed state. `b_warm_remote_rules.py` consumes this to
avoid requiring an A-side Room instance on B.

## Actual sequence and uncertainty

1. B verifies its actual `ReceivedCheckpoint`, file and STAGED journal, then
   exclusively persists `remote-adapter-begin.json` before sending anything.
2. A authenticates the separate adapter credential in addition to current B
   TLS/control identity; checks the offered scope/file/profile/date/viewers;
   samples A's declared world projection; calls actual `received()` and
   `begin_guest_load()` once. B's signed assertion is evidence from its enrolled
   owner that its own Journal is staged; A reconstructs its own immutable sent
   bytes to satisfy the existing receiver interface, not a fabricated B RAM read.
3. B commits the actual SQLite INTENT, invokes its retained native owner once,
   validates native completion and B sample, and commits the actual Journal
   completion before transmitting the authenticated result.
4. B locally validates its entire projection before deriving a compact signed
   witness. A checks the original intent, native profile/process/viewer result,
   witness, exact receipt and fresh A sample. Only then it calls actual
   `PeriodCoordinator.loaded()`. It never turns a warm diagnostic ACK into a
   loaded receipt. A retains the exact completed body for bounded idempotence.
5. A's reply binds checkpoint and intent; B requires the expected contract,
   result and all three false authority flags before recording that reply.

The first source-view load requires period 1, no prior applied receipt and
`BootstrapCheckpointJournal`; later target-view loads use ordinary Journal.
There is no silent schema migration. One retained B adapter serializes apply
with its own lock. Unknown/failure latches B held. Existing begin/completion files
and SQLite INTENT/COMPLETED prevent native retry even if a new wrapper is made.
A completion failure holds A's coordinator. A local B native exception leaves
A's intent unresolved in RECONCILING; it cannot advance without a completion.
Disconnect already holds the inherited room. There is no reconnect or host
restart recovery. The in-memory A ledger has an explicit 16-checkpoint limit.

An identical completion can be returned idempotently while that original
control connection remains live; this does not run a load or advance again.
No automatic send retry is implemented. A reply lost after A applied loaded
leaves B uncertain, with its completed journal and one native invocation.

## Trust and coverage limits

The independent adapter key is not the room join credential. Its safe local
provisioning is a startup-coordinator responsibility, not a public network
enrollment endpoint. HMAC authenticates the enrolled local adapter's assertion;
it is not remote attestation of the DLL, game, or scheduling fence. A compromised
key/adapter can lie. Do not give this key to an untrusted generic room client.
All native evidence must still originate in retained B native/rules owners.

The wire preserves uint64 identities inside a bounded authenticated compressed
canonical body, avoiding the older room JSON integer bound. It enforces both a
256 KiB decompressed limit and the existing 64 KiB TLS packet limit. The fixed
`san14.authenticated-partial-witness.v1` has contract/build/date, shared projection
SHA, separate object/force byte SHA values, slot counts, exact native/context
binding and explicit false authority flags. Both complete tables are validated
at B before reducing to this witness. A independently validates its own fresh
full sample, derives the same witness and compares every shared witness field.
No raw table bytes or local RAM-address context are transmitted. This remains
an enrolled adapter's authenticated assertion; hashes do not prove a native
load or exclusion, nor can A reconstruct B's opaque table bytes from them.

The only state contract is the already declared two-table plus date partial
projection. File SHA is never used as world SHA. Protocol periods can advance
under that explicit contract; full-world verification, native gameplay and
Ready authority all remain false. A/B engine exclusion, command replay,
production native callback wiring, WAN deployment and actual two-game execution
are not proved by these tests. No live game was accessed.

## Verification

Run `py -3 work/mod_research/b_warm_remote_completion_test.py` from the repo.
Final private result:

`../mod_research/b_warm_remote_completion_runs/20261009-200139-981665/result.json`

SHA256 `87d186d74de618856f8db395ced712fe88b7fbfb16bbe3087b44edf02552be01`.
5/5 PASS, 31 source pins and 54 artifact pins all rechecked unchanged.

- Real pinned TLS/control/download, real FreshSaveBinding/artifacts and actual
  SQLite bootstrap period 1 followed by ordinary period 2; A's real loaded moves
  to periods 2 then 3. B is a separate Python child with a distinct PID and no
  Coordinator instance, retained across both loads. Completed-body duplicates
  do not advance again.
- Wrong independent adapter key: no A intent and zero local native callbacks.
- Correctly authenticated but wrong native viewer: one callback, no loaded,
  A HELD, no retry from the existing folder.
- Completion delivered to A but its reply deliberately lost at B: A advances
  once, B stays uncertain/COMPLETED, retry rejected and native callback count 1.
- Deterministic low-compressibility opaque bytes fill every audited field in
  both complete tables (24008 object bytes and 19656 force bytes) at separate
  A/B addresses. The real local sampler and TLS completion succeed. The old
  full-sample encoding reproduces a 69314-byte packet (over the 65536-byte
  transport limit); the new compact authenticated packet is 1518 bytes.

Save/native load, RAM contents and held-boundary callbacks are explicit doubles.
Each owned child is closed and waited for during teardown. Actual production
Resident/rules execution is not substituted into this new cross-process suite.
The earlier `195616-856479` 4/4 PASS is retained for its previous source, which
sent full tables and only happened to fit with repetitive fixture values.
Root's capacity finding is preserved as the explicit low-compressibility
regression above; it was a genuine missing wire-size case, not a native error.
Intermediate `200103-325924` 5/5 PASS is retained before the final strict
canonical binding/date validation. No prior result was rewritten. Final source
hashes:

- `b_warm_remote_completion.py`:
  `58582003bd059ae679129b5ed9439d0ad82ce15713b7c7bd027cd82a05b8c1a6`
- `b_warm_remote_completion_test.py`:
  `0f8cc0e76e784fb860d3ddb3ad048889533993972ab62dc6ca53bf1fe3d1d8ee`

## Current date policy

The controlled diagnostic requires B pre-load date to equal the coordinator
old planning date. B waits while A prepares the next checkpoint, then loads the
target date. This does not implement both clients independently simulating to
the target date before correction. That playable path needs an explicit
successor date contract; never falsify B before-date to pass this diagnostic.
It is not an additional gate for the current no-command diagnostic.
