# A observed Room native entry

`a_observed_start.py` is an explicit successor of the approved `a_native_turn_start.execute` lifecycle. It connects real callable installation/Prepare/Plans, the same authenticated native save channel, typed Runtime observations, and `RoomTurnControl` to the exact `ObservedRoom`/`BootstrapCoordinator`. The frozen launcher is unchanged. This module does not create a second network protocol or treat a diagnostic ACK as `loaded`.

## Actual callable entry

The outer network owner must keep the authenticated TLS service alive throughout execution and cleanup. After both seats select/confirm and the fresh coordinator is bound in period 1 PLANNING:

```python
entry = RoomEntry(service.room, coordinator, adapter_key,
                  no_new_commands=True)
code = execute(args, capture_path, captured,
               entry=entry, on_event=on_event)
```

`adapter_key` is the separately provisioned local adapter key, not a peer-supplied callback or key. `args` has the existing `build_run`, `repeat_abi_run`, `publisher_build`, `launcher_test_run`, `wait_seconds`, plus `entry_test_run`. Paths are `Path` objects. `capture_path/captured` come from the original fresh read-only capture. `execute` returns 0/1 and prints its result path under private `a_observed_start_runs`; the retained `entry` exposes provider/binding/control and `status()` after failure. Default direct CLI only prints help; the network CLI is the separate root-owned `observed_host_start.py`.

Before native Prepare, `RoomEntry.prepare` creates the exact observed binding using this control's one-use channel artifact reader, begins same-day bootstrap, and applies `prepare_from_room`. Native room ID, fixed native room epoch, period, native epoch and input digest therefore bind the actual Room before installation. It never edits an installed native configuration. The first published file is same-day; its formal B completion advances checkpoint period while retaining that date. Actual Ready/seal/begin is still required before the one RequestNext and the next-date file.

After approved sources are installed and the real parent reports ready, `bind_runtime` constructs `AObservedBoundary` from the actual reader, captured identity, approved Plans, nonce and retained typed Snapshot callback. It checks an initial observation before enrolling the finite observed adapter. Host receipt keys come from the currently copied channel artifact; host sampling is the existing complete audited two-table projection. No file archive is substituted for a channel artifact, no input fence is asserted, and no A/B observation is replaced by `True`.

`on_event` receives the original stage events. The outer owner can issue A's actual Ready on `await-room-turn`, then independently wait for B's Ready and seal. Only `running-await-human` is the instruction to advance one ordinary turn without new commands. The entry neither advances the game nor answers in-game events. It waits for the second formal completion before normal native shutdown.

## Retained lifecycle and failure behavior

The new execute body retains source/build/ABI verification, full original-save backup, fresh capture comparison, once-claim, absolute dependency/runtime load, exact typed exports, ArmOwner then publication then ArmPublishedSources, bounded parent readiness, actual IPC server lifecycle, artifact disk-byte verification, diagnostic reads, Stop, server exit, repeat drain gate, strict publisher restore, post-turn read-only check and final file inventory. Natural autosave changes are still reported separately and can leave an INCOMPLETE result; they are not silently approved. Modules are not unloaded, once-claims are not reset, and unknown native requests are not retried.

Typed calls now share a lock because TLS handlers also obtain A Runtime observations. A `RemoteCallUnknown` from either thread latches the shared unknown state and blocks all later typed calls and Stop/restore. `close_observation` closes admission and waits for existing enrolled callbacks using the original room → coordinator → provider lock order before pipe/native/reader cleanup. This is a local Python callback lifetime barrier, not a native execution fence.

`a_observed_start_call.py` is a narrow explicit successor of the frozen remote-call helper. Its thread creation, bounded wait, response read and buffer-release predicates are unchanged. Thread-handle/buffer-cleanup and final-log exceptions are captured in the record; an attempted unresolved call always raises `RemoteCallUnknown` first, preserving the remote buffer and log failure. In particular, a disk-full error cannot hide a timed-out native call and cause dependent Stop/restore. Publisher behavior remains the original non-killing bounded process wait.

The predecessor's possible `ProcessAPI` constructor handle leak on a rejected construction remains limited to that controller process lifetime; this successor does not change the frozen class.

## Offline verification

Run only the owned test suite:

```powershell
py -3 -X utf8 work/mod_research/a_observed_start_test.py
```

Final **7/7 PASS**: `../mod_research/a_observed_start_test_runs/20261010-005820-398729/result.json`.

Result SHA256: `ea7bc67a8ffc6aabfc9bff8583fa030d8c43cc31a826cda7d92610aae8cca4b4`.

All **87 source, 9 private build/schema/binary input, and 407 artifact hashes** independently match. Sources:

- Entry: `b4edb77e54a719c585bb861b9aad6fd3d95609fac146191ca8bea94d25fb9de5`.
- Safe call: `e4449143f08d80b98f518ff56314078c52a8aa0a6cdb3e178d05f7a9f60fdc25`.
- Test: `d8a27d3159c60ad3e909996e05109c88c769252ec4074f1690dd8a86d0c39310`.

The new execute itself runs in the integration test: real TLS/SQLite/Room/retained B Session, the actual finite A provider, same-day first completion, real two-seat Ready and seal, RequestNext, new User/Strategy memory layout, second completion, Stop and restoration decision. File backups and inventories operate on owned temporary files. The native process, PE, save channel, Runtime reports, native loads and publisher are explicit doubles; inner launcher result strings do not turn this into a live-game result.

Negative cases verify an unresolved Snapshot originating in a TLS handler prevents Stop/restore and a second Submit; interrupted Running performs known Stop but refuses restoration; false human condition/reused Room is rejected; remote timeout plus failed result logging retains Unknown and its buffer; a running observation is drained before callback admission closes. The existing approved mode0 build, additive 9/10 ABI, strict publisher and predecessor launcher evidence are also actually verified from private archives, including both DLLs and publisher bytes.

The first run `005345-871266` retained a correct normal execute result but failed two outer assertions that expected ValueError instead of the existing RuntimeError; original candidate sources were saved. `005423-054369` and `005544-005041` retain earlier 5/5 results, before the added safe-call and concurrency checks. Their sources/results were not rewritten.

## Scope still excluded

No game process, Steam directory, current save, UI or live native call was accessed in this work. No commit or deployment was performed. Source-only and owned tests do not prove two live clients have run this combined entry.

This A route installs the seven save/parent sources; it does **not** install the six A-side human/AI rule hooks that protect B's force from A's local AI. B's own rule lifecycle does not provide that A-side protection. Therefore the current entry is a no-new-command two-snapshot synchronization diagnostic, not a complete two-player gameplay launcher. Integrating an A rules lifecycle must preserve its real source fingerprints, slot compatibility and retirement order in a separately tested successor. Continuous input exclusion, a scheduler fence and full-world equality also remain unproved and explicitly false.
