# Read-only CApp parent boundary observation

2026-10-09. This author did not open/discover the game, Steam, UI or current saves. No live preflight/record ran here. Only owned memory semantic processes ran, and all exited; no active observer or debugger remains from this work. Frozen predecessors and A Host are unchanged.

## Deliverable and exact boundary

`a_save_parent_live.py` offers explicit `--preflight` and `--record --pid --tested-build`. Both require a passing current build; record repeats preflight. Default help and missing-PID rejection were exercised without importing the game reader. Preflight reuses the supported EXE/birth/slot34 Zhang Lu/date/exact five-state stack/no-debugger/original User+Game slots checks, then checks four additional native instruction anchors in the same process birth/base. The recorder repeats its native binding checks before attaching.

Four fixed execution breakpoints observe `13DC09`, `13DC0E`, `50B598`, `50B632`. The first complete call establishes parent TID/RSP/App RDI; subsequent calls and returns require those identities and selected FormalUser unchanged. Manager RCX must match on entry. Initial mid-frame hits before the first call are censored/count-only. Thereafter out-of-frame task hits, wrong TID/RSP/App, changed formal state identity, unexpected slot/current-state/worker or nonmatching yielded worker reject.

Every parent call and return emits all five actual formal states, including `state+50`, sampled worker, callable, done `+58`, yielded `+78` and worker thread. Creation/completion points additionally read the actual `[RSP+40]` slot, verify it belongs to the formal stack and manager current state matches. `50B632` is explicitly labelled `complete_or_yield`: a remaining worker is required to match RDI and have its actual yielded flag. These snapshots do not prove task method bodies ran exactly once or all workers/writers finished. Stable formal state/vtable identity is pinned at the first before snapshot; no RTTI spelling is invented in the log.

The observer stops after 16 matched parent frames, or bounded timeout/cancel. A return is **not** a global worker join. Captured output is for deciding the next genuine Host hook, not a production permit. No caller fields, instructions, vtables or business data are written; debugger execution registers/RF are managed by the unchanged reviewed core. Debugger timing can perturb scheduling.

## Core provenance, tests and pins

The generated production `.cpp` differs from frozen `a_save_observation_status.cpp` only in the two payload/binding include names. The generated binding differs from its frozen predecessor only in the generated anchor-header include and the allowed first RVA. Core DR6 ownership, all-six-register restoration, pending-owned-event drainage, process birth/EXE checks, and retained-cleanup behavior remain unchanged.

Final offline build: outside repository `work/mod_research/a_save_parent_live_test_runs/20261009-111112-315596/result.json`.

- Result SHA256 `fea2db9e44a24583a18a5381949b092ace6aef8603ec5cf06cb8fe6a424ea377`.
- Production observer SHA256 `0d0404ed75dfb3fd93b4151d82eb3099e7ca1b7e075b2f24ead7fb17bea7a40c`.
- 24 source pins, four generated files, four executable/object hashes. Four semantic cases PASS: 16 normal frames with actual sample-reader accesses to owned modeled task fields; wrong return RSP, wrong thread, changed FormalUser rejected.
- These contexts are models, not debugger/game execution. Shared debugger lifecycle evidence is the existing 39/39 `a_save_observation_status_test_runs/20261008-202814-533972/result.json`; this build verifies its 20 exact source identities and records its result SHA. It does not rerun that large matrix or pretend its old Save payload tested this parent payload.
- Private anchor source is the existing flat `game-runtime-image.bin`, SHA `5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`; header/binary/raw trace remain private. No archive is read from the installed game.
- Earlier successful builds `110856-428052`, `110943-072196` and `111101-480572` are retained. The attempted shell edit before `111101` failed to parse and did not modify source; that build repeated the previous source. The final build adds log-write failure checks after both ordinary and final sample flushes. No failed native build/test occurred in this delivery.

Build: `py -3 work/mod_research/a_save_parent_live_test.py`. It uses `SAN14_PRIVATE_FIXTURE_ROOT` if provided, otherwise the established outside-repository private directory. Source/produce paths must be accessible on the machine running the test; this is not a portable packaged plugin.

## Root operator steps

After source review, use a newly verified PID, never a historical PID:

```powershell
py -3 work/mod_research/a_save_parent_live.py --preflight --pid <CURRENT_PID> --tested-build <PASSING_BUILD_DIRECTORY>
py -3 work/mod_research/a_save_parent_live.py --record --pid <CURRENT_PID> --tested-build <PASSING_BUILD_DIRECTORY> --seconds 20
```

No user Save/Load/turn action is required: remain on the idle baseline map. Inspect raw before/after state records and task identities, not just `CAPTURED`. Each record run writes a new outside-repository directory. If cleanup remains pending, retain the observer: launcher never kills it. `CAPTURED` requires clean verified detach and the full 16-frame summary. False `all_workers_complete_proved`, `all_writers_excluded` and `production_permit` remain intentional even on successful capture.
