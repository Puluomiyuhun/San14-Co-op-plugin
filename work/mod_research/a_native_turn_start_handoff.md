# A controlled native-turn startup successor

2026-10-09. New files: `a_native_turn_start.py`, `a_native_turn_start_control.py`, `a_native_turn_start_test.py`. Frozen diagnostic/single-save launcher, native Runtime, typed ABI and publisher sources are unchanged. No game process, Steam save, UI or debugger was accessed in this task. The only production DLL calls were in the owned Python test process, without Prepare/install.

## Closed connection gap

The previous `a_save_diagnostic_start.py` only submitted one Save, immediately stopped its pipe, and used a post-check fixed to 203-08-11. Merely replacing its DLL could neither request the second period nor survive manual advancement. The new explicit successor:

1. Checks the actual **native-turn** build family and all source pins, the full production DLL identity, legacy ABI schema, and a successful actual 9/10 ABI test of that exact DLL. It requires the strict `a_save_repeat_publish.cpp` publisher, plus matching launcher interface-test source identities. Old repeat Runtime builds are rejected.
2. Preserves the original current-machine read-only capture, complete save backup and byte verification, process-birth/base binding, one retained per-process claim, dependency loading, typed Prepare/Plans/ArmOwner, three-call publication and natural original-parent initialization. Publication occurs separately from remote calls; it never calls into a stopped-debugger target.
3. Opens the existing actual A named-pipe client. It performs generation-1 Submit/Copy and checks both exported packet and actual saved-file SHA before requesting the next period. The copied typed RequestNext binds the true first artifact hash, the next exact date and a distinct local period digest; native room epoch stays fixed. No B-loaded or room-authority receipt is fabricated.
4. Polls typed RepeatSnapshot. Only the new DLL's retired/no-lease/drainPending evidence is interpreted as Running; it prompts the human to advance normally without issuing new commands. Real pipe Snapshot requests keep the existing authenticated connection alive, avoiding the old 30-second idle disconnect. No date field or native advance/autosave function is called. Reports and event choices remain the human's responsibility.
5. Once actual native ReadySecond evidence matches the exact consumed next request, submits generation 2 through the same actual client/channel. Both artifacts are saved privately and compared with their actual native disk files. The new post-check expects the next date, same PID/birth/base and ruler/force, returned five-state planning/phase2 and no attached debugger.
6. Stops the native Runtime/service and checks repeat lease/frame/drainPending before invoking the strict restoration publisher. A stopped/timed-out Running interval retains sources instead of pretending that zero current activity means it is safe to remove them. Unknown remote calls and uncertain publication never retry or unload. Source restoration still requires the actual publisher's own held-process checks.

The standalone local test uses two fixed generations only. It is not yet the room coordinator, full command synchronization, B loading, AI-rule reinstall, or an unattended event handler. `allWritersProven`, B-loaded and two-game readiness remain false in the native/typed layers. Controlled Running exposes native menus, so the human must only advance and close ordinary reports, not add orders.

## Invocation and remaining live boundary

No arguments means help, with no process access. Explicit read-only preparation:

```powershell
py -3 work/mod_research/a_native_turn_start.py --capture --pid <current-PID>
```

The new execute command additionally requires all four recorded build/test folders:

```powershell
py -3 work/mod_research/a_native_turn_start.py --execute --pid <fresh-current-PID> --build-run <outer-a_native_turn_runtime_runs-folder> --publisher-build <strict-repeat-publisher-folder> --repeat-abi-run <exact-DLL-9-10-ABI-folder> --launcher-test-run <matching-a_native_turn_start_test_runs-folder> --wait-seconds 600
```

This is a newly connected experimental entry, **not a previously verified game run**. Parent owns selecting a fresh supported game process, verifying prior retained-module cleanup, and coordinating the one actual native turn. Never reuse the old uncertain process/claim or substitute a publisher family. The existing initial capture still targets the original machine's slot34 Zhang Lu baseline and storage paths; this successor does not make those paths portable to the friend's PC.

The wait is bounded to 1–1800 seconds (default 600), maintained by pipe Snapshot polling. On timeout or unexpected event, the Runtime may be permanently stopped in unresolved Running and hooks must remain until normal game exit or separate trustworthy drain evidence. No automatic continuation after a terminal failure is provided.

Original advancement may perform its own autosave and change old files. Every original save is backed up before installation; final inventory explicitly reports all changes/additions. The launcher does **not** silently permit or restore changed old files. Even if two Saves completed, changed originals or extra native files result in `INCOMPLETE_RETAIN_EVIDENCE`, with both artifact results preserved for review. Only two verified Saves, clean native restoration, unchanged originals and exactly the two expected new files yield `PASS_REAL_CONTROLLED_TWO_SAVES`.

## Offline verification and precise limitations

Final candidate: `a_native_turn_start_test_runs/20261009-172106-322176/result.json`, **5/5 PASS**, SHA-256 `d761cb95f1c2015eb1368fafe5f642c0a22a31a9cf9e3c7d3c5f593020263d13`. Eleven sources and five private inputs pinned; unittest output/failure details retained. Earlier passing revisions `171912-880997` and `172038-462873` remain intact; no failed run was discarded.

- Real archived native-turn production build and additive schema/source validation; old repeat build rejected.
- Actual production DLL loaded into the owned test process; both typed 9 and 10 reject unprepared calls. DLL and required dependency hashes are checked before this test load. This is ABI execution, not a new native Save.
- Actual `ASaveClient` serialization/response parsing and actual packet decoder consume the two archived diagnostic artifacts from the real native-turn component fixture. Interface transport and typed Runtime state responses are **explicit substitutes**, not a fresh pipe server or real simulation. The test verifies one RequestNext, original-artifact hash binding, heartbeat placement and generation-2 request only after ReadySecond.
- Stopped Running response prevents generation-2 Submit and cleanup restoration; no replay.
- Native autosave-style old-file changes are surfaced rather than hidden.

The full new launcher has not been run against the game or an owned copy of the entire runtime fixture. Its DLL loading, real remote-call publication sequence and native time progression remain to be validated together in the controlled live test. Reusing the already-tested primitives is not evidence that this last end-to-end run has happened.

Current source hashes: startup `8fa69e03d067809fe1fb435ef3e2e05b4ebd0f1ab56f446aade17d6a3b06dd99`; control `ec2097cbcc1ddce2fc0c7a09e2ec70e9b5a80b0a4cbc14a439b1de5807596363`; test `2566ef93f3cf6034050f32c91056400fcd1a670dd74ddba36a3743646fa6d062`. Public integration/Git are the root agent's responsibility.

Known inherited cleanup limitation: if `ProcessAPI` construction fails after opening its process handle (for example, debugger rejection), that handle can remain open until the controlling Python process exits. This successor retains the frozen constructor; the leak is not evidence of an installed hook or a completed native operation.
