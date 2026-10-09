# A Runtime controlled second-save successor

This successor executes two authenticated pipe Save/Copy transactions through the same real Runtime, Owner, Gate, Host, mailbox and physical bridges. It does not yet drive the game's time simulation or establish a trustworthy B-loaded acknowledgement. Do not advertise it as completed cross-period multiplayer.

## Concrete path

`a_save_repeat_runtime.h/.cpp` replaces the original Runtime TU; `a_save_repeat_parent.cpp` replaces the Parent TU while retaining its physical bridge counters and Host-cache publication. `a_save_repeat_runtime_build.py` links these with the abort/pending Owner, covered Gate, abort Host, and the root agent's additive typed exports. No predecessor is changed.

`RequestNext` copies one request for generation 2 and precisely the next ten-day date. A duplicate is rejected. At the original authenticated Parent BEFORE and original Host TID, Runtime requires mailbox generation 1 Delivered and original Host Complete, then obtains the real first artifact again from Owner and compares its verified hash with the request. It acquires the local producer lease and starts an actual Controller observation. Original Game/User callbacks run. At Parent AFTER, Controller EndObservation and actual period-owner Retire create a historical receipt. A later Parent BEFORE only accepts the unchanged old identity as waiting or the exact next identity as eligible; world/root/force/date drift fails closed. Actual Rebind, retained second Controller Initialize, and original Host BindPeriod complete before the active identity changes to generation 2. No bridge or Owner history is reset.

The normal diagnostic fixture supplies the next date by changing its own allocated world; Runtime itself never writes game dates. Retire leaves the Ready fence in force, so this code cannot rely on a player manually advancing the real game while waiting. A separately authenticated native simulation/advance path and real remote acknowledgement are the remaining integration requirements. `bLoadedProven`, `simulationEnabled`, `allWritersProven`, and production permit remain false.

## Stop and incomplete Parent frame

Repeat entry and exit are independent of `Host.BeforeFrame()` acceptance. Stop on another thread cannot release the repeated observation's SRW lease. Parent AFTER still closes it when original Host.BeforeFrame returns false. A missing AFTER invokes repeat cancellation from the real bridge FINALLY. All release happens on the established Host TID, and the copied request/error/history remain terminal rather than being reset.

Repeat Snapshot exposes lease/frame/drainPending. The additive exports include these in restoreReady. The explicit publisher successor requires restoreReady exactly 1 for every terminal kind. Clearing repeat's own lease does not imply that the frozen original Host frame has closed: the missing-AFTER test retains original Host.frame=1, which continues to prevent safe restoration. No forced clear or clean restoration is claimed.

## Final targeted execution

Private run: `a_save_repeat_runs/20261009-143723-860155/result.json`

SHA-256: `fa4a0337df682421b3b07f3f0ec92a5e04d8ad559734ec8d5398ffda57c62bb6`.

All three cases passed; independently rehashed 95 source entries, 45 binary artifacts and 6 generated files match. Three frozen private inputs are additionally pinned by the runner.

- `normal`: two actual Controller/Owner/Host/pipe submissions, two verified Copy packets decoded by the production Python packet decoder, same retained mailbox and physical counters, one actual Retire receipt, second actual Rebind. Both packets contain the diagnostic payload for their respective date.
- `stop-gap`: after repeat BeginObservation succeeds and before Host.BeforeFrame, a distinct owned thread calls Runtime.Stop. The lease is demonstrably still held on return from that thread. Host.BeforeFrame refuses; actual Parent AFTER nevertheless drains repeat on the original TID. Only first Save/Copy exists.
- `missing-after`: a fixture-only hook deliberately omits the Adapter AFTER handler after original parent work returns. Real bridge FINALLY cancels repeat; original Host.frame remains outstanding and no second Save or restore permission is fabricated. This verifies a missing handler, not native SEH unwinding.

`A_SAVE_REPEAT_FIXTURE` supplies only owned addresses and identity for the fixture Runtime. `A_SAVE_REPEAT_PARENT_FAULT_FIXTURE` adds two fixed local diagnostic hooks and is absent from production compilation. Save serialization, native scheduler body, and date change are diagnostic business substitutes. Actual Controller, Owner, Driver, report guards, real OS pipe, mailbox, physical bridges, source scopes, Retire/Rebind and fixed-thread lease handling execute. The local SRW only covers cooperating fixture writers; it proves neither all real game writers nor a production lock order.

## Retained unsuccessful runs

All private failure directories remain intact. 142618 failed a fixture text anchor; 142638 reached the second period but inherited a first-period-only pending counter assertion; 142806 completed two saves but its Python aggregate still required one decoded packet. 143522 ran before the final fault generator was installed. 143609 passed normal and Stop-gap; its owned machine-code parent stub had no unwind metadata, so the attempted SEH fault exited with 0xE0140010. The final test uses the explicit missing-handler injection above and does not relabel that SEH attempt as a pass.

Production source freeze: Runtime SHA-256 `c0057159696e75ed2f5a0a6bafbc29121b4536b349cc413aac46001afd1eec19`; Parent SHA-256 `96f10f30eeb682179a3a9809a478d0d5fc67a2671f7bb1ce3784dffdeaa9fcdf`. Root performs the final production DLL/typed-ABI rebuild after this freeze and records those result identities in the main handoff. Publisher is independently owned and verified by the sibling agent. No game, Steam, UI or current save access occurred in these tests.

Final production DLL build: `a_save_repeat_runtime_runs/20261009-143818-417144/result.json` PASS. Additive real-DLL operations 9/10 plus schema/contract ABI: `a_save_repeat_exports_runs/20261009-143906-534043/result.json` PASS (run independently by root after source freeze).
