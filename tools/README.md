# Offline developer check

Newest same-runtime queue composition: [Bootstrap and two generations](../work/mod_research/b_reload_bootstrap_queue_runtime_handoff.md). Normal and input-yield owned cases pass; read the macro/service doubles before reproducing. This is not a game installer.

[A native User lifecycle](../work/mod_research/a_save_dispatch_handoff.md) and [cold-start parent audit](../work/mod_research/b_reload_cold_start_handoff.md) run only pinned archive instructions, with explicit modeled services. No real saves or OS startup timing are proved.

Latest actual startup composition: [same PE / DLL / Provider and four workers](../work/mod_research/b_reload_bootstrap_workers_handoff.md), 2/2 owned-process cases. Production game readiness and two-generation ticketed queue are still absent.

One user-authorized normal Save observation has finished with verified cleanup; see [live interpretation](../work/mod_research/a_save_first_live_handoff.md). Do not automatically repeat historical live commands.

Latest same-process two-period composition:
[a_save_simulation_ipc_handoff.md](../work/mod_research/a_save_simulation_ipc_handoff.md).
It binds actual Room scopes to the native date-boundary and Session successors,
then executes two diagnostic saves through the authenticated pipe and real TLS.
Battle/date business and B loaded remain fixture/model; no real game access.

Previous held-save pipe/phase work: [a_save_held_ipc_handoff.md](../work/mod_research/a_save_held_ipc_handoff.md),
with [native held admission](../work/mod_research/planning_checkpoint_save_handoff.md)
and [actual Bootstrap](../work/mod_research/b_reload_bootstrap_handoff.md).
These use only owned processes and archived inputs. They do not establish actual
post-simulation native date transition, legitimate game saves, or two-game readiness.

For the latest retained Period Owner + actual save pipe/TLS/journal composition,
see [a_save_period_ipc_handoff.md](../work/mod_research/a_save_period_ipc_handoff.md).
Its explicit build and flow commands use only an owned process, diagnostic files
and loopback TLS. They require existing private archive inputs; they do not
discover the game or produce a valid SAN14 save or a production save permit.

For the new single-manual-save observer, see
[a_save_observation_status_handoff.md](../work/mod_research/a_save_observation_status_handoff.md).
`py -3 work/mod_research/a_save_observation_status_test.py` builds and tests only owned
Windows processes, without private native dumps or game discovery. The launcher
without arguments shows help. Its explicit `--preflight` and `--record` options
access the game and are separate future manual-test steps; they are not part of
any offline developer check or multiplayer authorization. This successor shares
the menu observer's DR6 event-ownership guard; the old observer remains frozen
for historical evidence and is no longer the recommended recording entry point.

For the portable two-computer **connection diagnostic**, see
[CONNECTION_CHECK.md](../docs/CONNECTION_CHECK.md). Build it from public sources
with `prepare_connection_check.py`; `test_connection_bundle.py` runs two actual
relocated loopback TLS processes. This diagnostic never starts or attaches to
the game and does not replace the native save/load prerequisites.

From the repository root, with Python 3.10 or newer:

```powershell
py -3 ".\tools\dev_check.py"
```

From another directory, use an absolute quoted path:

```powershell
py -3 "D:\Projects with spaces\san14-coop\tools\dev_check.py"
```

The tool creates `.local/dev-check/<timestamp>/` beneath this checkout. Its summary separates protocol test results from development-environment availability. Missing native research dependencies do not prevent the standard-library protocol tests from running.

What actually runs:

- The original `test_protocol.py` and `test_timeline_protocol.py`, selected explicitly with `unittest`. They open temporary **127.0.0.1 TCP** listeners. The report obtains the case count from the actual test runner rather than a hard-coded total.
- When `cryptography` is importable, the original `run_room_selftest.py`: pinned-certificate **loopback TLS**, two room clients, faction selection, authority rejection, retries and reconnect. A synthetic catalog replaces the historical game-derived catalog. Its reported named checks are listed separately from unittest cases.
- Import/availability checks for `capstone`, `pefile`, and `cryptography`; file-path detection of Windows x64 MSVC tools. No compiler or Visual Studio initialization script is executed.

There are **no internet requests, package installations, game-process handles, game calls, native hook installation or native integration tests**. The check does not scan/import arbitrary research scripts. `test_draft_transport.py` is excluded because it imports a live-related module and needs a captured draft JSON. Native harnesses needing dumps, saves or historical run directories are also excluded.

Use `--skip-tls` to omit TLS explicitly. Missing `cryptography` skips TLS with a reason; it does not manufacture a pass. On Linux/macOS, protocol tests can still run, but the native environment reports `NOT_WINDOWS`.

## Existing private dependencies

If an existing local dependency directory is available:

```powershell
py -3 ".\tools\dev_check.py" --deps-dir "D:\Private SAN14 research\python_deps" --strict-env
```

`--deps-dir` only adds an existing directory to this process and its test children. Nothing is installed, copied into the repository, or changed globally. `dependency-baseline.json` records versions observed in the original private `dist-info`: capstone 5.0.9, pefile 2024.8.26, and unicorn 2.1.4. Unicorn is recorded for historical research but is not needed or tested by this check. No cryptography version was recorded in that directory, so no version is invented for it. Installed versions and discrepancies appear in `environment.json`.

An unusual Visual Studio location can be supplied explicitly:

```powershell
py -3 ".\tools\dev_check.py" --vcvars64 "D:\VS\VC\Auxiliary\Build\vcvars64.bat"
```

Finding tools does not prove the Windows SDK, all C++ libraries, ABI profiles, or historical native build scripts work. `--strict-env` is an availability check, not native certification.

## Explicit checkpoint component checks (Windows)

To rebuild the current checkpoint components and exercise their local byte-transfer composition:

```powershell
py -3 tools/check_checkpoint_components.py --fixture-root "D:\SAN14 private research\mod_research"
```

This entry uses an explicit allowlist: `checkpoint_fresh_save_packet_test.py`,
`a_save_user_owner_test.py`, `b_reload_title_source_test.py`, then
`checkpoint_fresh_save_binding_test.py --owner-run <the successful run just produced>`.
It does not enumerate or attach to the game, load a DLL into SAN14, call a live
launcher, change Steam files, or require a user to operate the game.

Unlike `dev_check.py`, this **compiles and runs owned native test processes**.
It currently requires VS2022 Community's default x64 toolchain path and the
private runtime/profile/archive inputs referenced by the selected tests. Those
inputs are read only. Missing inputs fail with an explicit reason; the tool
does not manufacture them or accept arbitrary replacement hashes. First-time
setup on another PC still needs its local evidence, as explained in
`docs/LOCAL_SETUP.md`.

The A fixture runs its real retained Owner, bridge, storage checks and
`CopyArtifact` byte encoder. Game save business functions remain test doubles.
The B fixture runs actual Title vtable publication and two-generation native
component paths; its parent/start services remain doubles. The final step
transfers the A fixture's two distinct diagnostic files over loopback TLS,
reopens staged SQLite journals, preserves control channels and rejects stale
downloads. **World observations and B load receipts are models, and the A
packets were created before those model reservations.** This does not prove
dynamic game Submit binding or successful B gameplay reload.

Reports go to ignored `.local/checkpoint-components/<timestamp>/`; individual
builds and detailed logs remain under the named ignored `*_runs/` directories.
Each stage is reported separately. Even a successful summary always keeps
`complete_game_pipeline_validated: false` and `actual_two_games: false`.
This is an offline development check, not a playable multiplayer launcher.

## Dynamic A save request check (Windows)

```powershell
py -3 tools/check_dynamic_save.py --fixture-root "D:\SAN14 private research\mod_research"
```

This newer entry explicitly builds `a_save_ipc_test_build.py`, then passes that
exact successful build to `a_save_ipc_flow_test.py --build-run`. It checks current
source and executable fingerprints, uses an owned native child, and creates each
diagnostic file **after** its Room reservation and actual named-pipe Submit.
The same retained Owner handles two requests; the existing TLS download and
SQLite journal consume the resulting bytes. Packets are not pre-generated.

The client authenticates the kernel pipe server PID and creation time. The
server pins its allowed local client process, limits its ACL to the current
user, and rejects remote pipe clients. Lost Submit replies never cause replay;
Stop and faults revoke Room downloads. Tests also exercise stop during the
native admission callback, stale completed bytes, and malformed/replayed frames.

This needs the private `checkpoint_push_profile.h`, Windows x64 MSVC and Python
`cryptography`. The tool does not attach to any game, operate a window, discover
processes or call historical live installers. Its saved files are 32-byte
fixture data, **not SAN14 saves**. Real game business functions, world snapshots
and B load receipts remain test doubles/models. A production launcher and a
trusted complete input/write-exclusion permit are still missing. Passing this
check does not enable Ready, grant save permission, or prove native B loading.

The combined report is saved to ignored `.local/dynamic-save/<timestamp>/`.
Build/flow logs are preserved separately, including failures. It always reports
`complete_game_pipeline_validated: false` and `actual_two_games: false`.

Separate source checks are documented in
`work/mod_research/a_save_input_handoff.md` and
`work/mod_research/b_reload_title590_handoff.md`. They exercise the A global-UI
source and B Title +590 worker source, respectively; neither is a full input
lock or a complete native save/load pipeline.

## Private fixture paths

The latest planning/menu/reload compositions have explicit offline entry points:

```powershell
# Owned debugger targets and menu memory only; this is not --preflight/--record.
py -3 work/mod_research/reward_menu_observation_test.py

# Require the private fixture root described below. No installed game access.
py -3 work/mod_research/planning_input_interlock_test.py
py -3 work/mod_research/b_reload_lifecycle_queue_test.py

# Supply the exact new PASS interlock fixture, not the old Ready worker.
py -3 work/mod_research/reward_interlock_flow_test.py --native-fixture '<new interlock run>/fixture.exe'
```

These cover different layers and are not a playable end-to-end launcher.
The input interlock retains explicit uncovered consumers/writers; B uses a
diagnostic second file and constructor/business substitutes. Menu observations
are read-only and must never be replayed as commands that may already have run.
See the corresponding `*_handoff.md` files for source pins and remaining gates.

Private inputs are unnecessary for the protocol checks. To diagnose their location without reading their contents, copy `private-fixtures.example.json` to an ignored local config and edit the root:

```powershell
New-Item -ItemType Directory -Force ".\.local" | Out-Null
Copy-Item ".\tools\private-fixtures.example.json" ".\.local\private-fixtures.json"
py -3 ".\tools\dev_check.py" --config ".\.local\private-fixtures.json"
```

Alternatively:

```powershell
py -3 ".\tools\dev_check.py" --fixture-root "D:\SAN14 private fixtures"
# Or set SAN14_PRIVATE_FIXTURE_ROOT in the current shell.
```

The diagnostic reports only existence and file sizes. It does not load, hash, validate or redistribute game images or saves. Paths in `files` must remain below `root`. This configuration does **not** automatically rewrite hard-coded paths in historical research scripts. Different native harnesses additionally require their own generated headers, native DLL/EXE builds, captured samples, exact game-build hashes and historical evidence.

## Results and exit codes

`summary.json` gives protocol status and separate environment status. `protocol-unittest.txt`, `protocol-result.json`, `room-tls-result.json`, `worker.log`, and `environment.json` provide details. Temporary TLS private keys/invites exist only in the ignored test scratch area and are removed by the original selftest cleanup.

- `0`: selected tests succeeded; environment and fixture availability may still be incomplete.
- `1`: a selected test or worker failed. Read the logs.
- `2`: invalid arguments/configuration.
- `3`: tests succeeded, but `--strict-env` found missing dependencies or a missing Windows x64 MSVC environment.

`--output-dir` overrides the default. Keep that directory private/ignored: diagnostics contain local paths. A protocol pass is not proof of a two-computer match, native loading, battle determinism, or complete game synchronization.

## Menu, window and logical-period successors (offline only)

These explicit tests do not find or open the game. They require the documented
local private archive/profile and Windows MSVC dependencies. Generated native
code copies, DLLs, raw results and diagnostic saves stay in ignored run folders.

```powershell
py -3 work/mod_research/reward_menu_handoff_gate_test.py --archive-root "<private archive folder>"
py -3 work/mod_research/reward_menu_completion_test.py --archive-root "<private archive folder>"
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<private mod_research folder>'
py -3 work/mod_research/planning_period_owner_test.py
py -3 work/mod_research/planning_input_boundary_test.py
py -3 work/mod_research/planning_input_boundary_period_test.py
py -3 work/mod_research/planning_period_session_test.py
py -3 work/mod_research/planning_input_resident_test.py
```

Read the [menu](../work/mod_research/reward_menu_handoff_gate_handoff.md),
[period](../work/mod_research/planning_period_owner_handoff.md), and
[window](../work/mod_research/planning_input_boundary_handoff.md) handoffs first.
The new period Owner/Controller replace their earlier implementations at link
time; never link two implementations for the same physical slots. Window tests
use their own hidden HWND and actual message threads, not game UI automation.
These are not native installers or full input/simulation permits.

## Save dispatch and cold wait successors (offline only)

```powershell
# Self-owned threads only; MSVC required, no private game archive needed.
py -3 work/mod_research/a_save_dispatch_mailbox_test.py
# Existing pinned archives required; neither command discovers the game.
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<private archive folder>'
py -3 work/mod_research/a_save_dispatch_parent_audit.py
py -3 work/mod_research/b_reload_cold_wait_test.py
```

Read [mailbox](../work/mod_research/a_save_dispatch_mailbox_handoff.md),
[parent](../work/mod_research/a_save_dispatch_parent_handoff.md) and
[cold wait](../work/mod_research/b_reload_cold_wait_handoff.md) first.
Config port compatibility is not a running IPC Server or native Save host.
Cold wait is a separate pre-registration component, not integrated into the
existing Runtime; all producers must obey a separately established host lock.
No command grants a production permit or performs a real save/load.

## Pipe/mailbox and original cold registration compositions (offline only)

```powershell
# Actual owned child process, named pipe and mailbox; Owner business doubles.
py -3 work/mod_research/a_save_dispatch_ipc_test.py
# Pinned private inputs required; actual original RegisterColdPool in owned PE.
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<private archive folder>'
py -3 work/mod_research/b_reload_cold_registration_test.py
```

Read [IPC](../work/mod_research/a_save_dispatch_ipc_handoff.md) and
[registration](../work/mod_research/b_reload_cold_registration_handoff.md).
These are explicit successors; do not link both lifecycle implementations or
call the old Bootstrap after the new Prepare has already initialized it.
Neither test opens the game or supplies a production save/load permit.

## Actual save Controller host and cold Bootstrap queue (offline only)

```powershell
# Owned processes, actual Owner/Controller and pipe; save business doubles.
py -3 work/mod_research/a_save_dispatch_host_test.py
# Private archive root must be outside this repository.
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<private archive folder>'
py -3 work/mod_research/b_reload_cold_bootstrap_test.py
```

Read [A host](../work/mod_research/a_save_dispatch_host_handoff.md) and
[B Bootstrap queue](../work/mod_research/b_reload_cold_bootstrap_handoff.md).
Both keep generated inputs and artifacts outside the repository. A still has
the documented original-machine private runtime dependency; B requires pinned
archive inputs. Neither command opens the game or proves real save/load readiness.
