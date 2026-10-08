# Faults under the actual automatic Root activation owner

## Result

`b_reload_activated_fault_runs/20261008-173634-582192/result.json`: **3/3 PASS on the first build/run**, 148 source hashes and private input hashes unchanged. Result SHA-256: `1ca45c17719d724b8d22b3b4fd05244d2ab3ba5da2cce9080cfd0cb031bfaa81`.

New files are only `b_reload_activated_fault_test.py`, `b_reload_activated_fault_fixture.inc` and this handoff. They reuse the frozen activation/nested production implementations without changes, and compile the three activation C++ units in production mode. There are no new production permits or relaxed identity/thread checks.

## Executed paths

The three isolated cases derive their fixture from `b_reload_activated_queue_test.py`, but stop after one generic task. Original parent `509FE0` assigns the task; accepted actual `50B598` registers it; the original initial wait permits one cold worker publication; original `83A930` enters original `834D10` through the activation PE wrapper. The actual IAT task source begins Root observation. The business callback then arms the real nested input observer and executes the hardware prefetch site. No fixture Root Begin, fabricated Capture, direct report mutation or invented task ticket is used.

- **activated-fault-observer:** the pending observer raises `0xE014CF13` inside the real hardware event path. The frozen observer boundary catches it and records `Error::Observer`; child state restores cleanly. Original business returns normally and Root records all three entry/return/done events. The aggregate activation owner correctly remains clean: a contained observer error is not a hardware ownership failure. The diagnostic observer never grants queue authority.
- **activated-fault-business-seh:** after the actual child capture, business raises `0xE014CF11`. Child FINALLY restores its lease, then the exception crosses the native thunk/runner and activation PE FINALLY. Root records only entry, abandons its immutable Provider scope, and restores its hardware state. The outer fixture catches the same exception after these native cleanup layers, then exits the worker. Task abnormal is retained; aggregate owner error remains None because cleanup succeeded. This does not mislabel the original task as normally returned.
- **activated-fault-foreign-dr:** an owned helper suspends the actual worker and uses real Set/GetThreadContext to install another execute breakpoint in its free DR2. Business raises the same SEH exception. Child FINALLY refuses the changed layout (`RestoreConflict`, restored=0, uncertain=1); a second child scope on that same thread is refused before touching hardware. Root FINALLY retains the unresolved child lease and reports `Conflict`, restored=0, uncertain=1. The automatic activation owner receives `Error::Ports` and uncertain=1. A final OS-context read outside both native FINALLY layers confirms the foreign register values were preserved. They are never cleared to manufacture recovery; the owned worker exits and the process terminates.

All three cases have one initial-wait proof, one task, one actual outer owner claim, one IAT start and one cleanup, with no duplicate task/claim during error handling. Stop is checked not to rewrite the retained error and uncertainty receipts.

## Exact limits

These are **isolated automatically activated fault cases**, not full queue runs. No Load/Title chain or yield/resume runs in this new suite; those retain their separate frozen proofs. The result flags explicitly set full-queue composition, queue finalization, Load nesting and yield execution false for this suite.

After the original exception has crossed both native FINALLY layers, the **owned outer except** sets worker+78 and manager+30 and signals the completion event solely to release the fixture parent. These writes are explicit fixture teardown, not normal task completion, a synthesized Provider receipt, a tested fresh-task scheduling refusal, or evidence that production exception wake-up has been implemented.

No second task is submitted after the failure. `further_task_attempted=false` is explicit in every record. The conflict case proves same-thread **child observer** retry rejection before worker exit; it does not claim a full later parent-task scheduling rejection or a recovered pool. A future installer/controller must consume child/aggregate failure states appropriately. In particular observer-only failure stays in the child receipt; it is not automatically converted into an aggregate Root hardware failure.

The foreign owner is simulated by an owned helper performing real hardware-context mutation, not another external debugger or live process. Constructor/pool/callable storage/business remain explicit fixture doubles. Activation still requires the first native cold wait, and does not support an already-running unwrapped pool. No game, Steam, UI or current saves are accessed; this is not evidence of live installation or remote room readiness.

## Reproduction

From the repository root:

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<immutable private archive directory>'
py -3 work/mod_research/b_reload_activated_fault_test.py
```

The structured result includes all source/private input hashes, the executable hash, production object hashes, and each isolated receipt. Standard output and the generated owned fixture are preserved beside it. There were no failed intermediate builds or runs for this successor.
