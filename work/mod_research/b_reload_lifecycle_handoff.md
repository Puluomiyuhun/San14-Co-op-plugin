# B startup lifecycle successor — 2026-10-08

## Scope and status

This successor closes an owned-process source path from the native four-worker pool initializer to two observed tasks on one warmed worker. It does not attach to an existing game or turn a worker already waiting at 834DFD into an owned observer. Separately, an explicit new-process loader now loads and invokes an owned DLL before a fresh executable's PE entry. These are two distinct proofs: the loader fixture does not call the SAN14 lifecycle Initialize/Arm API.

No game, Steam, UI, current save, existing PID, or live SAN14 process was accessed by this work. No frozen predecessor was edited. Room readiness, complete runtime bootstrap, and live installation remain false.

## Native source and selected lifecycle

The runtime archive shows the generic pool getter at 145B20, pool storage at 1A24DA0, and first storage construction at 145B71 -> 5090E0. Construction alone does not create the four native threads. Normal startup calls 145B20 at 1447AE, moves its result into RCX at 1447B3, then calls the actual initializer 509580 at 1447B6 (return 1447BB). The original 509580..509639 loop calls 833CB0 at 509600 for four workers with stride 0x80.

The new lifecycle source prepares an exact 1447B6 call replacement through a dedicated PE bridge with unwind/FINALLY. It requires the original initializer and call bytes, supported page provenance, the actual pool argument and return address, and an empty pool. After the original initializer returns, the real bridge owner authorizes registration of all four distinct worker objects. Each publication retains the existing exact initial wait 83A9D7 proof, native object/control/function identity, original 834D10, empty debug-register ownership, and the outer activation wrapper. It does not rewrite a suspended return stack or bypass CET.

Workers are wrapped before the first native wake. Normal tasks that have no accepted parent ticket pass through the wrapper unchanged and do not invent Provider records. Later accepted 50B598 creation establishes task identity on an already wrapped, warmed worker; the actual IAT capture starts Root observation. Resume handling remains the frozen parent successor's strict same-object path.

An unwrapped worker already inside 834D10 and waiting at 834DFD will not reread object+38. Consequently slot replacement cannot insert the required outer unwind owner there. This successor refuses an existing initialized pool rather than treating that state as equivalent to the initial wait.

## API and publication boundary

`b_reload_lifecycle.h/.cpp` exposes Initialize(Config), PreparedPlan(Plan), Arm(), Stop(), Snapshot(). Config remains the activation Config. The plan is a five-byte replacement for 1447B6 plus a retained near RX relay. Initialize prepares and validates; it does not write the callsite. Arm requires that an external stopped-startup publisher has already installed exactly the prepared plan and that the pool is still empty, then publishes the strictly validated original LeaveCriticalSection IAT route. The owned test applies the plan to its own allocation. A production stopped-startup publisher and failure rollback policy are not supplied by this module.

`b_reload_lifecycle_activation.cpp` is a same-ABI successor to frozen Root activation and must be linked instead of it. It registers the pool only under the dedicated real lifecycle PE owner and permits transparent unticketed tasks. `b_reload_lifecycle_bridge.h/.cpp/.asm` is its separate bridge bank. Profile headers are generated from the private archive by the test harness and are not generic signatures.

## Lifecycle execution evidence

Run: `b_reload_lifecycle_runs/20261008-180044-348116/result.json`

SHA256: `6dcdc4c86c1edd6323a26f78e90f866f50a0475bbfdcf1ab6803741a899a7d1c`

2/2 PASS, 153 source fingerprints unchanged; lifecycle, activation successor, and bridge production objects compile without fixture macros under /W4 /WX.

- `lifecycle-two-tasks`: original initializer executes; four actual native worker threads reach their native first wait; all four register. One real unticketed warm-up runs with Provider snapshot unchanged, then the same worker executes two parent-authorized tasks with six actual Root captures. All four outer FINALLY paths execute during normal worker shutdown.
- `lifecycle-existing-pool-refused`: an already initialized pool runs one unwrapped warm-up and is refused before activation/source publication.

The owned 833CB0 constructor substitute actively waits for each worker to reach its initial native wait before returning, so all four are ready when the original initializer returns in this fixture. This does not prove that the real constructor has the same timing. Production currently performs a single strict initial-wait check: if a real worker has not reached that wait yet, registration refuses; it does not wait/retry or adopt an arbitrary running state. The 2/2 result therefore does not establish successful real startup timing. Transparent ordinary business coverage is exactly one unticketed warm-up; general ordinary-task and exception coverage has not been established.

The owned constructor, callable storage/copy, task bodies, image allocation, and startup caller prefix remain explicit fixture substitutes. The archived loop/runner/thunk, OS waits and threads, accepted parent source, Root observation, and unwind bridge are actually executed. This lifecycle successor has not yet been combined with the entire two-generation queue, nested Load/Title sequence, or the earlier fault matrix.

## Explicit new-process loader

`b_reload_lifecycle_loader.exe <explicit-exe> <runtime-dll> [--wait-exit]` creates only the named new child. There is no attach-by-PID or process discovery. It verifies a fixed exported `BReloadLifecycleBootstrap`, starts the child under its own debugger, sets a one-byte PE-entry breakpoint, then restores the original byte and RIP. It holds the primary thread explicitly while detaching its debugger, loads the DLL using the matching remote system module/export RVA, and invokes the named export on another remote thread. No remote executable stub is allocated. On success it rechecks the held primary entry and restored byte before resuming. A rejected bootstrap terminates only this created child. `--wait-exit` is used by the owned test.

The DLL's bootstrap receives versioned metadata, not a permit. The owned DLL independently verifies the current PID, main image, primary thread process identity, actual held primary CONTEXT at the PE entry, and restored entry byte before setting an executable-owned marker. The real runtime DLL would still need its own independent identity/source and stopped-lifecycle checks.

Final loader run: `b_reload_lifecycle_loader_runs/20261008-181520-748028/result.json`

SHA256: `948929928902c807aa19b3b240122ebf97b7772c36a22bbc8b9d85214e80ed31`

2/2 PASS: the successful bootstrap occurs before the owned host's entry, and explicit bootstrap refusal returns failure without running its main. Four source fingerprints unchanged. The non-diagnostic production loader object also compiles. The same binary passed ten additional fresh owned-child runs; full outputs and its hash are in `repeat-check.json` beside the result.

## Missing real bootstrap connection

The archived runtime and on-disk executable have previously differed at 79 inspected ranges. It is not established that 509580/1447B6 or all activation profiles already contain the supported runtime bytes before the real game's PE entry. DLL-before-entry success therefore does not establish a usable Initialize/Arm phase in SAN14.

Remaining work is concrete:

1. Establish when the supported runtime profile becomes available and when the native pool is still cold, without assuming PE-entry availability or bypassing the profile checks.
2. Build the actual runtime Bootstrap export that owns Provider/parent/session lifetimes and binds the known image and supported profiles. The current DLL is only an owned marker fixture.
3. Connect a stopped-startup publisher to Initialize -> PreparedPlan -> exact source publication -> Arm, with explicit restoration/retention behavior on every partial failure. The loader does not perform this publication.
4. Compose this lifecycle successor with the already separately verified complete queue and failure handling, then conduct an authorized real startup test. Steam-launch behavior, command-line forwarding, protected/packed startup, user-facing launcher flow, and live room connection are unverified.

## Retained failure history

- Lifecycle `20261008-180006-489738`: first compile failed on the added namespace's Error enum collision; no execution result claimed. Names were qualified in the successor.
- Loader `20261008-180700-816593`: Python failed while encoding the build log; retained artifacts, no execution claim. Logging changed to UTF-8.
- Loader `20261008-180714-781543` and `180824-008326`: entry wait timed out because CREATE_SUSPENDED had not been released before waiting for CREATE_PROCESS. The fix releases that one initial suspend; Windows debugging holds the child at its events before the PE entry.
- Loader `180910-597595`: initial 2/2 pass before later diagnostic/production-object changes.
- Loader `181027-079296`, `181116-253291`, `181145-318935`: premature CloseHandle on debug-event thread/process handles caused DebugActiveProcessStop to refuse with ERROR_ACCESS_DENIED, including intermittent outcomes. The final source retains those handles for the debug session instead of prematurely closing them. The entry restoration and primary suspend checks remained mandatory throughout. All failed outputs remain in their run directories.

## Reproduction from repository root

```powershell
py -3 work/mod_research/b_reload_lifecycle_test.py
py -3 work/mod_research/b_reload_lifecycle_loader_test.py
```

Both commands execute owned fixture processes only. The lifecycle test requires the same private runtime archive/profile inputs as its predecessors. Neither command launches the installed game.
