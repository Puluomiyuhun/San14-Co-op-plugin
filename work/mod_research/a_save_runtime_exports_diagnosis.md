# First real A Runtime save: terminal guard diagnosis

This is a separate diagnostic handoff. It does not alter the frozen Runtime, exports, Owner, Gate or Driver, and it does not authorize retry or removal of retained hooks.

## Actual result and known failure chain

The parent agent ran the current controlled single-save path. Private record: `a_save_runtime_live_runs/20261009-123703-876595`. Native Save created the independently named `mp83d7e462.s14`. The original files were unchanged and this was the only new file, but the artifact was **not** accepted or delivered. The final result remains `INCOMPLETE_RETAIN_EVIDENCE`, not a completed synchronized save.

The native Driver observed one bind and one queue, all five phase bits (`31`), worker join, native Save return and return to five planning states. It subsequently entered `Uncertain` (`saveStatus=7`) with error `54`; file verification stayed false. Owner retained saveLane, and the Host retained its producer lease. Stop was honored for admission but could not satisfy the existing successful-completion drain rule. All sampled bridge active counts were zero; this alone does not permit unlocking the retained lease or claiming clean restoration.

The root agent then read terminal data without invoking another target function. The bounded offline layout work below enabled these reads:

- `terminal-gate-evidence.json`: upstream Gate first error is **Input=6**, not Scope=7. UI/panel suppression counters both reached 15; User-tail suppression reached 1. This proves the gate worked earlier and later rejected a source/input check; it does not identify the exact failed predicate.
- `terminal-report-evidence.json`: report sidecar is pinned/revoked, with `afterRejected=25`, `storageRejected=1`, `entrySuppressed=0`, last boundary Storage and last decision Drift. At the terminal read, root/world/user identity, report cursor (43), empty report tree/count and User report flag all matched. This is a sticky earlier rejection, not evidence that those fields still differ. The last Storage/Drift record overwrites the earlier rejected boundary/decision.
- `terminal-file-evidence.json`: Verify stopped at **`context`**, with exception/OS errors zero and native exists/size/read calls all zero. Its local/native hashes are zero because Verify had not reached its own hash stage. `copyFresh` had already performed its separate initial local open/read/hash before invoking Verify. Error 54 is therefore **not** evidence of mismatched Steam bytes, slow file flushing, or a failed Steam FileRead.
- Storage Gate reports Invalidated/ValidationFailed, five validation attempts (four success, one rejection), and binding error **Owner=4**, no exception or OS error. The report sidecar's sticky revocation is sufficient for `Owner::Impl::storageOwner` to reject; Runtime's own storageOwner does not reject merely because Runtime is stopped.

The supported sequence is: an upstream Gate Input rejection stopped Owner; subsequent report observations were rejected and left sticky revocation; on returning to planning, `copyFresh`'s first Verify context validation reached that revoked Owner guard and failed. The early Stop with Owner error zero, followed by Owner Input error during the Save phases, supports this ordering. `ServerStatus` and cleanup snapshots alone do not pin the exact first Game call.

## What is still not proved

Do not call the Gate's five-stack User-tail check the confirmed first cause: its direct aggregate failure is Scope=7, whereas the actual Gate recorded Input=6. The native covered User also branches away before the patched User-tail call when it is not top state. The concrete first rejection could lie in the Game BEFORE source/caller/claim/layout condition or its layout inputs.

The fresh Sampler explicitly accepts counts 5 and 6; it is not a blanket five-stack-only sampler. Game layout accepts a six-state Save shape after its initial validated planning frame. Its five-state branch, however, runs the planning Inspector; a queued Save transition before the sixth state is pushed may be rejected there. This queue-transition explanation is a candidate requiring a captured first-failure predicate, not a conclusion from terminal counters.

There is also a separate demonstrated coverage gap: the existing single-period fixture dispatches Save phases and then a returned five-stack User. It omits ordinary Game/covered-User callbacks interleaved across every active Save frame. Owner's report observer requires a five-stack planning state, including in User AFTER, so treating covered six-stack User callbacks as fresh planning observations can revoke a valid in-progress Save. `entrySuppressed=0` and the earlier Gate stop mean this second bug must not be presented as the proven initial stop in this run.

## Targeted successor work

1. Preserve this run and wait for a confirmed normal game exit before another attempt. No once-claim reset, duplicate Submit, injected cleanup, guard patch or native read retry is justified by these terminal records.
2. Add a narrow first-failure diagnostic in a **new** Gate/Owner successor: latch the exact first predicate, caller/TID/source stage, manager count/queue count/current/top, first five state identities and owned Save identity/phase. Do not overwrite that first record with later Storage failures. This directly fills the missing evidence instead of adding a generic telemetry API.
3. Model the real sequence in one existing composition: queued-but-not-pushed Save, interleaved Game and covered User during all Save phases, then returned planning User. A covered User must retain exact source/owned-Save checks and original early return; it must not be labeled a planning boundary or globally exempted from report checks. Keep the early report guard's normal five-stack contract.
4. Resolve the actual Gate transition check, then rerun one new-process, independently named real save. The completed result still needs two native reads, byte/hash agreement, packet delivery and verified source cleanup. Do not change error54 into success or allow the Host to release solely because native Save wrote a file.

## Offline layout evidence and RPM chain

`a_save_runtime_exports_layout.py` never opens a process. It compiles the exact production source shapes with the same MSVC target/options and emits class layouts. A map-only re-link uses the already pinned library/objects. Its `.text`, `.data`, `.pdata`, `_RDATA`, `.reloc` sections and their RVAs exactly match the original DLL. `.rdata` contains differing link metadata, so it is not claimed byte-identical. The static symbol mapping is supported by identical code/data addresses; the root agent also independently found the runtime pointer via the actual export's RIP-relative instruction.

Final offline record: `a_save_runtime_layout_runs/20261009-124604-851913/result.json`, SHA-256 `6548c4952598d6923df7dbcf5a0dbf0c93d3733331968a68573a375c7f0a8c2a`. Earlier incremental evidence is retained in `124152-017673` and was used for the actual read-only terminal captures.

These offsets apply only to the exact DLL SHA `dd92aa6958f135ca480f6db1b1b98c505c8db29a17a9238624586a62a417658b`, with its matching original production source pins. They are not portable game addresses:

- DLL RVA `0x5de48` holds the Runtime pointer. Runtime `+12440` holds User Owner; Owner's first pointer is its Impl. Impl `+9080` is Driver, whose first pointer is Driver::Impl. Driver `+6888` is `fileEvidence[0]`, stride 152; count is `+2616`, report `+2472`, target UTF-16 buffer `+2696`.
- Runtime `+12448` holds upstream Gate Owner; its first pointer is Impl. Impl report begins `+88`: error `+0`, active `+24`, gameCalls `+32`, UI suppressed/forwarded `+40/+48`, panel `+64/+72`, User-tail `+80/+88`.
- User Owner Impl's serialized storage Gate begins `+9088`; its report begins another `+7168` (total `+16256`). Report state/error are `+0/+4`, validation attempts/success/reject `+16/+20/+24`, active `+36`, last binding report `+48`. Binding error/exception/OS are `+0/+4/+8` within that nested report.
- DLL RVA `0x60510` holds the 248-byte report sidecar. Base/root/world/user are offsets `136/144/152/160`, pinned cursor u16 `168`, generation `176`, claimed/ready/pinned/revoked/boundary/decision u32 `184/188/192/196/200/204`; rejection counters u64 `208/216/224/232/240`.

The parent agent owns actual RPM, user instructions and process cleanup. This subtask only inspected archived files and produced compiler/map diagnostics; it did not touch game/Steam/UI/current saves or invoke a target DLL. At handoff, normal game exit had been requested but was not yet independently confirmed by this subtask. Retained hooks and the unresolved lease must not be described as cleanly removed.
