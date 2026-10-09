# Owned Save coverage in the User callback

`a_save_covered_owner.cpp` is a complete same-ABI implementation successor to frozen `planning_checkpoint_save_owner.cpp`. Link exactly one Owner implementation. It retains the original checkpoint/lifecycle includes, native Driver, storage verifier, planning report guard and bridge bank. Neither file was edited in place.

The narrow change addresses a real scheduler shape omitted by the earlier fixture: while this Owner's Save is the sixth/top state, the scheduler can still invoke the underlying User callback. Its original top-state test returns false and the original User returns before the upstream gameplay call. That covered callback is not a five-state planning observation.

## Exact accepted path

Initialization pins the first five state identities from the same immutable Owner input source. The new selector marks `reserved_58=6` only after checking all of the following:

- Actual Driver status Queued, no Driver error, exactly one bind/queue, nonzero generation equal to the report sidecar's pinned generation, and nonzero Driver save_state.
- The actual manager has six states, zero queued commands, current state equal to this User, the same first five identities, and this Driver's save_state exactly at the sixth/top position. It is a `CSaveState` with the correct vtable/name and phase 0–4. User phase stays 2.
- This exact callback has User slot, actual thread, nonzero call ID, authenticated native return address and User argument; there is one active Owner scope and no inherited claimed User owner at selection.
- Existing slot/source checks pass. `rp::fields` still checks root/world/User identity, report flag/count/tree and pinned report cursor; sticky revocation is never cleared. State shape and report fields are reread.

The selector only classifies; it does not invent a TLS claim. BEFORE still calls the real Driver.Before, then requires the actual UserOwner TLS token/generation/call/TID/depth and the same Save shape. The native original runs once. AFTER requires its actual RAX to be zero and repeats the owned-source/Save/report checks; then real Driver.After and FINALLY run normally. Separate read-only counters record selected, claimed, returned, FINALLY and rejected observations. They do not increment Driver completion or fabricate receipt fields.

Every nonmatching/unknown shape falls back to the frozen strict path. Ordinary five-state User callbacks still call the unchanged `rp::observe`. Save callbacks retain their original field checks. Unknown sixth states, another Save, a nonempty command queue, cursor/tree drift, wrong source or failed claim do not receive a covered exemption. Existing original-forwarding behavior on observer failure is preserved; such failures stop admission and cannot produce a successful save artifact.

## Production source identity

The production branch validates the original User prefix through the existing normalized-slot check, plus these additional archived sources:

- IsTop `[0x509640,0x509675)` SHA-256 `63b7bf401981a4cd0ff3976f75fdcc761e8ea8ee3df6b697ab5da8e1dd0e4116`.
- Manager singleton `[0xF690,0xF711)` SHA-256 `c04dff10f16d1bf930f6b4ecf5e7bec60911e83f11d81613042f5372adfe44fe`.
- Native User early-return epilogue at `0x3FA0AE`: six bytes `48 83 c4 40 5e c3`.

The IsTop function checks the fixed singleton's last stack entry. The singleton returns the existing global manager when initialized; its CRT guard at `base+0x19E7360` must be neither 0 nor -1, excluding cold construction/in-progress initialization. No native test or singleton call is injected. These identities were independently checked against the private archived image SHA `5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`. Fixture builds explicitly skip these native-source checks; that fact is not production coverage.

## Verification and integration boundary

The initial production /W4 /WX compile passed in `a_save_covered_owner_build_runs/20261009-125220-374733`; its source/OBJ pins describe the intermediate version before the added singleton/return checks. An attempted final source patch met a transient file write failure while another agent compiled the file; it made no change and was subsequently applied and hash-checked. No source lock was bypassed.

Final source identities:

- CPP `38882de5bdab99b07e3adce5baa9ef4aa2b57624adc82b32b17a2f8cfd3e69e0`.
- Header `94279e7c937ebbae18a2d42d43891613990b915c8e7a1042cbdf746d10efa107`.

The root agent owns final production Runtime building; the parallel Gate agent owns the combined transition fixture and its final run. That combination must include a normal queued-Game/covered-User/Save/returned-User sequence and the negative case of this exact Save with a changed report cursor/tree. The current file does not substitute an intermediate compile or fixture pass for those final records. The final diff is preserved beside the initial compile as `final-source.diff`; changes are confined to the new diagnostic namespace, pinned covered-source/state helper and the selector/Before/After/FINALLY routing.

No game/Steam/current save/UI was touched by this implementation. There was no attempt to repair the stopped live process, reset a consumed generation, retry the failed save or relax its terminal verification. First-Gate-failure diagnosis and cleanup remain separate from this Owner fix. A fresh-process real save and verified restoration are still required after the combined successor is built and reviewed.


## Final combined records

The final production Runtime and owned-process ABI build passed in `a_save_covered_runtime_runs/20261009-125624-320549/result.json` (SHA-256 `d090c9212398430101f80241cecbdc0775e6eb11c039ca806dfd6cef1effe00c`). This builds the final Owner and queued-Save Gate successors without their fixture source exemptions; it does not execute them in the game.

The actual Owner/Controller/pipe combination passed all five cases in `a_save_covered_integration_runs/20261009-125734-923360/result.json` (SHA-256 `32bdc51feaf2b8e14692bc2e66815fd6a3ca3f959d7f4b42cba91ff7a7602dd2`). Independent review verified all 81 source, 42 binary and six generated-file hashes against disk, plus the two archived native source hashes and the original zero-return branch bytes. The normal case includes the five-state own-Save queue window, five interleaved covered User calls and actual Save callbacks, final User, verified artifact Copy and writer-lease release. Covered selection, real claim, zero-result AFTER and FINALLY counters each equal five. The dedicated owned ASM returns zero on the covered branch; the earlier constant-return model failure was retained and corrected in the fixture, not accommodated by weakening production validation.

Foreign queue type, multiple queued items and mismatched generation fail at Gate layout, deliver no artifact and only release after their already-bound native work drains. The cursor-drift case uses this exact owned sixth Save and changes the pinned report cursor before covered User: report revocation remains terminal, Driver becomes Uncertain/error 54, no artifact is copied and the writer lease remains retained. This is a cursor negative, not an additional tree-mutation test; the existing unchanged field predicate continues checking both. Business/serializer and native scheduler bodies remain owned-process substitutes, so these records establish the corrected narrow composition rather than a successful real-game save.

The queued-Save Gate still runs the original Inspector first and supplements only its `UnownedStateQueue` result. That result occurs before the Inspector's final quiescent-only cache-status check; this successor is a distinct owned-Save queue permission, not a claim that the queue is quiescent.
