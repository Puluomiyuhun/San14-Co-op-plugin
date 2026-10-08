# A Save: copied mailbox and bounded held-IPC execution ports

2026-10-09. **7/7 owned-process C++ cases PASS.** No game, Steam, UI,
current saves, archives, process discovery or network was accessed. Frozen
predecessors are unchanged. No patch, live helper or user operation remains.

## Implemented

`a_save_dispatch_mailbox.{h,cpp}` retains two immutable request identities and
copied completion artifacts behind a Windows SRW lock. Initialization records
the current trusted host thread. Only that thread may Take, Accept, Complete or
mark an outcome Unknown. Take claims a request once and cannot be repeated.

The request, binding, completion request/report/hash and vector bytes are
copied; no pipe-owned buffer or output pointer is retained. Semantic request
comparison avoids C++ padding. Requests require increasing generation, a new
binding, the same native room ID/epoch, and a non-regressing period. A next
request requires the previous artifact to have been delivered. Records are
never recycled; capacity is two, matching the existing bounded drivers.

`Adapter::SubmitPort/CopyPort` have exactly the existing
`a_save_held_ipc::Config` execution-port types. Tests assign them to that Config
and call through its function pointers from real owned pipe-role threads.
Submit enqueues and waits on a Windows condition variable for at most its
configured 1–60000 ms. **Enqueued or claimed is not success.** Only a trusted
host's explicit Accept after its actual Submit succeeds permits the waiting
port to return true. A completed Save is a later, separately copied record.
Calling the blocking port on the host itself is refused before enqueue.

Timeout/Stop before Take records Cancelled. After Take or Accept it records
Unknown, permanently stops the mailbox and prevents replay. Late acceptance
or completion cannot resurrect that request. Stop wakes a blocked submitter.
Malformed completion identity also stops with Unknown. Copy delivers once;
copy allocation failure leaves the completed record available for retrieval,
which does not repeat a native Save. No host/native callback runs under the
mailbox lock.

## Exact integration status and remaining host work

The **Config execution ports were executed; the named-pipe Server itself was
not executed or modified**, and no real Controller, Root bridge, permit or
serializer is connected. The tests' host acceptance and artifact are explicitly
named business doubles; even their nonzero hash is diagnostic. The mailbox
checks copied identity and completion-report shape, not file SHA or world
consistency. Real artifacts must come from existing verified storage completion.

Existing `a_save_held_ipc::Server::process` returns Ok as soon as its submit port
returns true and immediately samples Owner state. Returning true at Enqueue
would therefore misrepresent admission. The bounded adapter instead waits
until host acceptance. It still cannot make the old Server's shutdown path
safe by itself: `Server::stop` calls Owner.Stop, with no mailbox notification.
Before installing these ports, a retained host coordinator must propagate
shutdown/disconnect to Adapter.Stop, preserve Owner/Controller lifetimes and
join the pipe thread only after its blocked Submit has been released. Internal
Server errors must also propagate, through an explicit successor Stop hook or
a coordinator observing its stopped diagnostics. This coordination is **not
yet implemented/tested as a full pipe transaction**. Timeout is the fallback,
not permission to continue native work after a disconnect.

The intended adapter sequence is:

1. Initialize the mailbox on the already-proved host control thread; retain
   it, its Adapter, all native owners and the completion storage until drained.
2. Pipe role posts through Config.submit and waits. It never calls Controller.
3. At a separately proved eligible parent boundary, the same host thread Takes
   the copied request, validates actual Room/planning/hold/writer evidence and
   invokes existing `planning_checkpoint_save::Submit`. On true, call Accept;
   on false or uncertain outcome, call Unknown/Stop. Do not replay.
4. At the real completion boundary call existing held Copy, then Complete with
   that actual artifact. Pipe Config.copy retrieves the retained independent
   copy. No new serializer invocation occurs from Copy.
5. Next-period authority remains with actual B-loaded acknowledgment and
   Session.Retire/PlanNext/Rebind. Delivered merely allows transport queuing;
   it neither supplies those receipts nor permits host execution or Ready.

`WireSave.room_epoch` is the fixed native room epoch in the current
`a_save_simulation_ipc` chain. It is **not** the 16-byte changing network
timelineEpoch carried by ScopeWire. Tests follow its actual two-period shape:
generation/period 1→2, checkpoint day 11→21, fixed native epoch and different
binding. Native epoch changes, room changes and generation/period rollback
are refused. The mailbox does not infer timeline scope from these few fields.

Take remains an explicit trusted API, not proof of a safe native boundary.
Use the parent audit's precise call/return source, stable host TID, drained
FINALLYs and unchanged planning state before consumption. Neither one parent
return nor this mailbox establishes full input/writer exclusion. A/B must
share a single owner of the native parent call site.

## Verification and retained evidence

```powershell
py -3 work/mod_research/a_save_dispatch_mailbox_test.py
```

The runner requires the existing Visual Studio C++ toolchain, builds its own
EXE and runs seven cases. No private archive is required. It pins all 19 source
and header dependencies, preserves build/test logs, checks the full expected
case count, and writes a FAIL result on build failure or child timeout.

- Two periods: actual Config function pointers, blocking until acceptance,
  copied request/artifact, one-shot claim/delivery, wrong-thread and wrong-token
  rejection, no pre-Accept completion, no next request before delivery, rollback
  and capacity refusal.
- Sixteen competing producers and consumers: exactly one acceptance and one
  delivery.
- Queued timeout, claimed timeout, explicit Stop waking the pipe, explicit
  unknown outcome, mismatched artifact: terminal records and no resubmission.

Final run: `a_save_dispatch_mailbox_runs/20261009-004507-355538/result.json`.
Result SHA256: `09d08713b4c58e81d2c6b692efa524db4ea5fdde12a2cc62cef2ba0a985502b0`.
EXE SHA256: `ca7040538ed96e305af631a4d6cbdebd8a4a6507184a48af7dacb66495cf7e2b`.

| Source | SHA256 |
| --- | --- |
| mailbox.cpp | `5f166ea812a51c414c45dabfdc998df91e069d4175f09f1b5383cdc428628347` |
| mailbox.h | `37d79aacb9cd0d7382282e6317afedc6c40dd8c934a21e94b296e815b1f0b97f` |
| mailbox_fixture.cpp | `9d32826a424fc6cd118e18c7c5796ca8d761202ef18f14e7c6c13664a2d52a5e` |
| mailbox_test.py | `21f05f255233e48b5adb5d2d3011a10f617f69869f7364dc4fd2c111d57dc6a1` |

Earlier runs remain: 004132 passed the initial seven cases; 004357 failed at
compile under /W4 /WX because a fixture variable shadowed a thread variable
(C4456); it ran zero cases and retains FAIL. The variable was renamed. 004421
passed updated period/delivery checks; 004507 additionally hardens the runner's
failure-summary and complete-case-count handling. No failed run was erased.
