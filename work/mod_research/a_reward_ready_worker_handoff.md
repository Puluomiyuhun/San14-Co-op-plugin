# Persistent reward worker: observed final Ready fence

## Result

`a_reward_ready_worker_runs/20261008-193737-390733/result.json`: **8/8 PASS**, 51 source fingerprints unchanged.

- Result SHA256: `2ed702ff37a25076ada8ef71cdab0f984cd3a2958f0c3d2724f445785033157c`.
- Fixture SHA256: `abab090919b832b7813a5fc249f8b5ae1e2c7744dc38bf9b8974e676be8e0a1b`.
- Schema: `san14.a-reward-ready-worker-owned.v1`.
- Artifact fields: `fixture_sha256`, `production_sha256`, `planning_dll_sha256`, `reward_dll_sha256`.

Only the new `a_reward_ready_worker_fixture.cpp`, `_test.py` and this handoff are added. Frozen reward/save Owner, bridge, upstream gate and older runners are unchanged. The new harness links the same single physical User/Save Owner and uses its real installed callback; no new User hook is installed. Production predecessor objects are rebuilt without fixture macros as in the preceding test. There is no new production game installer in these worker additions.

No game, Steam, UI, current saves, live scripts or Git operations were used.

## Worker interface

Use the final run directory as working directory, retaining `reward.dll` and `checkpoint_planning_hold.dll` beside the EXE. Start a fresh owned process with an exclusive scratch directory:

```text
fixture.exe worker <scratch> abab090919b832b7813a5fc249f8b5ae1e2c7744dc38bf9b8974e676be8e0a1b
fixture.exe worker-b <other-scratch> abab090919b832b7813a5fc249f8b5ae1e2c7744dc38bf9b8974e676be8e0a1b
```

Both preserve the predecessor's `sample`, `reward`, and `close` JSON-lines messages and continuously retain their own fixture world. The viewer values remain 12 and 2 respectively; these are separate owned replicas, not SAN14 clients. Force IDs, resources and officer data are unchanged from `a_reward_save_owner_handoff.md`.

New messages:

```json
{"op":"ready_fence","value":true,"revision":1}
{"op":"fence_sample","revision":1}
{"op":"ready_fence","value":false,"revision":2}
```

`ready_fence` only requests the existing Owner's final-prefix admission fence. A successful setter response always has `observed=false` and `observed_revision=0`. An identical same-value/same-revision request returns `duplicate=true` without calling the setter again. A lower revision, zero revision or different value at the same revision is rejected. Explicit higher-revision release clears local observation evidence; it is never automatic. A single player's Ready must not call this operation: the room uses it only after both players are ready and all accepted commands have applied.

`fence_sample` requires the current accepted revision. It first checks the exact retained fixture world identity/date/viewer, both Owner reports, no Save lane, no User hold, no queued/active command and no stopped/error/uncertain state. It then dispatches the actual User object's currently published vtable slot via the existing assembly caller. The post-call checks require:

- still the same requested fence and revision;
- zero original User native-start and native-return increments;
- exactly one actual User FINALLY increment;
- exactly one observed suppressed-scope increment;
- no abnormal exit or cleanup-fault increment;
- no queued/active scope, uncertainty, source identity drift or terminal error.

Only this succeeds with `observed=true`. Repeated samples execute a fresh real User callback without changing the revision. This is current local Owner evidence, not an arbitrary caller's assertion and not proof of complete input exclusion. The serialized worker and the Owner's shared control lock retain the same command/save admission protection.

The response includes `requested`, `value`, `revision`, `ready_revision`, `observed`, `observed_revision`, `user_native_started_delta`, `user_native_returned_delta`, `user_finally_delta`, `held_delta`, `active`, `queued`, `uncertain`, `owner_stopped`, `owner_error`, `reward_error`, absolute User counters, `held_scopes` and `thread_id`. The three delta fields are observation evidence only when `ok && observed`; failed or setter replies must never be promoted to that claim. Root compares each actual callback's 0/0/1 deltas, not merely a nonzero cumulative held count.

`all_input_held`, `room_ready`, `full_world` and `native_gameplay_enabled` remain false in every fence reply. The room may describe both replica observations as `OWNER_FENCES_CONFIRMED`; no simulation permit or global engine pause is implied. Existing report-writer/other-thread exclusion limits remain.

## Actual evidence

`worker/stdout.jsonl` and `worker-b/stdout.jsonl` retain real replies. The successful test sequence executes a B reward, requests revision 1, repeats that setter, then samples twice. Each sample reports native deltas 0/0 and FINALLY delta 1. The second sample's absolute FINALLY is one higher while revision remains 1. Commands are denied while fenced; same-revision false and stale revision zero are rejected. Explicit release at revision 2 invalidates the old observation and permits the next real A reward. Both original native reward and pooled-argument cleanup reports still come from the frozen owned replay path.

Six direct cases supplement the two persistent workers:

1. `fence-queued`: a real pending reward blocks the fence without discarding the queued command; the command then executes and later fence observation succeeds.
2. `fence-save`: an admitted Save blocks the fence; the actual original-shaped Save lifecycle completes before the fence is permitted.
3. `fence-active`: a second OS thread tries the setter while inside the actual reward callback and is refused. Subsequent clean observation succeeds.
4. `fence-uncertain`: actual cancellation during execution produces the existing uncertain result; both fence request and observation are refused.
5. `fence-world`: a requested but unobserved fence is followed by actual fixture world-pointer drift; observation fails and cannot produce an observed revision.
6. `fence-original`: a normal User native callback is not a suppressed-scope observation. With the existing upstream hold and no Save lane it terminally stops that scope; later fence admission also remains refused.

This set does not rerun every earlier reward/save negative case or historical upstream gate regression. It adds bounded coverage of the new IPC and actual local observation while preserving the preceding API and code.

## Failure history

First run `20261008-193657-314771` had 7/8 PASS. `fence-original` correctly executed the ordinary User path and the existing upstream gate stopped it; the test incorrectly expected to recover and enter Ready afterward. The test now verifies refusal after that terminal state and exits the isolated case. No production check was relaxed. Final `20261008-193737-390733` passes all eight; the first failure remains preserved.

## Reproduction

From the repository root:

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<private archived research inputs>'
py -3 work/mod_research/a_reward_ready_worker_test.py
```

Dependencies and source/DLL limitations are the same as the frozen reward/save Owner harness. This command runs only freshly built owned fixtures; it does not launch the game.
