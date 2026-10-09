# Resident remote wiring: one owned-process completed bank

Final result: external `work/mod_research/b_warm_resident_runs/20261009-183349-584071/result.json`; SHA-256 `6cded90f04ddef9f21b406d2a19854d7201fb118ab3784b0e869bd7037878b99`.

The original `b_warm_coordinator.Resident` is imported unchanged. Its constructor opens the real owned process; `_module` actually copies and remotely loads DLLs, checks mapped image/export/bridge bytes and module identity; `open_bank` reads the real typed description. `Calls` invokes the actual `InstallBWarmProfileOwner` remotely, including the real one-shot profile Capture and complete Owner configuration/installation. The bank is not installed from its environment-preparation helper.

After Install returns, the owned EXE's original main thread handles a stdin test signal and executes the native-business double frame sequence through the installed six physical bridges. All real factory guards and Storage Binding/Gate remain active. Bytes, lifecycle, identity and planning receipts complete; the actual Session seals and restores all six original sources. Two remote report samples have increasing sequences 69 and 70. Each reports 57 guard checks and 72 storage validations. Both hardware receipt and retirement receipt identify host main TID 12808. A separately loaded actual coordinator helper DLL receives real remote typed Prepare and Observe commands, and confirms firstCompleted=1, secondCompleted=0, stage=1. No fabricated completion JSON is submitted to it.

The child exits normally with exit code 0 after both DLLs remain resident through the test. No game, Steam process, current save or UI is touched. Only the explicitly created host PID is opened. No remote thread or DLL is terminated/unloaded on the successful path.

## Exact test scope

The new `b_warm_resident_host.cpp` provides a shared simulated image, six actual source slots, stable host native-original/caller functions and a main-thread frame trigger. `b_warm_resident_test.py` generates a phased successor from the fixed full-factory-pair fixture: Prepare creates environment/configuration without consuming the production profile Capture; the actual remote Install consumes it; RunFrames executes the original completed factory sequence on the host main thread. Actual native Owner, Session, guard, bridge and retirement sources are unchanged. Existing diagnostic fixture macros still adapt environment/native source mappings as documented in the factory-pair handoff.

This test does **not** call the entire `Resident.load` method. In particular, production `capture_planning`, actual Steam module sampling, `build_config`, post-load GameReader snapshot and production `completion` classifier are not executed. The classifier was not called and rejected; it was not called at all. Its explicit real-game caller/original/site checks (`b_warm_start_acceptance.py:47`, `:92`, `:104`, `:176`) cannot truthfully accept this host-ASM, two-module environment. No fields are rewritten to impersonate those real-game origins. This result proves real remote module/control transfer and completion within the existing owned factory boundary, not a legal game load or complete two-bank Resident run.

The native helper is the approved production build from `b_warm_coordinator_build_runs/20261009-181031-457801`. Unlike the prior factory-pair test, it is actually loaded as a separate DLL and called remotely here. The execution still covers only one bank. The predecessor factory-pair test remains the evidence for same-six-slots two-bank handover; the two results must not be silently combined into a claim of two remote production game loads.

## Evidence and reproduction

Run `python work/mod_research/b_warm_resident_test.py`. Generated artifacts go outside the repository. There are 117 source pins, 12 private input pins, 8 generated pins, 37 binary/object pins and 22 observation pins. Imported local Python dependencies are pinned before remote work; an unexpectedly late local import makes the result fail. All final hashes were rechecked after execution. New source hashes:

- host: `54b00d8a5ef584a1b6d252a9f6eaacd8cae4d52339dac2ca2d81139a750ee648`
- test: `791b17e3c8c4fb6f71a800354caea80ce4fa89a7a8ccd231be5f506e3fb5cc6e`

Preserved earlier runs: 182823 compile rejection from a helper parameter shadowing an input stream; 182903 compile rejection from generated path escaping; 182957 missing private pefile dependency path; 183044 actual Owner shape refusal because the generated local path used a forward slash for its final separator; 183133 completed remote chain PASS before final thread/source audit; 183256 completed chain but FAIL for the unpinned late HardwareReceipt decoder dependency. These were test-host/generator defects; none required relaxing a production guard. Final source whitespace checks passed before execution.

## Rules withdrawal and new-world binding

The current rules adapter is not dynamically rebound. `human_rules_activation_v2.cpp:31` checks that `root+0x85130` still equals the prepared world both around reads. Its `:40` fatal retention is permanent. `:97` Prepare is a one-shot New-to-Preparing transition. `:162` Revoke only moves Sealed/Faulted to Faulted; it is not transparent hook removal.

The current external publisher still requires Sealed plus the old world binding even on restoration (`human_rules_activation_publish_v2_inspect.h:49-52`). Therefore Revoke-then-Restore cannot work, nor can restoring only after the world pointer has already changed. Do not bypass these checks.

The shortest existing interface sequence is: while the old world remains in supported idle planning, run the approved external publisher's restore transaction and require its actual RESTORED/source/protection/counter/context evidence; then permit B loading; after genuine new planning and B retirement, load a fresh independently approved rules module, Prepare with newly captured root/world/date/viewer and fixed room human identities, Seal, then publish. Preserve the old module and claims. Any publication/restore uncertainty blocks loading and new installation. Current Resident does not yet implement this bracketing. The publisher's in-flight-thread checks remain required: B's transparent late-bridge behavior must not be assumed to exist in the rules adapter.
