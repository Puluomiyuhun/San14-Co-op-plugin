# Two-file diagnostic: existing startup audit and read-only preflight

The existing `b_warm_coordinator.py` already has a real two-bank CLI and
`run_two`. No duplicate `pair_start` was created. It uses the approved production
bank and helper, captures actual planning bindings, refuses prior PID/birth
attempts, claims one process lifetime, loads bank 0, authorizes bank 1 from the
real native retirement, backs up/replaces the second file and validates the
second load. It is explicitly a controlled two-legal-file diagnostic without
automatic game advance, a network room or a claim of global input exclusion.

One concrete startup defect was ordering: the old main could write a claim and
load the first bank DLL before finding that the first already-staged CC03 file
was missing or had the wrong hash. `--execute` must not be used as a harmless
file/build precheck. New `b_warm_pair_preflight.py` provides that check before
any process access; root's diagnostic successor consumes it.

## Interface

```python
from b_warm_pair_preflight import preflight
checked = preflight(
    absolute_plan_path,
    helper_build=absolute_helper_result, helper_sha256=expected_helper_result_sha,
    pair_build=absolute_pair_result, pair_sha256=expected_pair_result_sha,
)
plan = checked['normalized_plan']
helper = checked['helper']  # result_path, result_sha256, production_dll{path,sha256}
pair = checked['pair']      # same fields
```

Call this before importing/constructing GameReader, opening writable process
handles, writing a claim or loading any module. No PID, process object, native
callback, execution flag or staging authorization is accepted by this module.
No-argument CLI only displays help. Explicit read-only CLI options are `--plan`,
`--helper-build`, `--helper-sha256`, `--pair-build`, `--pair-sha256`.
The tool does not print an execute command or grant permission for another tool.

The exact plan fields remain the existing coordinator's:

- `profiles`: two objects accepted by `b_warm_profile_capture.profile_from_dict`.
  Each has `file{name,slot,size,sha256}`, `before{year,month,day}`,
  `loaded{year,month,day}`, `source{ruler,force,district}`,
  `target{ruler,force,district}`, `currentForce`.
- `target`: absolute existing first staged `svdexccSC03.s14` (slot 63).
- `second_source`: absolute distinct private second archive file.
- `expected_ruler`: current real ruler ID, not an inferred process observation.
- `steam_paths`: exact `steam_api64.dll` and `steamclient64.dll` names mapped to
  explicit absolute local paths.

The unchanged `validate_pair` requires second.before == first.loaded,
second.currentForce == first.target.force, equal source/target identities,
second.loaded exactly the following period, and different file hashes. This
entry is the preprepared two-file diagnostic, not the remote settled-date policy.

## Checks and limits

The preflight uses original typed profile/pair validation and original
`approved_component` build closure verification. It requires first/second actual
Windows file size and SHA to equal the corresponding profile. It rejects aliasing
files and missing/wrong first files before checking builds or accessing any
process capability. Existing file handles reject reparse/hardlink paths and hold
read leases during each read. Paths are explicit fixed local paths. It never
creates a staging lock, backup, intent, target, module or claim.

The exact frozen Steam hash allowlist is copied as data; a test AST-checks it
against `b_warm_start_support.STEAM_HASHES`. This deliberately avoids importing
the support module and its process-memory helpers. Actual files are read via
pinned Windows handles in bounded chunks, allowing DLLs up to 256 MiB rather
than incorrectly applying the 16 MiB save-file limit.

Helper and pair result hashes, source/private/generated/binary pins, production
DLL containment and helper/pair native-source equality are checked. The plan and
two save identities are read again after the longer build checks. Locks are not
retained on return: runtime must still perform its own fresh capture, native
original-source checks, prior-attempt/claim checks, storage and file validation.

Success explicitly returns `game_checks_pending=true`,
`no_execute_authority=true`, `claims_created=false`, `files_staged=false`,
`native_load_permitted=false`, and `archive_content_semantics_verified=false`.
Hashes verify bytes against a plan; they do not prove that archive contents have
the plan's date/force or that a live game has reached a safe boundary. The first
CC03 must already have been prepared under a separate appropriate file-overwrite
and backup procedure. This module does not overwrite a user's slot.

## Existing approved builds and legal-file evidence

Read-only archived build audit:
`../mod_research/b_warm_pair_start_audit_runs/20261009-202418-554052/result.json`.
Both original `approved_component` checks pass and all helper native sources
match the pair. No rebuild is needed merely to repeat these fixed artifacts:

- helper `b_warm_coordinator_build_runs/20261009-181031-457801/result.json`,
  SHA `4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a`.
- pair `b_warm_factory_pair_runs/20261009-181448-912475/result.json`,
  SHA `c13390840e1fbeaf54fde8822add15ef9c44a75967b8c57ea2da2af73247a990`.

The shared slot34 manifest has historical verification of 203-08-11, Zhang Lu
force12/ruler666, size274920 and SHA
`afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95`.
That is the only save authorized for repository publication.

There is a useful **private second-file candidate**, not yet a proven target
date: the successful native human-rules turn
`human_rules_activation_live_runs/20261008-001113-003013` ended at 203-08-21 and
its closeout records only `autosdexSC08.s14` changed. Its round-state file hash
matches both the later known backup manifest and actual private backup bytes
under `a_save_runtime_live_runs/20261009-123703-876595/original-saves`:
size274879, SHA
`7fd89b1e0c0b38e651ffda0ca778474668825be1058161e92fd7587174dd357b`.
This establishes native autosave provenance and association with the turn; it
does not independently establish the file's internal save date (autosave timing
could differ). Do not invent a profile date by filename or searching byte patterns.

Exact source paths/hashes and the explicit unknown are retained privately in
`b_warm_pair_start_audit_runs/20261009-202418-554052/file-candidates.json`, SHA
`4dbf7d65a94ff69987399b55622b1be4b18e230ca3e3f5feb34d635fac930fd4`.
No Steam directory was scanned/read and the candidate is not copied into Git.
A normal load on a fresh test game can establish its actual date/identity before
using it as the diagnostic second profile. This may avoid requiring a new A
automated-save milestone solely to obtain two legal diagnostic inputs.

The failed A run's newly created `mp83d7e462.s14` is not an accepted substitute:
its recorded result is INCOMPLETE, error54 and `real_fresh_save=false`. Do not
promote that file to a successfully verified new checkpoint. The historical
native pair fixture's modified second payload is also explicitly not a legal
archive. Two reliable dated inputs are not yet established merely by those tests.

## Verification

`py -3 work/mod_research/b_warm_pair_preflight_test.py`

Final private result:
`../mod_research/b_warm_pair_preflight_runs/20261009-202759-214380/result.json`,
SHA `7f148f896151f814c7a8c593c4d41c56dec304a032c9ea5be75d0f43a4e89ecf`.
5/5 PASS; 10 source, 2 private build-result and 25 artifact pins rechecked.

Tests use owned temporary save/DLL-named files with real Windows reads and the
actual archived helper/pair approval closure. Only the Steam hash allowlist is
substituted with those temporary bytes' hashes; real Steam is not touched.
Valid files cause no mutation. Missing/mismatched first files reject before a
build callback; no Resident, claim or staging API can run. Second-file/Steam
drift, invalid dates and wrong build hashes reject. Fresh CLI subprocesses prove
default help and importing the module do not import GameReader,
run_autonomous_pilot, checkpoint_complete_live_capture or b_warm_start_support.

This is file/config/build verification, not another native model framework.
No production start, game access, UI operation or debugger ran. No failing test
was discarded; the five-case run passed on its first execution. An initial
historical JSON inspection needed explicit UTF-8 after the default Windows GBK
decoder rejected it; the subsequent read used UTF-8 without changing any source.

Source hashes:
- `b_warm_pair_preflight.py`:
  `bbb76a7fac696b15ca57a9bd4790429ece2104cf96abae40dafcc89af8d31bc8`
- `b_warm_pair_preflight_test.py`:
  `e25f329d8e7d57cec72bc0958ea650b13e3fab248b39fc65ab5316347b9cc8ce`

Root owns the diagnostic successor, public docs and Git. Frozen sources are
unchanged. The old failed game instance must not be repurposed by clearing claims;
process-exit confirmation is tracked by root separately from this file preflight.
