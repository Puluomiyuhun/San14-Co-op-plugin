# A Save dispatch: actual User lifecycle through two queue cycles

2026-10-08. **3/3 bounded archive cases PASS.** This successor executes a
previously doubled part of the actual automatic Save route: User pause,
resume, exit-event and enter-event callbacks inside the same native queue
apply/pop execution. It does not implement a production dispatcher or new
Save permit. No game, Steam, current saves, UI, process discovery or network
was accessed. No active patch/debugger or pending user action was created.
Frozen predecessors, root documents and Git were not changed by this agent.

## Why this was the next useful step

The held-save IPC fixture still invokes the host port synchronously on its
owned test thread. Existing FreshSave already knows how to enqueue Save on
the **actual User callback's AFTER**, using the captured native caller, owner
claim and original return. A second arbitrary remote native invocation is
not the missing piece.

The candidate automatic path is `User -> Save`, with six stack entries. The
manual menu is `User -> Config -> Save`, with seven. The earlier six-state
queue regression doubled every User lifecycle callback; consequently it
proved stack preservation but not native input callback restoration. This
successor runs the actual four User callbacks and their input callable
containers rather than adding another boolean admission model.

## New executed findings

- Actual `2DF990` type0 push, queue event/apply, successful `465C10` pop and
  queue removal execute twice on the same existing User object. User is
  neither finalized nor destroyed. Save allocation/constructor and all
  non-User lifecycle callbacks remain the named predecessor doubles.
- Actual User pause `3F5920` calls actual `C020`: it clears input bit0 and
  clears all three callable owner slots at `+2B0/+2F0/+330`; it also writes
  updater `+28=1`. No callback contents are patched to simulate this result.
- Actual phase2 resume `3F5530` restores updater `+28=0`, rebinds the two
  native inline callables through `3DF8B0/3DF670`, their clone/move operations,
  `404AA0/327900/500320`, and executes native `8F50` to set input bit0 again.
  The `+330` callback retains the exact existing User pointer. Native resume
  also writes the modeled Game panel's secondary `+198=1` refresh field.
- The second pause actually runs the original inline callable destructors
  `4F9AF0/402F60` before clearing their owner pointers. Both periods return to
  the same phase2 User and again restore the two callback containers.
- The selected-object case reaches `3E8EF0` twice. That business remains an
  explicit double; this case locates a real conditional side-effect path,
  **not** proof that selected objects are safe for automatic Save. The idle
  case does not enter that business. Keep the current no-selection precheck.
- A phase5 negative control executes the same push/pop twice but remains
  phase5 and does not restore phase2 input callbacks/enable. Save completion
  does not repair an invalid starting phase. Never force phase2 after pop.

Each of the three cases contains two queue cycles. These are neither six
actual saved files nor six live tests. There is no serializer, Save worker,
real OS thread or original UI resource allocation in this new experiment.

## Doubles and precise limits

The harness loads only the frozen predecessor **class AST**, not its old
top-level runner or implicit archive-discovery imports. Queue/control-flow
instructions and actual User lifecycle/inline callable helpers execute in
Unicorn from one pinned archive. No generated machine-code profile is public.

Named doubles still cover Save construction, fresh owned graphics association,
allocator/temporary containers, other states' lifecycle, UI/cursor/scene
services, special mode absence, named Game lookup, selection validity and
clear business, cookie check, and camera scalar math. The actual camera
update takes its input bit1-clear branch; other camera branches are unproved.
The successful-save result is explicitly synthetic. Date, RNG, full world
purity, background writer exclusion and real Save/file success are not proved.
The source's short name `input` denotes only the subsystem returned by
`F720`, whose callback/bit changes are exercised here. It does not establish
that this is the complete keyboard/mouse/gamepad input system, nor that bit0
alone blocks all player commands. The names `updater` and `camera` similarly
describe the tested roles, not an independently proved complete class type.

The inherited instruction runner has an instruction limit and accepts only
addresses inside the fixed archive or explicit owned stubs. This is a bounded
branch experiment, not an exhaustive executable verifier or callgraph closure.
No compiled EXE/DLL is produced, so there is no new binary hash to report.

## Concrete dispatch integration finding

Source review, separate from the three archive cases:

1. `planning_input_interlock::Controller::Initialize` pins its **host control
   thread**. Request/BeginObservation/EndObservation and planning Save admission
   must use that thread. This does not imply all native User tasks use that TID.
2. Controller `clean()` requires zero active Owner/Gate scopes and bridge calls.
   Calling Controller admission directly inside User bridge BEFORE/AFTER would
   therefore fail that requirement; weakening it would discard its boundary.
3. FreshSave `Submit` only arms a request. Its subsequent actual User BEFORE
   claims the native call; actual User AFTER checks the preserved planning
   state and calls native binder/queue. No need to invent a fixed worker TID or
   invoke Save serialization from the pipe service.
4. The smallest coherent next integration is a retained mailbox serviced by
   a **proven Root parent boundary** outside all active child tasks, on one
   host thread: request hold, BeginObservation, allow the covered native frame,
   EndObservation after all required FINALLYs, then admit Save. The original
   following User task performs the actual bind/queue. Results are asynchronous
   and correlated to request/generation; a pipe thread never supplies addresses
   or synthesizes callbacks to make progress.
   **The real Root parent thread has not been identified or proved stable.**
   Initialize, Request, BeginObservation, EndObservation and Submit must retain
   one control TID with the present Controller. A proposed cross-frame bracket
   must therefore prove both ends occur on that same TID; if the actual parent
   migrates or remains yielded, reject the bracket rather than changing its
   recorded thread. Worker callback TIDs alone do not establish a host thread.
5. This boundary must handle Root yield/resume, pending state transitions,
   ownership drift and Stop. Existing completed-task fragments alone do not
   prove every frame is safe. The full writer permission is still separate:
   native pause is not an army worker join, and this test proves no producer
   closure. Do not convert one idle real Save or these three cases into permit.

The mailbox/Root boundary above is a design conclusion, **not implemented or
approved for live use in this successor**. Existing Owner/Controller invariants
stay intact. B continuous-load work can proceed independently using legitimate
files; there is no reason to repeat the prior low-information idle Save test.

Concrete next source entry points: `a_save_held_ipc::Config::submit/copy` are
the cross-thread ports; `planning_input_interlock::Controller` owns the
same-thread bracket; `planning_checkpoint_save::Submit` is admission;
`checkpoint_fresh_save::Driver::Before/After/Finally` already performs native
User dispatch/Save tracking. Add an explicit new `a_save_dispatch_mailbox.*`
successor for copied request/completion records, and a separately evidenced
`a_save_dispatch_root.*` host adapter. Do not call Controller from inside its
owned User bridge or overwrite the frozen synchronous fixture to imply the
host exists. First collect/execute the precise parent entry/exit/yield paths
and their thread identity; only then install a real adapter. A wrong-thread
or yielded callback must leave a queued request unexecuted or fail it, never
retry a binder that may already have committed.

## Reproduce and evidence

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<existing local research archive directory>'
py -3 work/mod_research/a_save_dispatch_test.py
```

Only `game-runtime-image.bin` and `python_deps` from that explicit private
directory are read. Missing dependencies/input fail rather than skipping.

Final private run: `a_save_dispatch_runs/20261008-235330-702355/result.json`.
Result SHA256: `c587bf900cc57e0dc05e5a254bb5af87fa33397a1d712f3a629a3dc9aa3cbf6b`.
Archive SHA256: `5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`.

| Source | SHA256 |
| --- | --- |
| `a_save_dispatch_test.py` | `b536361388785bf7d40e1fced8154413402aae5657efe8c6b680f845c8ae4aea` |
| `a_save_dispatch_audit.py` | `5139d78bf83c269c76fc156f24c4fd0c427ae6b4a9f015f0d109800ee8c7178e` |
| frozen `private_checkpoint_save_apply_regression.py` | `14c36c4dd807426fc057ca1cb792fb805c34280e32f5f8b7a9286074e8b058ee` |

All three sources and archive identities checked before/after the final run.
Native instruction totals: idle phase2 **2917**, selected phase2 **2905**,
phase5 control **2025**. Totals are diagnostics, not completeness percentages.

Failures retained:

- `234721-571935`: second cycle tried native graphics allocation because the
  inherited one-cycle constructor double did not rebuild the association
  cleared by native pop; failure retained as `UcError`.
- `234734-314317`: same failure with richer fault-PC diagnostics added.
- `234811-305298`: same failure after separately correcting the cookie double
  to preserve RAX; that ABI correction did not resolve the graphics issue.
- `234853-697940`: 3/3 after making the Save constructor double explicitly
  reconstruct its owned graphics association each cycle.
- `235002-300539`: 3/3 with exact User identity, selected-business counts
  and second-cycle original callable-destructor assertions added.

- Final `235330-702355`: 3/3 after pinning the exact frozen predecessor source,
  following explicit new-source whitespace checks.

No old failure was removed or transformed into a successful live claim.
