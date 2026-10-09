# Received checkpoint → local apply → diagnostic ACK verification

2026-10-09. This is an offline integration test, with actual loopback TLS and an explicit native/rules bridge double. It neither accesses SAN14/Steam/UI nor installs a game hook or debugger. No user operation is required for these tests. The previously unresolved real-game shutdown state is unchanged.

## Scope and exact dependency boundary

`b_warm_received_apply_test.py` independently exercises the new `b_warm_received_apply.ReceivedApply` through existing `WarmRoom`, `FreshSaveBinding`, pinned TLS control/download connections, `CheckpointReceiver`, and a persisted/reopened SQLite `CheckpointJournal`. It reuses only the old room test's setup/offer/receive/cleanup helpers, without rerunning its tests or advancing the room through `complete_model`.

The A save producer/world observation and B `WarmRulesBridge.replace` are explicit doubles. The B double returns the actual `Resident.load` and `WorldLifecycle.replace` outcome structure, including profile SHA, native attempt/PID/birth, loaded date/viewer, completion receipt key, restored slots and the rules generation/checkpoint. Its observation/preparation callbacks are also doubles. This test does not execute the native loading, rules publisher, file staging to CC03, or a real input/execution fence; those separate tests must not be described as one combined game success.

The request uses a local native epoch deliberately distinct from the wire timeline epoch. This adapter does not equate those namespaces. The real rules lifecycle remains responsible for validating the native epoch and real world binding.

## Executed checks

All six final tests passed:

1. Actual TLS receipt and verified local bytes lead through exclusive local load intent, one bridge invocation, completion record and actual TLS diagnostic ACK visible to A. The Journal remains `STAGED`, the room remains `RECONCILING`, and Ready is refused.
2. Foreign file hash, guest force, requested checkpoint, requested date, received room scope, or mixed warm/rules process PID each refuses before any bridge invocation. No completion ACK is sent.
3. A load exception retains the local hold and durable intent without ACK. Recreating both `ReceivedCheckpoint` and `ReceivedApply` cannot repeat native loading against that directory.
4. The ACK is actually delivered over TLS, then the local caller loses the reply. Both same-instance and recreated-instance retry are refused; the bridge runs once and the diagnostic packet is sent once. This simulates reply loss at the local transport adapter, not a physical network outage.
5. A bridge completion whose PID or birth differs from the retained local process binding is refused, with the load intent retained and no completion ACK.
6. Actual coordinator `received`/`begin_guest_load` and SQLite `reserve_load` create a persisted `INTENT`. A mismatched reservation refuses before loading; the exact reservation permits one bridge invocation and actual diagnostic ACK, while the formal Journal remains `INTENT` and no applied receipt or next period is produced. The host world observation and guest safe-boundary observation in this test are explicit models, not actual engine authority.

The optional `sample_loaded` branch is **not dynamically combined in this test**. Its underlying two-table sampler has separate tests, but that does not establish end-to-end sampling through this new adapter. Full-world verification, formal `PeriodCoordinator.loaded`, next-period authorization and Ready remain absent. The test performs one checkpoint per fresh test room, not two production periods in one game.

## Reproduction and final evidence

From repository root, with the existing local Python dependencies available:

```powershell
py -3 work/mod_research/b_warm_received_apply_test.py
```

Private final run: `../mod_research/b_warm_received_apply_runs/20261009-184434-925368/result.json`.

- Result SHA-256: `e9f9b85f72bed06f6cd7043de05323975cfb346d5d8a3ae821ba09313ba10967`
- Tested apply source: `4bd5fcf9bf9e7df398e08911606618ae70e77777f831be2d038c4f4d1e31917d`
- Test source: `d5d1cd188888d57b7f7b4f5debebd3ccbd2326f9be51695752de0f2bc7958db6`
- 23 Python sources and 73 output artifacts independently rehashed unchanged after execution. Private artifacts include local TLS credentials, received fixture files, Journals and intent/completion/ACK records; none are intended for Git.
- The earlier `20261009-184140-929465` four-case PASS is retained before the process-binding hardening and reservation successor. No failing runs occurred. All room handlers and server threads were joined during cleanup. No native child or game process was started.

The next useful step is to invoke this adapter from the retained B owner with the actual rules/warm bridge and fence, then connect its optional current-load sample. A diagnostic ACK is still only a scoped guest report; its file SHA must never be substituted for the broader world hash or used to authorize the next turn.
