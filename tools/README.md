# Offline developer check

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

## Private fixture paths

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
