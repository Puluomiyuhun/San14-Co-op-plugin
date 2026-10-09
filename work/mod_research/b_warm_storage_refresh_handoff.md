# Warm storage refresh: diagnosed cache mismatch and bounded successor

2026-10-09. This task used repository/private records and owned test processes only. It did not open the game process, Steam files, or UI. The parent agent collected the separate real-game evidence and managed game shutdown. No frozen source was changed.

## Actual failure and prior success

Real diagnostic `b_warm_pair_diagnostic_runs/20261009-212018-163311` reached `b_warm_profile_request.cpp:73` (`fresh_complete_native_reads`) and rejected before any pending-slot CAS or native load. First profile was the correct same-date 203-08-11, current/source Zhang Lu force 12, target Liu Bei force 2. The private source was original slot34, 274920 bytes, SHA `afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95`.

The other agent decoded two consistent native read Evidence records from the parent-collected owned-bank `.data` snapshot. `native-size-audit.json` SHA `3b3f7f9a8d8ebb4d023ba2154a241dcf8f7e4990bc2ff2fc191e40a9af3c92eb` records `native_size_before`, exists calls 1, size calls 1, read calls 0, native size 274880, and local SHA matching the new 274920-byte file. This is a storage namespace/cache mismatch, not evidence that date/player guards are wrong. The public `requestReadSha` is only the second native hash, so its zero value alone was never sufficient to locate the failed read stage.

The prior real single-load success, `checkpoint_complete_live_v2_runs/20261007-163447-239499`, used the older CC03 identity: 274880 bytes, SHA `88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c`. Its local file and native namespace matched. The current configuration's different size is intentional; weakening the read size/hash test would allow loading the wrong bytes.

The old `native_storage_publish_core` cannot refresh this destination: it fixes the old size/hash and requires native absence three times. The old `b_warm_coordinator.run_two` also physically replaces the target and holds a deny-write target lease through `port.load`. A native FileWrite inserted underneath that sequence would either see inconsistent old native metadata/new physical bytes, or encounter Windows sharing denial. Both the staging order and the native publication path need explicit successors.

## Implemented component

New `b_warm_storage_refresh_core.h/.cpp` exposes `Refresh(Input, Api, Evidence)`. Input provides an immutable private new-file copy, its exact Windows file identity, fixed CC03 basename/new size/hash, expected previous native size/hash, owner binding, and exclusive intent path. The previous identity must come from the owner's verified old target/backup, not an untrusted peer assertion.

The core holds the private source deny-write handle throughout, validates source bytes, reads the old native contents twice against the expected old hash, creates and flushes one `CREATE_NEW` intent, calls the pinned FileWrite ABI once, and invokes the unchanged `native_storage_read::Verify` for two complete new native reads. Intent or write uncertainty is terminal; no rollback, delete, unload, or retry with a new intent is provided. The input callback must establish private source versus native destination separation, owned destination authority, the actual permitted caller boundary, and FileWrite/interface identity. The core does not independently discover or prove those relationships.

This is a compiled production component, **not yet wired into the production Owner/launcher**. It creates no scheduler/input fence and always reports `nativeLoadAuthorized=false`. It deliberately handles an existing native destination with a known previous hash; it is not an arbitrary overwrite or native-absence initialization API. There is no Steam API import.

## Test evidence

Run `python work/mod_research/b_warm_storage_refresh_test.py` from the repository.

Final run: private `b_warm_storage_refresh_runs/20261009-213256-631945/result.json`, SHA `7ebd84ca5287305d3917de642b605d9e1406c17c6bc0c8b18fcd25ca6f703cbf`, **6/6 PASS**. All six owned fixture processes exited normally with code 0. No debugger/publisher or background worker was created. Earlier `212917-327737` passed four cases and is retained; review then restricted the destination to exactly CC03 and added the corresponding rejection case. The subsequent five-case success `213125-230749` is also retained. Root review then found that the old-byte read buffer needed per-read poison filling to avoid inheriting the first read when a broken second native read reports success without writing. Each old read now fills its buffer with 0xA5, matching the frozen read core behavior. There was no failing test execution; this defect was found by source review.

- Two generations: same target and native cache, distinct immutable source files/sizes/hashes; both publications complete old two-read validation, one FileWrite, and new two-read validation. Source write probes fail with actual Windows sharing violation throughout publication.
- Wrong old hash rejects before an intent or FileWrite.
- A second old native read that reports the full length but writes no bytes rejects before intent creation, with zero writes; it cannot reuse the first read buffer contents.
- A different valid `.s14` basename with a matching private source leaf rejects at the input stage; this API cannot publish arbitrary saves.
- Actual target read-only/deny-write lease makes FileWrite return false; the attempt remains uncertain and a repeated call using its existing intent cannot write again.
- A successful physical FileWrite with deliberately corrupt native cache fails readback; uncertainty and the intent remain, with no second write.

Native exists/size/read/write methods and the caller-boundary validator are explicit owned-process substitutes. Real Windows file identities, sharing rules, durable intents, core code, SHA256, and frozen read-core verification execute. This is not evidence of actual Steam refresh, real native thread affinity, or two successful game loads. Synthetic payload sizes are 701→903→1127, not game save bytes.

The result pins six source files, one generated build script, four compiled EXE/objects, and all test logs, intent records, and owned data files. Production refresh object SHA `b6356a9d75ed769971a5606c93505765de08173246cc4c47891068f57deb2a32`. Core cpp SHA `a52304afef7a6ed192bf4972e8beefcf8c8bb7eb286045fbeb854c0403a0a0f1`; header SHA `3627ce02ba08fa6707ee4c8d773447c5e10bab2d6eb700bc5e550f12b172352d`. No fixture preprocessor macro is used in the core or read core. MSVC emits one C4996 warning for `strcpy` after the explicit exact CC03 basename check into a 64-byte zeroed field; no compile errors.

## Smallest remaining actual integration

1. In a fresh diagnostic lifecycle, preserve and verify the old physical CC03 and matching native identity. Do not replace it first. Create the new private copy and a durable owner-bound refresh intent.
2. At the already authenticated native storage call boundary, with no target deny-write lease, bind and revalidate FileWrite v014 slot 0 in addition to the existing read endpoints (the old read-only validator alone does not prove the write binding) and invoke Refresh. Keep the private source pinned. Unknown or failed write retains all evidence and ends this attempt.
3. Only after refresh and native full readback, acquire/recheck the target lease and proceed to the unchanged exact-byte pending-slot commit and normal warm load. If publication is inside the existing GameBefore transaction, the outer launcher must stop holding the target lease and rely on the explicit native owner/private-source chain until the later appropriate lease point.
4. After actual first-bank completed retirement and six-slot restoration, repeat the same order for bank two. Do not reuse an old Session/once/intent or claim that successful cache publication alone proves native load completion.

No new global-fence prerequisite is introduced for the user's no-new-command diagnostic. The missing item is concrete native FileWrite/ownership integration plus the target-lease order, not more relaxed hashes or another blind restart.
