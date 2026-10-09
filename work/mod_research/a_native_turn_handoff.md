# A native turn controlled successor

This closes the offline control-path gap between one delivered Save and a second Save after native planning states leave and return. It does **not** prove a real game turn, B-loaded synchronization, full writer exclusion, or two-computer play. No game/Steam/UI/current-save/process access occurred in this task.

## Native composition

`a_native_turn_runtime.h/.cpp`, `a_native_turn_parent.cpp`, `a_native_turn_owner.cpp`, `a_native_turn_gate.cpp`, and `a_native_turn_control.h/.cpp` explicitly succeed frozen repeat Runtime/Parent and abort-pending Owner/covered Gate. Do not link both implementations. `a_native_turn_exports.cpp` includes the new Runtime header, preserving wire 1–10 layout; it must replace the repeat exports TU so class layout is consistent. `a_native_turn_runtime_build.py` builds the actual retained DLL with these replacements and the existing actual Owner/Controller/Driver/IPC dependencies.

After actual first artifact delivery, original-parent BEFORE/AFTER still perform real observation and `planning_period_owner::Retire`. At that authenticated boundary, immutable local module wiring enables Running only after Owner/Gate business scopes and physical bridges are quiet. ReadyFence/period retirement stay recorded, but original User/Game callbacks become transparent. Parent continues original scheduler dispatch while skipping the old five-state Host planning checks. The producer lease is released on its owning host thread before this Running interval. No production code writes the date or invokes autosave/time advancement directly.

During Running, the Runtime reads root/world/cache/force/ruler and bounded date progression, without dereferencing retired User/Strategy. At exact next date it waits for five correct state names/vtables, no task pointers, no queue/current, User planning phase, actual fresh pending Inspector and quiet report Guard. A staged retained second sampler supplies actual new addresses. Owner refreshes its report Guard and user identity at the same authenticated parent/TID and retired serial; Gate then refreshes its five-state identity. Real Rebind, second Controller Initialize and Host BindPeriod must all succeed before Running ends or the second Save becomes admissible. History, bridge counters, Driver claims and old allocations remain retained.

The second sampler is selected before refresh validation. Any later failure is terminal: stop, keep Running/drainPending, no fallback to old objects and no retry of a consumed new Guard. Stop during Running never converts this state into normal planning or restore-ready. Original callbacks keep forwarding without reviving old Save admission. This is deliberately unresolved until separate trustworthy turn-drain evidence exists.

Running exposes original native menus, not a command whitelist. A future controlled real test must only advance normally and handle ordinary reports; do not add new orders. Original advancement may naturally execute its own autosave. Unknown choices require the human; there is no automatic event selection. The existing typed `simulationEnabled=false`, `bLoadedProven=false` and `allWritersProven=false` remain truthful. Two generations only; not an unbounded room runtime.

## Executed evidence

- Actual combined Runtime/Parent/Controller/Owner/Gate/Driver/IPC test: `a_native_turn_runs/20261009-155031-692039/result.json`, SHA-256 `b2d0eaba0af2adb1a09bff92cd7e2960dc7320c28aa4ff2bf3017f25deea5885`: **2/2 PASS**. 98 source identities, 46 products, 6 generated files and 3 private inputs pinned. Source identities independently rechecked after execution.
- Normal case performs two real mailbox/pipe Submit/Copy transactions through the production control classes. Native business/serializer are explicit owned substitutes. Between Saves, phase-5 User and Game UI/panel originals pass through actual bridges; Strategy/User leave the stack. Next date with incomplete stack does not rebind. New User/Strategy addresses are then installed and old object memory cleared; pending report still blocks rebinding, and clearing it allows fresh binding and the second complete Save. Both artifact packets are decoded and verified by the existing packet implementation. Counters: observations/submits/copies/releases all 2.
- Stop-running case stops from another owned thread while Strategy/User are absent. The actual Parent AFTER/FINALLY remains paired; producer is free, Running/drainPending remain set, no second request/artifact occurs. This proves conservative refusal of restoration, not native simulation drain.
- Production DLL and existing 1–8 ABI: `a_native_turn_runtime_runs/20261009-155107-507427/result.json`, SHA-256 `80a8b8c27fade1ebeeeb6d23f3bf9150dfd066c8614b40ce4b6ddcdefd31d2a7`: **PASS**, 91 production source identities and 33 products. DLL: `abi/production/build/a_save_local_runtime.dll`, SHA-256 `473e542dc9512c994077c8187b27357388a41ca80a83685ecb13d593cbeff8b7`. New exports correctly include the new Runtime definition. Root separately validates additive 9/10 schema/ABI.
- Independent sibling review found no blocking issue in the narrow Running/Stop/fresh-Guard path. It specifically confirmed the deliberate terminal behavior after a partially staged sampler/Guard refresh.

Failures retained: `154507-491437` failed compile because new Control header included both old and planning Gate declarations; corrected to forward declarations. `154818-165119` normal two-Save case passed, but stop-running hit the inherited healthy-Parent-only fixture assertion; the final fixture explicitly accepts the actual Stopped parent state with BEFORE/AFTER/FINALLY paired. No production check was weakened for that correction.

## Next work / actual evidence still needed

Use the new production builder and the existing additive ABI test for offline reproduction:

```powershell
py -3 work/mod_research/a_native_turn_test.py
py -3 work/mod_research/a_native_turn_runtime_build.py
py -3 work/mod_research/a_save_repeat_exports_test.py --dll <new-build>/abi/production/build/a_save_local_runtime.dll
```

Do not launch historical live scripts automatically. Parent owns the next controlled installer/launcher selection, fresh local profile capture, source/publication checks, full save backup and actual game test authorization. Attach `a_turn_identity_capture.py` to that already-needed test to capture real returned state addresses rather than asking for a separate repeated game operation.

Previously saved live traces establish that User/Strategy leave the stack and reports appear before stable planning (`lockstep-traces/rng-pairs-live-n/trace.jsonl`, SHA `694418cbb579ebd7792d3c0100bf0d2a5f2c97509e4eb58ce45cec36d7827cd8`), but those records contain names, not object addresses. This task supports fresh addresses in production code and tests an explicit address change; it does not infer that the real game always reallocates them.

The remaining critical validation is one actual native turn through this new Running path, including native event/report behavior and the returned fresh planning state, followed by the second verified Save. B-loaded proof and coordinated player input remain separate missing room integration. This task neither inspected nor altered any previously active game patches/debugger; main-thread handoff governs current process cleanup.
