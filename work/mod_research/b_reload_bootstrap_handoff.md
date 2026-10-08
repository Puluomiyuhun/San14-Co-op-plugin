# B startup Bootstrap stage — owned-process only

## Change and callable boundary

New `b_reload_bootstrap.h/.cpp` adds `InitializeAndArm(const BReloadLifecycleBootstrapInfo&, Provider&)` and retained `Snapshot`. New `b_reload_bootstrap_export.cpp` exports the exact old loader name `BReloadLifecycleBootstrap` and owns a static Provider retained for process lifetime. The old loader, lifecycle, activation, nested observers and bridges remain byte-for-byte frozen.

The export now invokes actual production `b_reload_lifecycle::Initialize`, `PreparedPlan`, publication of the 5-byte initialization callsite, and `Arm`, including the real root activation IAT compare/exchange. It is no longer a marker-only export. No fixture macro is used to compile the lifecycle, activation, bridge, Bootstrap core, Provider or nested observer objects; even the positive exercise keeps MEM_IMAGE and actual `LeaveCriticalSection` export identity checks.

The bounded stage checks:

- Metadata size/version/reserved, PID, current primary PE base/header/machine/image bounds and exact entry/original byte.
- Opens only this process's named primary thread, adds one suspension and requires the previous count exactly one; reads its real OS CONTEXT and requires RIP at the PE entry. Its added suspension is removed in FINALLY and the loader's original hold remains.
- Requires thread enumeration to finish with `ERROR_NO_MORE_FILES`, with precisely the primary and current export threads. Rechecks that set before publishing.
- Requires six exact bounded source ranges (initializer call/body, runner, thunk, yield, thread entry), MEM_IMAGE pages belonging to the primary PE, and the actual locally loaded system `LeaveCriticalSection` IAT address in a read-only image page. Requires four empty worker-object slots on writable image pages.
- Pins this DLL, initializes once, checks the prepared plan and unchanged sources, writes its exact 5-byte call under the trusted startup condition, restores RX protection and flushes the instruction cache, then calls actual Arm. Rechecks primary entry before returning success.

The stage returns false on failure. The frozen loader treats this as bootstrap refusal, terminates only its newly created owned child, and does not resume the main entry. It does not roll back or unload a published module. A failure after a call/IAT publication is reported uncertain. Subsequent InitializeAndArm calls return false without resetting receipts or beginning a second attempt. Snapshot is diagnostic, not a new startup authorization.

`BReloadBootstrapReadReport` allows the owned host to inspect the actual retained report after the loader resumes entry. This is local diagnostics, not an authenticated remote IPC or room handshake. The static Provider in the DLL is not yet wired to a complete room/queue host; an integrated local runtime can use the C++ interface with its retained Provider. This task does not claim that later parent registration/task dispatch is installed by Bootstrap.

## Explicit proof boundaries

Thread snapshots are NOT continuous all-thread exclusion. Trusted loader/bootstrap callers must maintain the startup no-other-thread/no-new-thread condition across inspection and publication; there is no global prevention of concurrent creation or external publishers. DLL initialization must not call this interface under DllMain/loader lock. The original primary remains suspended while the separate export thread runs.

Only six source ranges and local image/layout properties are checked here. They are not an entire game EXE/version proof, complete runtime profile, background writer drain, input fence, room readiness, loaded-world proof, or simulation permit. The production host must separately establish executable/version identity and source preparation stage. Ready/fullWorld/gameLaunchVerified/workersStarted remain false.

Historical disk/runtime comparisons found 79 differing source ranges. Whether real SAN14 already has the archived `509580`/`1447B6` and other required runtime bytes before its PE entry remains UNPROVED. The production DLL is deliberately tested on an unprepared owned executable and refuses it before any source publication. This implementation does not unpack or reconstruct the real game, poll indefinitely for changed bytes, or take over an existing pool. It supplies an executable refusal path, not a claimed game-ready installer.

The positive fixture creates its own PE with a large reserved image section. **Only** the export compiled with `B_RELOAD_BOOTSTRAP_OWNED_PREPARE` explicitly copies private archive profile ranges into that owned PE, sets the dedicated artificial system IAT, and sets its zero pool pages writable. Production export contains none of this preparation. No installed executable, running game, Steam, actual save or existing UI is opened. Self-built child startup/debugging is the entire OS test scope.

The successful stage has initialized and armed sources but `lifecycle.entered==0`, `activation.threads==0`: it has not executed the four-worker constructor, waited for cold workers, run a task, or completed queue/Load/Title. Earlier lifecycle and queue results remain separate. Real constructor initial-wait timing remains unresolved.

## Tests and retained failures

- `20261008-222740-719381`: initial link failed because the inherited fixture-only observer alias remap was carried into production DLL linking. Removed that fixture alias from this new build; no frozen source edit.
- `20261008-222838-991544`: four rejection cases passed, positive failed before Initialize/patching at the pool page check. Diagnostics showed actual owned MEM_IMAGE zero pool pages had `PAGE_WRITECOPY (8)`, not PAGE_READWRITE; fixture preparation now explicitly makes its own pages RW. Production check was not weakened.
- `20261008-223002-023103`: all 5 initial cases passed, including updated complete enumeration terminal-status check.
- Final `b_reload_bootstrap_runs/20261008-223110-879958/result.json`: **7/7 PASS**, source/private inputs unchanged.

Cases:

1. `prepared-owned-image`: original loader stops actual PE entry, actual LoadLibrary/export invokes production Initialize/PreparedPlan/publish/Arm, primary main reads initialized/armed/IAT-published report, and exits 0.
2. `production-source-unready`: production DLL without fixture preparation refuses exact source check; no lifecycle init/call write/IAT publish/Arm; main never starts.
3. `mutated-runtime-body`: artificial archived initializer byte mismatch refuses before Initialize/publication; main never starts.
4. `wrong-system-iat`: executable but wrong system export (`GetTickCount64`) refuses; main never starts.
5. `existing-pool`: one artificial nonzero worker slot refuses before Initialize/publication; main never starts.
6. `extra-thread`: actual third owned thread waiting on an event makes complete inventory reject; no source publication/main. The fixture drains that thread after the rejection.
7. `duplicate-bootstrap`: after successful actual initialization, another direct call to the stage refuses; attempts stays one and the existing source remains armed. Main reads the original real receipt; no second Initialize/publication.

Result SHA-256: `cbe6ff364c16e9e79305522b2478247eca2e1f86f3ef70aea03b9e183c1491ce`.
Pinned source count: 143; all rechecked after final run. Exact private profile/archive identities and every source hash are recorded in result.json.
Production Bootstrap object SHA-256: `a4a98f03ec6ad1d34bdf13e7cf134d526ee3c34c0087f351a507fee4b3890c81`.
Production runtime DLL SHA-256: `6535e7b8b5235856941d8a3b65b102f138a90ca27fcb874ae43c192d28392acb`.
Owned fixture DLL SHA-256: `f1dc6a1e3fd5d442aa514dc3d4932c2b9775592264548bf44bc4e9a7bb6d361c`.
Owned host SHA-256: `bb3840bd51c5cd9110507a58a24ed6dd65ebf0f75cb11d30b15522363317e0ec`.

Run from repo, using already available private archive inputs:

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<local existing private archive directory>'
py -3 work/mod_research/b_reload_bootstrap_test.py
```

No user game operation is needed for this test. No debugger/patch is left in any existing process; each self-built child exits or is terminated by its own loader on refusal. Do not run loader/production DLL against a game based on this evidence. Next required work is establishing a supported real source-ready startup phase, then composing this export with the actual cold initializer/queue lifecycle and the local host Provider registration under an authenticated/version-pinned startup contract.
