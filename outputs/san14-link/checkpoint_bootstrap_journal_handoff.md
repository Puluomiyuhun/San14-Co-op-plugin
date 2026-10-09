# First source-view bootstrap journal

2026-10-09. This successor expresses the first B-side load truthfully: before loading B is still in A's source view; after loading it must be in B's target view. It does not access a game process, Steam, UI or network. No hooks, debugger, native load or user operation were involved. The earlier unresolved game shutdown state is unchanged.

## API and storage boundary

`BootstrapCheckpointJournal(CheckpointJournal)` has the same constructor arguments and inherited staging, reservation, completion and application methods. The constructor explicitly creates the new identity from the start; it never creates an ordinary journal and migrates it.

- Identity schema: `san14.checkpoint-bootstrap-journal.v1`.
- SQLite `user_version`: 2. Ordinary journals remain version 1.
- Additional persisted identity: `pre_load_viewer_force`, derived exactly from `scope.bindings.A.force_id`. The local player remains `B`; B's existing attachment remains the pre-load attachment.
- Only exact integer protocol period 1 is accepted. Scope validation still requires distinct A/B force and main-district bindings. The command cut is not forced to zero; a bootstrap may refer to an already sealed prefix. Period 1 alone is not evidence that the native engine has never loaded before.
- `_guest()` requires the source force before reservation. The inherited `_validate_receipt` and `apply_to_coordinator` still require the target B force after loading. No target observation is fabricated at the pre-load boundary.
- The serialized intent keeps the original structural intent schema, but belongs to the distinct bootstrap journal identity/version. Its persisted guest observation is revalidated against source view on reopening; any completed receipt is also revalidated against target view.
- No reset, migration or recovery permission is added. `INTENT` remains a consumed native attempt after reopening or a callback exception. A late independently verified completion can complete that same intent using inherited rules; it cannot issue another native load.

The ordinary and bootstrap constructors reject each other's databases. Even manually changing only SQLite's version does not make the identity match. Existing ordinary `INTENT` records are not upgraded, renamed or rewritten.

## Six executed checks

1. Actual staging/reservation from source force 12, reopening, strict completion as target force 2, real `Journal.apply_to_coordinator`/`PeriodCoordinator.loaded`, and duplicate receipt delivery without another load. Protocol advances to period 2 and rotates the epoch; Ready remains empty and native gameplay false.
2. Pretending B already sees target force 2 before reservation is rejected; claiming source force 12 after load is rejected. A deliberately corrupted source-view intent also rejects on reopening.
3. A modeled native callback exception leaves `INTENT`; reopening and invoking again cannot call the callback a second time.
4. Ordinary and bootstrap `INTENT` databases mutually reject both reopening and exclusive-create attempts. Original file hashes remain unchanged.
5. Period 2 creation refuses before creating a file; foreign scope and an ordinary reader pointed at a manually changed bootstrap version also refuse.
6. Two actual SQLite connections race to reserve the same checkpoint. Exactly one returns a permit and the other receives `LoadHeld`; the persisted result is one `INTENT`.

SQLite, Receiver, journal methods and protocol `loaded` are real. All world digests, native boundary observations and callback outcomes in these tests are explicit models. A validated JSON/dictionary or database record cannot establish engine input exclusion, reader drain, loaded world correctness or a native permission by itself.

## Reproduction and evidence

```powershell
py -3 outputs/san14-link/checkpoint_bootstrap_journal_test.py
```

Final private result: `../mod_research/checkpoint_bootstrap_journal_runs/20261009-192452-706361/result.json` — 6/6 PASS.

- Result SHA-256: `0eaf8a1f7df351f980ed0d9e5e7f1282efc7476c093a7f2449137e521c5d3eb0`
- Successor source: `d73772ad71e0c593e0d211572afbab1cb54d9cf7535952285edd2777adf3a731`
- Test source: `6137770a0b4c05f4de39cfede5740ee2c2f1a2622917a355afb30eecf9169f8e`
- Four repository sources and eight private artifacts independently rehashed unchanged. Databases and logs remain outside the repository.

Failure `20261009-192441-326662` is retained: the test fixture attempted to change an already recorded sequence-zero prefix, which the existing coordinator correctly refused before the journal tests. The fixture now uses a strictly advancing modeled sequence 1. No production check was weakened.

## Integration still required

The trusted bootstrap projection and received-apply adapters must explicitly accept this new journal type and exact identity, verify the actual source-view native boundary, execute the first load once, then observe target B and complete the matching intent. They must not reinterpret an old ordinary journal or use the diagnostic ACK as completion evidence. Subsequent target-view periods use ordinary journals with their original preconditions. This standalone test does not establish that bootstrap, real game loading and the next period have run together; that belongs to the separate combined integration evidence.
