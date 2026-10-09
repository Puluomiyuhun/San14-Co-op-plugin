# A single-save next live trial: offline candidate audit

2026-10-09. This work opened no game process, read no Steam directory or current saves, and made no native call. It did not launch the production startup or a debugger. The root agent owns any subsequent live trial.

## Candidate and precise gap

The existing `a_save_diagnostic_start.py` already provides the complete single-request startup, real named-pipe Submit/Copy, fresh artifact comparison, Stop and external source restoration. A new launcher is not needed. The useful missing precheck was an entirely offline verification of the exact retained build, including private/generated inputs, artifacts, typed ABI and required abort/first-failure exports before any capture touches a game.

`a_save_next_audit.py` implements that bounded check. It has no process API and defaults to help. It approves only these previously tested manifests by exact result hashes, then checks their complete named source/artifact closure:

- Runtime outer: `a_save_abort_pending_runtime_runs/20261009-135510-973447/result.json`, SHA `85a2bf2d9c176cf8917ae757d492cb19d64e2ea577003dbf58ac5e1c64148974`.
- Runtime inner ABI: `.../abi/result.json`, SHA `4b6f834e5b35a6860f9ff58bb5e1fd70d856842502b314438fdccc9604e98703`.
- Abort-aware publisher: `a_save_abort_publish_runs/20261009-135151-357545/result.json`, SHA `9d278c350607379b5e68113ea5181a0d0e539dfa29a10cfb04e9824fbaa4c66f`.

The Runtime DLL remains `8125ec17de92bd46f9fcda780008990b5c8c1b9456630f895de8bb39886054cb`; publisher remains `12eaf83f93ca772187e58041f940aed48898de57251e62b9c3c967efb2d12c89`. No production source or binary changed. Imports are ADVAPI32, KERNEL32, bcrypt and the pinned `checkpoint_planning_hold.dll`; the latter must be loaded from the copied approved path by the existing launcher. Current launcher/control/capture source hashes are separately recorded, not falsely described as original native build inputs.

The checker verifies 121 manifest source references (overlapping sets), 32 production binaries/objects, eight publisher artifacts, three private build inputs and the generated files. Its 166 distinct file pins also include manifests and current launch/control code. It compares C++ schema sizes/offsets against the actual Python structures and parses PE exports; it does not execute the DLL's ABI test again or load that DLL into any process. The retained build already records actual owned-process ABI execution.

## Retained fixes and limits

The candidate includes the strict own-Save queued Game path, five-state pending User path, six-state covered User path, and original report cursor/tree/source checks. These specifically address false planning-only refusals while normal Save is queued or covering User. The separately named abort successor only retires an actual stopped error54 request with complete native phase/join/finalizer evidence and a quiet authenticated original host boundary. Error54, revocation, once claims and Unknown remain; no artifact or Ready is invented. External restoration consumes the matching retirement DATA receipt and still checks actual bridge/Host activity.

The earlier real failed save created a file but did not complete verification/restoration. The combined fixes have passed owned composition tests, not a fresh actual game save. This trial remains necessary; neither this precheck nor the previous B two-load success proves A save success. The old failed process has already ended according to the current main HANDOFF, but a new PID/birth and fresh current state must be verified again by the root before execution.

## Exact operator flow

From the repository root, the following first command is entirely offline:

```powershell
py -3 work/mod_research/a_save_next_audit.py --check
```

For the live trial the user starts a fresh game, reads slot34, and leaves Zhang Lu's 203-08-11 map idle. No new command, manual save, date advance, menu opening or additional B installation is needed. No old PID, capture, claim or nonce is reused. The root obtains the current PID; these commands intentionally contain a placeholder instead of a stale process identity:

```powershell
# Read-only game capture, no installation or Submit:
py -3 work/mod_research/a_save_diagnostic_start.py --pid <freshPID>

# Only after the fresh capture and authorized trial prerequisites have passed:
py -3 work/mod_research/a_save_diagnostic_start.py --pid <freshPID> --execute --build-run ..\mod_research\a_save_abort_pending_runtime_runs\20261009-135510-973447\abi --publisher-build ..\mod_research\a_save_abort_publish_runs\20261009-135151-357545
```

`--build-run` must name the inner `abi` directory, not the outer Runtime run. The executable checks all source identities again, backs up the whole current save set, generates a fresh `mpXXXXXXXX.s14` name and once claim, recaptures before mutation, installs through the actual parent boundary, and sends exactly one request. It verifies that exported bytes, the new local file and reported SHA all agree. It then stops and waits for the service, requires native drain, restores the original three call sites/four slots, performs read-only postchecks and compares every pre-existing save. User action is not required for those normal steps.

Success is only `PASS_REAL_SINGLE_FRESH_SAVE` together with `real_fresh_save`, `cleanup_verified`, originals unchanged and exactly the expected new file with the same hash. The new file is a diagnostic artifact and is not automatically loaded or used for a multiplayer period. Do not clean it up while the game is active merely because this document lists the next operation; retain the archive and use the root's confirmed closeout procedure.

On failure, retain `first-failure-diagnostic.json`, final typed snapshots, publisher output, save inventory and once claim. Unknown remote calls preserve their allocation; an unresolved publisher may own a debug event and must not be killed. No automatic replay, new claim for the same lifetime, forced release or module unload is authorized. A known failure may have a valid abort-drained receipt and complete restoration, but that does not change the failed-save result to success. If cleanup cannot prove quiet/restored, preserve evidence and arrange normal game exit through the root's recovery procedure.

The inherited `ProcessAPI` constructor may retain its opened handle until the controller process exits if it rejects before construction completes; this is a resource limitation, not native save completion or permission to retry. It was not changed in this audit. Full all-writer coordination, complete input exclusion, live auto-advance and two-computer gameplay are outside this single-save candidate.

## Executed checks and retained failure

- `a_save_next_audit_runs/20261009-221620-345586/result.json`: PASS, SHA `41a40532cdf67ecfc61ff187867e09a30174a153278b1fbc06d1f900edceab0a`.
- `a_save_next_audit_test_runs/20261009-221706-411582/result.json`: 6/6 PASS, SHA `116d78079d9e1bc1c14c84101a7118e4369a3351803d6df22f7e8abb89eb92d9`. Real private build audit plus owned-file exact identity, changed/missing/duplicate artifact and relative-path rejection. No native load was performed.
- Initial checker run `221559-723898` failed with `KeyError('passed')`: the old publisher case rows use `owned_child_exited`, not a per-case `passed` field. Only the new checker was corrected; the immutable passing publisher result and all prior failures remain intact. This was not a production runtime failure.

Final checker source SHA `a046b04caa62daf6179e6da69d8d0fcdf980f3d490023cb05eb46f9d43ca6411`; test source SHA `a155b81c9367284b58ab7f6b787ba4d2ce79dfd15741c3d78646ca6575955f12`. EOF and whitespace checks passed. No shared documentation or Git commit was changed by this subtask.
