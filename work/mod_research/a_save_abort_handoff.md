# A failed-save retirement

This is an explicit successor for the first controlled Save that reaches Driver `Uncertain/error54` after native finalization but fails content verification. It never converts that failure to Complete, supplies an artifact, clears a claim, clears the report pin/revocation, or permits another request. It is not a repair API for the old loaded module.

## Composition

- `a_save_abort_owner.cpp` replaces `a_save_covered_owner.cpp`. Apart from the local retirement helper/receipt registration, the covered User and all existing success validation paths remain unchanged.
- `a_save_abort_host.cpp` replaces `a_save_dispatch_host.cpp`. Only its stopped-boundary cleanup adds the narrowly authenticated retirement. The original Host thread releases its producer SRW lock after a fresh quiet snapshot confirms the save lane retired. The mailbox remains Unknown.
- `a_save_abort_runtime_exports.cpp` replaces `a_save_runtime_exports.cpp`; `a_save_abort_runtime_build.py` builds those implementations into the real Runtime DLL. The existing Snapshot wire layout and Driver status remain unchanged. `restoreReady` additionally requires an actual matching retired receipt for error54.
- `a_save_abort_publish.cpp` replaces the external publisher. It locates `ASaveAbortReceipt` through the fixed target DLL's PE export directory, checks the exact error/generation/host thread/base and stable sequence, and repeats that check while holding the debugger event. All previous live bridge-count, HostCache, process/module/source identity and restoration checks remain. Receipt absence, non-retirement or disagreement cannot authorize restoration.

Exactly one implementation of each component is linked. Objects/modules remain retained. This does not authorize unloading or running remote export calls while target threads are debugger-suspended.

## Retirement evidence

The local entry must run inside the actual ParentAdapter control boundary on the Controller's existing host thread, with the matching real Parent bridge claim. It requires the same consumed checkpoint/report/Driver generation; stopped and initialized Owner; Driver Uncertain/error54; one bind and one queue; phase mask31; worker started and joined; native success and finalizer returned; no successful verification/return receipt/completed request; balanced Driver entries/exits, zero abnormal/active scopes, no covered call and no queued/active reward work. Owned source and User/Save bridge activity are checked.

At that boundary it rereads the native five-state stack, all five original state identities, empty command queue, current state zero and all five state task pointers at +0x50 zero. Root/world identities and fresh sampler binding must still match. It deliberately never dereferences the departed Save pointer, which may have been freed. The native worker/finalizer evidence comes from the unchanged Driver, not caller-provided booleans. Error54 alone is insufficient.

Only `saveLane` is retired and the one-way receipt published. Original Owner error, Driver status/error, report cursor/tree rejection, sticky revocation, pinned generation and consumed once/reservation remain. This is failure cleanup, not room Ready or full-player-input restoration. The external publisher must still independently verify all bridges/cache and stopped state before restoring source bytes.

The current policy is intentionally limited to the first controlled request (`completed_requests==0`). Other errors, partial Save phases, abnormal callbacks, source/world changes or incomplete tasks retain the lease. It is not a general cancellation engine. The cooperative producer lock still is not proof that every game writer participates.

## Executed tests

All runs are outside the repository; no game, Steam, UI or current saves were accessed.

- Actual Owner/Controller/Driver/Host and named-pipe composition: `a_save_abort_runs/20261009-135855-524527/result.json`, SHA256 `5151ca8fdc147a53b2ce2ef71ce1e96ee2f671497c4dcb7dcdb67af6a0c5eef3`, 2/2 PASS. Normal still Copy/releases once. Cursor drift reaches the real Driver error54. An outstanding state task rejects retirement in the actual Parent boundary; wrong TID and a direct call outside that boundary reject it. After the owned task pointer is cleared, the next actual Parent boundary retires and only the original Host thread releases. Error54, revocation and Unknown remain, with zero Copy.
- Production Runtime and existing typed ABI: `a_save_abort_runtime_runs/20261009-134925-611666/result.json`, SHA256 `3dbdaf63b2d711302ce66502d660415972db60e00a4d2c265f821e84e97d36cf`, PASS. All 86 source, 32 production binary/object and five generated pins were independently rechecked. This is a production build plus owned ABI execution, not game Runtime execution.
- Actual debugger publication transactions in owned processes: `a_save_abort_publish_runs/20261009-135151-357545/result.json`, SHA256 `9d278c350607379b5e68113ea5181a0d0e539dfa29a10cfb04e9824fbaa4c66f`, 6/6 PASS. Aborted receipt permits restore; unretired receipt, mismatched generation and held Host lease reject. Original Complete and unbound Cancelled restore still pass. All 18 transitive source, eight binary and generated-build pins were rechecked. The owned publication target supplies diagnostic receipts; actual receipt production is tested separately by the Owner composition.

The first composition compile `20261009-134804-209042` failed under /WX because a fixture thread variable shadowed another local. It is retained; only the fixture name was corrected. Earlier publication runs remain intact. Owner wrong-generation, worker-join-missing and abnormal-report predicates were reviewed statically, not dynamically fabricated: those latter conditions normally cause an earlier Driver error rather than this precise error54. The active-state-task, wrong-thread and wrong-boundary refusals were exercised.

Native scheduler, Save business and serializer bodies remain clearly identified substitutes in the composition. These tests do not establish every producer's participation or certify a live game's all-writer drain. A fresh-process controlled real failure/success and full restore are still required. The prior stopped process cannot acquire this new receipt retroactively.


## Final combined successor for the next fresh-process trial

Use `a_save_abort_pending_owner.cpp`, not the earlier abort-only Owner, in the next Runtime composition. It merges the independently verified pending five-state User path from `a_save_pending_user_owner.cpp` (SHA256 `87300130d8dc4ce02e70b4b8959e5cd947af89c440f25d1586b969b5ddd29af2`) with this abort cleanup. The combined Owner SHA256 is `1bbf1eb7c1437253becd960e322c523abc7ed5d6f1744f98852f9961f9e97762`. Removing exactly the added includes, abort namespace/receipt, Impl::abortDrain and initialization registration reproduces the frozen pending Owner byte-for-byte after normal newline decoding; no pending/covered User routing was edited. The merge diff is preserved beside the final production result. An initial merge-anchor assertion stopped before writing because the pending successor adds a namespace alias; the anchor was corrected without changing either predecessor.

`py -3 work/mod_research/a_save_abort_pending_test.py` exercises the new combination. Final run `a_save_abort_pending_runs/20261009-135855-553382/result.json` has SHA256 `e5c007030db82f0af4d52fa32beeca9220ceef8ce6ef3a7c9ee3e0e73fa36ca3`, 2/2 PASS, with 84 source/42 binary/six generated-file pins independently rechecked. Both normal and cursor-failure flows include queued Game, pending User, covered User and normal Save dispatch. This extends the abort composition with the additional pending User window; the standalone pending Owner's six-case negative suite remains separate evidence rather than being relabeled as six combined cases.

`py -3 work/mod_research/a_save_abort_pending_runtime_build.py` is the final production build entry. Run `a_save_abort_pending_runtime_runs/20261009-135510-973447/result.json` has SHA256 `85a2bf2d9c176cf8917ae757d492cb19d64e2ea577003dbf58ac5e1c64148974`; all 87 production-source, 32 binary/object and five generated pins match. The resulting DLL is `abi/production/build/a_save_local_runtime.dll`, SHA256 `8125ec17de92bd46f9fcda780008990b5c8c1b9456630f895de8bb39886054cb`. The existing typed ABI test also passed. Pair this with the new publisher from the six-case publication run above; the frozen publisher intentionally rejects Uncertain and cannot consume the new retirement receipt. All owned tests completed their client/server/helper processes; none were left pending.

No new live trial is performed here. The remaining gate is a fresh game's real save/verification and, for an aborted path, real native drain plus external restoration. The DLL keeps the original failure visible even when its exact cleanup receipt allows source restoration.

Commit-time whitespace validation removed extra EOF blank lines from only the two new composition test scripts; both two-case suites were rerun with the final source pins above. Their earlier passing runs remain retained. Neither script is a production Runtime input, so the production DLL and ABI identities above remain unchanged.
