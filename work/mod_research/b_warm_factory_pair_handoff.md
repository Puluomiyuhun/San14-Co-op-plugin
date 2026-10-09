# Same-process two full warm factory banks

## Verified result

2026-10-09 final owned-process run: `work/mod_research/b_warm_factory_pair_runs/20261009-181448-912475/result.json` outside the repository. Result SHA-256: `c13390840e1fbeaf54fde8822add15ef9c44a75967b8c57ea2da2af73247a990`.

Two bounded scenarios passed. The successful scenario executes two actual factory installations in one process: each calls `InstallCheckpointCompleteLiveOwner`, actual `Owner::configure`, durable reservation, the six real physical bridges, Session, actual queue authorization, all six attachment guard families, actual Storage Binding/Gate, completion receipts, seal and six-slot `RestoreAll`. Each bank reports Installed=1, SessionState=13, 57 guard checks and 72 storage validations. Guard-family call counts per bank are 19/16/5/9/6/2, with every called check accepted. No guard callback is replaced by an always-true function.

The host has one retained simulated game image and exactly six shared source addresses: five separated image-RVA vtable slots and one host storage-vtable slot. `GuestSessionSlots` contains their addresses; it is not a second set of slot values. Both actual factories attach these exact sources to distinct DLL-local bridges. Stable original functions and callers belong to the host. The first completion seals its Session and restores these sources before the typed coordinator permits the second bank. Old DLLs, old Session state and once claims remain intact and resident. There is no unload, image remap, reset or bridge route to the second Session.

The actual `Describe/Prepare/Authorize/ObserveBWarmCoordinator` implementation is linked into the owned EXE together with frozen `b_warm_two_bank::Handover`. This tests the typed wrapper and the original Handover; it does not claim that a separately built helper DLL was loaded by this test. A launcher using a helper DLL must associate its native source pins with this run.

## Negative boundaries exercised

- Authorize before the first installation and while the first bank is armed both refuse without consuming the eventual permit.
- A separately loaded, stopped but unconfigured candidate refuses. The legitimate second bank can subsequently receive the one permit; repeat authorization refuses.
- While the second bank owns the six slots, every cached first-bank bridge is invoked with inaccessible arguments. Each reaches its stable host original exactly once; neither bank's bytes/load/identity business receipts change, and the second bank's bridge counters do not change. Native business bodies are explicitly bypassed for this late-call probe.
- A second owned process installs the first bank, then changes one checked source byte before Game. The actual attachment guard reports Image, refuses before request CAS, and does not seal. Typed completion/authorization both refuse, and the second bank remains uninstalled. The broken first bank is not repaired or retried; its owned process exits normally.

## Profiles and remaining substitutions

Bank 1 uses before/loaded 203-08-11, current force 12, source 12/666/11 and target 2/952/2. Bank 2 uses before 204-09-01, loaded 204-09-11, current force 2, source 7/111/6 and target 9/222/8. The second diagnostic payload appends 32 bytes to an archived file, producing a different length/hash; it is not claimed to be a legal game archive. File hash, date, profile and identity receipt logic execute, but native gameplay, state reconstruction, input/menu movement, worker work and storage reads remain explicit owned-host business doubles.

The new Owner differs from frozen `b_warm_factory_owner.cpp` only by allowing two approved MEM_IMAGE modules in its existing fixture branch: bank DLL and stable host EXE. Production still requires the main game image and the existing three-module configuration. The fixture uses real disk/header identities, endpoint byte identities and actual module provenance; bank-local temporary configuration objects are replaced with host storage before actual Install. It does not substitute the attachment guards themselves.

The executed diagnostic DLL uses the predecessor's named fixture macros: COMPLETE_LIVE_OWNER, LIVE_STORAGE_BINDING, LIVE_RUNTIME_GUARDS_V2, NATIVE_QUEUE_ADAPTER, CC_LOAD_OBSERVER, CC_LOAD_LIFECYCLE, TITLE_IDENTITY_ADAPTER, FORWARD_NATIVE_SESSION and FORWARD_PLANNING_OBSERVER, all with the CHECKPOINT_ prefix and _FIXTURE suffix. These adapt environment, archived-source and caller mappings. The generated guard-access translation unit also retains the predecessor's unused legacy comparison helper; the actual factory path calls the corrected real guards, not that helper or the predecessor's bypass factory. This is not a claim that production code ran inside SAN14.

A complete production DLL is separately compiled with these fixture macros disabled and the corrected `b_warm_two_bank_guards.cpp` target-force predicate. Its production Owner configure path is unchanged. Path: final run `composition/production/checkpoint_complete_live_owner_v2.dll`; SHA-256 `e9766e073b4a4b63d230c1f7e788d477c4f5ebb7e660a2ed3dcc5b7c8342bf05`. That production DLL was built, not injected or executed here.

## Reproduction and evidence

Run `python work/mod_research/b_warm_factory_pair_test.py` from the repository. It creates all generated code and binaries outside the repository. The fixed previous factory result and its consumed source/private/generated closure are verified before use. Final manifest family is `san14.b-warm-factory-pair.v1`; `full_factory_pair_passed` and `inputs_unchanged` are true. It has 89 source, 11 private input, 10 generated, and 67 binary/object pins; all were independently rehashed against disk after completion. The generated driver is itself pinned. The actual coordinator and Handover headers/implementations are included.

Both owned host invocations returned normally; no debugger or independently running worker was started. No game process, Steam save, UI, or installed executable was accessed. The earlier successful normal-only run `181121-558402` remains archived and is superseded by the final normal-plus-failure run. All four implementation/test files passed trailing-whitespace and final-newline checks before final execution.

Next real milestone is the controlled warm launcher using approved production artifacts and two genuinely valid archives, with a fresh actual planning capture for each bank and original completion/retirement acceptance before native authorization of the second. This result closes the previous missing two-factory composition, but does not establish real-game continuous loading, visual masking or cross-computer networking.
