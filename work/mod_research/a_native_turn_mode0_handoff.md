# A native turn: strict planning mode zero successor

This is the existing two-generation native-turn Runtime with the real-game mode-zero Inspector correction and Initialize-only first-failure diagnostics. It does not replace that Runtime with the single-period Owner used by the successful A automatic save. This development accessed only repository/private evidence and self-created processes; it did not open the game, Steam files, UI, or current saves.

## Exact production changes

- The actual Inspector TU is `a_save_planning_mode_input.cpp`, already validated by the single-save game run. Its final cache-mode comparison requires exactly zero. Modes 1 and 2 are rejected; queue, six-state, source, pending-state and scoped authorization checks are unchanged.
- `a_native_turn_mode0_owner.cpp` is generated from frozen `a_native_turn_owner.cpp` by adding the existing trace header/namespace and replacing the lifecycle include with `a_save_initialize_trace_lifecycle.inc`. All Running, transparent native forwarding, Owner refresh and repeat behavior remains from native-turn.
- The Controller TU is `a_save_initialize_trace_controller.cpp`; the existing trace implementation is compiled once and linked. DATA remains 144 bytes, stage at offset 140, and only records the first failure in an Initialize dynamic scope. Its presence is diagnostic, not authorization.
- The same `a_native_turn_runtime`, Parent, Gate, Control and exports implementations remain linked. Typed exports 1–10 are unchanged. The strict repeat publisher is still required for restoration.

`a_native_turn_mode0_test.py` uses the hash-fixed successful native-turn generated fixture/compile commands (`155031-692039/case`) and production inputs (`155107-507427/abi/production`). It checks their exact manifest hashes, all source hashes, generated inputs, private profile and actually copied dependency binaries. It does not rerun or silently rewrite historical generators. The original Owner remains in the source closure as a checked generation input; the manifest explicitly lists the new actual compiled TU rather than claiming the original Owner was compiled.

## Final executed evidence

`a_native_turn_mode0_runs/20261009-232744-407945/result.json`:

- **PASS, 4/4 owned-process cases**, full production DLL build, actual original 1–8 ABI and additive 9/10 ABI against that exact DLL, original launcher build approval and unique-artifact lookup.
- Result SHA-256: `3b905485a78bf04e54eaa3031a07c6ef2fc7afebc7a8e60417256310025c0b18`.
- 133 source identities, 43 private inputs, 13 generated files, 85 binary/object products, 20 records; all rehashed after execution.
- Normal case: two actual Runtime/Parent/Controller/Owner/Gate/Driver/IPC observations, Submit, Copy and releases. During Running, Strategy/User leave the owned stack, old objects are cleared, new addresses are supplied, and reports delay rebinding until cleared. The actual second Controller initialization keeps cache mode zero. Both returned packets pass the existing decoder, with generations 1/2 and dates 203-08-11/21. Native business/world/serializer bytes are explicit substitutes, not real game saves.
- Stop-running: one delivered artifact, no second request; original callbacks stay transparent and Running/drainPending remain set. This proves conservative refusal of restoration, not that native advancement can safely be aborted.
- Mode 1 and mode 2: the actual Parent invokes Controller Initialize, which records stage 46 / error 0 / StateTransition / five states / empty queue and refuses initialization before any Save bind, queue or completion. The fault changes only the owned cache value immediately before the real Parent call.
- In normal/Stop cases the established current-state tests remain: unclaimed current zero, wrong current and current zero inside native body are refused. In the two negative mode cases, only that separate native-body Pointer expectation is skipped to allow the real Initialize failure to be returned and inspected; no production predicate is bypassed.

Full production DLL SHA-256: `1dcd09ec0f592feb410d1039d5a6d52490fec0ae2a40fc43778e56382a28a573`.
Compatible bundle manifest SHA-256: `f5f6e4a91e33508b723315d0417c3702b44783c30cf8b67e624b1bd33b424380`.
Actual new-DLL additive ABI result: `a_save_repeat_exports_runs/20261009-232821-575477/result.json`, SHA-256 `3955ed9ca791e99fea7416df849f0548eccfe7d8974ab412602d659317fef4dd`.

Failures remain private: `232440-111539` failed compilation because the new include needed the trace namespace/header; `232505-925329` compiled production but the new negative fixture treated void `Snapshot` as bool. Both were narrow source/fixture corrections. `232600-032279` passed all four cases and ABI; final `232744-407945` adds the actual imported Python source closure and validates the already-passing launcher test evidence. Production and fixture semantics were not changed between these successful runs.

## Executable candidate, not an automatic game command

From the repository root, the offline rebuild is:

```powershell
py -3 work/mod_research/a_native_turn_mode0_test.py
```

The old launcher accepts the new bundle without weakened checks. For a newly captured, supported process only, the four approved paths are:

```text
--build-run ..\mod_research\a_native_turn_mode0_runs\20261009-232744-407945\bundle
--repeat-abi-run ..\mod_research\a_save_repeat_exports_runs\20261009-232821-575477
--publisher-build ..\mod_research\a_save_repeat_publish_runs\20261009-142815-825524
--launcher-test-run ..\mod_research\a_native_turn_start_test_runs\20261009-172106-322176
```

Parent controls fresh process capture, backups and explicit execution through `a_native_turn_start.py --execute --pid <fresh-pid>` with those four arguments. Default help does not access a process. Do not reuse a previously stopped/claimed Runtime. The bundle contains only one matching runtime DLL and one dependency DLL; the separate owned test directory is outside that bundle, so recursive artifact validation remains unambiguous.

The human should advance only after the launcher emits `running-await-human`, without new orders; close ordinary reports and stop at any event requiring a choice. There is no automatic advancement call. Natural advancement may alter the game's own autosave; the current conservative final file check can then report INCOMPLETE even if both specific automatic artifacts completed. Preserve that distinction and evidence rather than rewriting inventories or allowing an unexplained file change.

If initialization fails, the existing `a_save_initialize_trace_read.py --observe --run <new-live-run>` can read the new DATA record without calling an export. If Stop occurs during unresolved Running, cleanup deliberately refuses restoration: retain the modules and evidence and use the established normal game exit path. Do not force unload, clear once claims, or replay requests. Nothing in this offline result proves a real native turn, a second automatic game save, B-loaded coordination, two remote clients, full writer exclusion or UI masking.
