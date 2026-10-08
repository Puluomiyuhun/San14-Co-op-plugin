# Same-period native date boundary successor

Status: production library built; 16/16 owned-process cases PASS, 1,019 assertions.
Offline only. No game/Steam/current-save/UI discovery, attachment, live installer,
or debugger. Diagnostic children run once and exit; no resident game module exists.
Frozen predecessors are unchanged.

## API and implementation

`planning_simulation_boundary::Execute(owner, gate, controller, evidence, run,
context)` is a trusted **synchronous host callback boundary**, not a game scheduler
or simulation permission. `run` has type `bool (*)(void*) noexcept`. It must execute
on the existing Controller/Owner thread. The new four translation units are:

- `planning_simulation_boundary.cpp`
- `planning_simulation_boundary_owner.cpp`
- `planning_simulation_boundary_gate.cpp`
- `planning_simulation_boundary_interlock.cpp`

Link these instead of the respective held-checkpoint Owner/Gate/Interlock;
continue linking `planning_checkpoint_save.cpp`. New `.inc` files implement the
replacement lifecycle, checkpoint entry and boundary entries. Never link two
implementations of the physical Owner/Gate/Controller together.

Admission reads the actual sealed EndObservation report (not freshly re-labelled
Snapshot counters), checks exact native/local binding, logical serial/date/cut,
Controller and thread, original sources, actual live root/world, held Ready/Gate,
report cleanliness and storage/known pending layout. Gate then Owner is the lock
order. A phase reservation is latched before invoking the native admission;
an admitted failure is terminal and does not automatically retry.

The callback executes outside those locks, with explicit entered/returned/FINALLY
counts and SEH handling. On return the native entries check the same physical
identity, original nextDate, unchanged command cut and Ready revisions, actual
Game native returns and held User callbacks, no active/abnormal scopes, sources,
report and the ordinary five-state User planning layout. This is stronger than
accepting a JSON `simulation_done`, but still relies on a trusted host callback
and does not prove game simulation correctness or exclude background writers.

Success retains the original epoch, period and logical serial. The lifecycle
keeps its starting date and moves its effective checkpoint date to the next node.
The SAME Controller then needs a NEW actual BeginObservation/Game/User/
EndObservation sequence before `planning_checkpoint_save::Submit/Copy` can run.
Execute itself does not create that new observation or save automatically.
The old Controller date guard is explicitly replaced with the current lifecycle
expected date; it does not accept arbitrary dates or a different world.

Throughout the phase, direct ReadyFence, Gate.Hold and Controller.Request refuse
release. Copy ends only the save reservation; it does not end the phase hold.
Retire requires a successfully copied checkpoint and a new observation. Explicit
Rebind must supply the next period/epoch/digest at the SAME already-reached date;
only then can a new Controller claim the new period and release. This test
executes the actual Retire/Rebind calls, without resetting bridge or sequence
state. It does not grant network reconciliation authority: the trusted host must
only call Rebind after the real room has advanced.

Failure preserves the Ready/Gate requested flags, leaves the phase held and stops
the Owner; no automatic release or rollback occurs. This is NOT full input
exclusion: existing Gate error/stopped paths can forward some UI consumers,
which remains a production host/input-boundary gap.

## What remains unconnected

The owned callback writes the diagnostic world's date and runs the existing
Game/User fixture callbacks. The native Game bridge still forwards its Game body;
known UI/panel consumers are suppressed and User is Ready-suppressed. Real
simulation state-stack transitions, asynchronous scheduling, modal events, actual
world writers and legal save generation are **not** exercised. No real engine
advance entry is installed or invoked.

The frozen The frozen `planning_period_session` still pins its initial scope date. The new
[Session successor](planning_simulation_session_handoff.md) accepts only this
exact boundary's endpoint without changing the original scope; root's
[two-period pipe composition](a_save_simulation_ipc_handoff.md) now exercises it
with actual Room scopes, native retirement/rebind and two diagnostic saves.
This module's standalone test does not itself include that composition. Real
engine/thread scheduling, continuous input/writer exclusion, legal game saves
and production authorization remain absent.

## Reproduction and evidence

From repository root, with existing private fixture dependencies:

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research'
py -3 work/mod_research/planning_simulation_boundary_test.py
```

Use locally generated run identity on another machine. The builder requires the
private archived save profile and previous planning runtime import library;
no full archived bytes or binary artifacts are committed.

Final run: `planning_simulation_boundary_runs/20261008-230452-084576/result.json`.
SHA-256: `a587c3fad6cb6b1b509a01d82a6952abce488f4f3796f9eaf12bd27f3811d942`.
64 pinned sources all rechecked current. Fixture SHA-256:
`fba4a0573b2fca4790412b21819dc15129e72c2fef49c7caf9482c0a85d0b972`.
Production library SHA-256:
`4fde55e733ff2f66c66db93ebd1a45c8d87c929e7c5686968fba60ec20663d44`.

One positive case executes boundary -> new observation -> same-period held Save
-> real diagnostic storage readback/Copy -> observation -> Retire -> Rebind -> new
Controller release. The other 15 cases reject wrong thread/binding/serial, stale
Game observation, unchanged/skipped date, no callbacks, Game-only/User-only,
callback false, actual callback SEH, pending report, replaced world, Stop and
actual published source-slot conflict. There are no skipped cases.

Failures remain preserved:

- `20261008-230243-640566`: 9/12 passed. A release attempt inside the callback was
  refused by the held Gate, but the old Controller then latched PartialRequest,
  poisoning later observation. The explicit successor now refuses Request at its
  phase guard before any mutation. The world-change fixture also incorrectly
  expected a normal callback after deliberately replacing world; it now lets the
  finish boundary observe the conflict directly.
- `20261008-230320-731959`: intermediate 12/12 pass. Expanded to the final 16 cases
  and removed a duplicate positive case; the additional cases exercise distinct
  native callbacks/source conflicts.

No pending manual-game request. The root composition now binds the room identity and Session successor. Next bind
real trusted game scheduling/serialization coordination before a real two-save test.
