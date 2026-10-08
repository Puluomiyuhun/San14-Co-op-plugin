# Automatic Root activation composed with the full owned queue

## Result

`b_reload_activated_queue_runs/20261008-172226-558105/result.json`: **4/4 PASS**, 146 source files and private input hashes unchanged. SHA-256: `fee198f6b6cbcc58385e08644ae95dfe12f16c0e368871e5e42cd36836bc04a5`.

Cases are the three original full two-generation scenarios (`success`, `reuse-full-addresses`, `completion-wait`) and `nested-input-yield`. The executable hash is `5af7935b6d958b836658ddfd446f4491f93f7ff20049c0fa67ac27f0425f5f1e`. The test also compiles the three existing activation C++ units without fixture macros and records their object hashes. No production source was changed.

Every case runs 16 generic Root tasks across two generations on **one actual persistent native worker thread**. There is one initial-wait publication proof, one outer runner invocation/finally, 16 actual IAT start/finish pairs, 48 actual Root entry/return/done captures and 8 generic Load tasks. Each retained task report is checked against the original generation and the same worker thread. Both native queue pops, Load/Title starts and joins, identity/planning observations, retired-generation immutability and 2,000 unowned parent calls retain the previous assertions.

The yield case additionally executes the original `50B690` while the actual User input hardware lease remains armed, followed by original reset and parent resume, once per generation. It has 20 parent scopes, two resume captures and **still only 16 fresh generic tasks**. Its two actual yield events are checked in the completed activation-owned Root reports. No live Root Context handle is exposed or copied to make this work.

## What changed

Only new `b_reload_activated_queue_test.py` and `b_reload_activated_queue_fixture.inc` implement the composition. The build links the frozen activation parent successor instead of the old yield parent, and links the frozen dedicated activation bridge. All frozen nested Root/input/start/completion modules remain unchanged.

The new `runState` constructs the cold pool once, sets up the current owned business callback, and lets the archived `509FE0` scheduler create and start the task. It does **not** initialize or begin a Root observer. Actual `50B598` capture registers the immutable creation; the first real initial wait at `83A9D7` permits publication; the actual `834D88` and `834DC8` IAT return sites begin and finish each observation inside the original long-running `834D10`. The generic thunk then invokes User/Menu/Game/Load business on that worker, including real nested hardware observations. The dispatcher waits for native completion and the activation receipt before reusing callable storage.

The existing Controller already defers pending-adapter binding until its actual User Before callback, so moving business to the native worker required no thread-check relaxation or production initialization change. Actual callback/queue pairing and frozen guards pass on the worker thread. The fixture's scheduling parameters are passed through the actual parent call, rather than writing substitute argument values into an already-captured Root context.

The second synthetic world retains the worker object, thread, runner/entry code pages and IAT wrapper. The new harness prevents its old bulk memory reset and machine preparation from replacing those retained sources. The same IAT pointer is verified before each task. Only explicitly owned callable-copy storage and external synchronization doubles are installed between fixture tasks; original scheduler `done=1` creation semantics remain in use.

## What this does not prove

Construction, pool selection, callable storage and engine business are still owned doubles. A copied runtime image is executed only inside the standalone fixture process. This is **not two legal game reloads**, live world verification, input/presentation coverage, a production installer, or readiness for a remote room.

The activation source still supports a **cold worker stopped at its first native wait**. An already-running unwrapped pool stopped at `834DFD` remains unsupported. No existing pool is stopped or taken over by this test. The complete queue composition now works with this bounded activation source; installing it safely in the real game's lifecycle is the next separate gate.

The test retains legacy helper definitions from the composed fixture generator, including unused independent Root probes. Only the four listed complete queue scenarios run; their `runState` path contains no fixture Root Begin and no synthetic Root Capture. Existing unrelated negative helper probes are not claimed as newly executed coverage.

## Reproduce

From the repository root:

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<immutable private archive directory>'
py -3 work/mod_research/b_reload_activated_queue_test.py
```

The runner validates the existing archived input hashes before compiling. It fingerprints all transitive sources and preserves standard output, generated fixture code, build logs, production objects and a structured result. It does not discover or access the game, Steam, UI or current saves.

## Failed history

`b_reload_activated_queue_runs/20261008-172119-096906/build.log`: production objects compiled; `/WX` rejected the old `nestedPrepare` helper left unused after replacing `runState`. The new generator removes that obsolete fixture helper block. No production condition was weakened. The next complete run is the 4/4 result above; there were no failed runtime cases in that run.

## Next bounded step

Compose this source with the remaining independently tested failure paths and an explicitly bounded cold-pool lifecycle installer. Preserve the existing initial-wait proof, original IAT identity, immutable generation ownership, persistent module lifetime, native FINALLY and nested debug-register lease checks. Do not infer a running-pool permit from the successful owned cold-pool test.
