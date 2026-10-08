# Checkpoint through the existing Save lane while Ready remains held

Status: **22/22 owned-process native cases PASS**, including ordinary Submit
refusal, one Save/native-storage-readback path, retained Ready/Gate, rejected
stale observation and identity/cut/date counterexamples. No game, Steam, current
save or UI access; no preflight/record/live installer, active debugger or game
patch. This agent did not change frozen predecessors, root docs or Git.

This is a **current-date, current-period trusted-host interface**. It does not
advance time, accept a next-date request under an old Controller, prove Room
authority, authorize production export, or provide complete writer/input
exclusion. The root's separate network mapping must bind the authenticated
scope to this local evidence; a JSON flag cannot create an observation.

## Composition and API

Link these four new C++ implementations:

- `planning_checkpoint_save_owner.cpp` **instead of** `planning_period_owner.cpp`;
- `planning_checkpoint_save_gate.cpp` **instead of** `planning_input_interlock_gate.cpp`;
- `planning_checkpoint_save_interlock.cpp` **instead of** `planning_period_interlock.cpp`;
- `planning_checkpoint_save.cpp`, plus existing unchanged bridge/Driver/storage
  dependencies as listed in `planning_checkpoint_save_test.py`.

Do not link both an implementation and its predecessor, create another physical
Owner, or overlay a second bridge bank. Existing Owner/Gate/Controller public
class headers/ABI are unchanged. The new `planning_checkpoint_save.h` exposes:

```cpp
struct Evidence {
    checkpoint_planning_hold::Binding binding;
    planning_period_owner::Date date;
    uint64_t periodSerial, readyRevision, gateRevision, observation, cut;
};
bool Submit(Owner&, Gate&, Controller&, const Evidence&, const fs::Request&) noexcept;
bool Copy(Owner&, Gate&, Controller&, const Evidence&, uint64_t generation,
          fs::Artifact&) noexcept;
```

The aliases above describe the signatures; the header has the full namespace
types. Inputs are copied before use. `Copy` clears output on failure and succeeds
once for the reservation. It releases **only that reservation**, leaving Ready
and Gate requested hold unchanged. There is no abort/reset/replay API for an
uncertain accepted save.

The two `_entry.inc` files hold the new Gate/Owner paths;
`planning_checkpoint_save_lifecycle.inc` retains the previous lifecycle with
one additional `quiet()` restriction: outstanding checkpoint reservation blocks
retirement/rebinding. A Copy must finish before that logical transition.

## What admission actually checks

1. The exact initialized Owner and Gate are registered once by their replacement
   implementations. The Gate's configured Save Owner must match. This is an
   internal in-process linkage, not a hostile local-process security boundary.

2. The Controller must be the current claimed object for the same logical
   period and trusted execution thread. Binding includes native attachment,
   owner generation, period, epoch and input digest. Current native date/viewer,
   retained Controller date and requested date/viewer all match; logical serial
   and Ready/Gate revisions must match. A retired Controller is rejected.

3. Successful `EndObservation` alone seals the actual report counters in the
   new core. Submit loads that sealed record and checks its observation identity.
   While holding Gate then Owner locks it compares the fresh bridge/counter
   values with the sealed values and rejects active scopes. Additional User or
   Game execution since that observation therefore invalidates this submission.
   **Snapshot alone cannot refresh old observation evidence into permission.**

4. Ready remains true; reward lane has no queued/active/uncertain work, submitted
   equals completed, and `Evidence.cut` and `Request.cut` must equal that local
   completed sequence. Zero is valid. `Request.period` equals the native logical
   binding period. The request room ID/epoch and the original Driver's request
   checks remain in place. An opaque full Room/PeriodCoordinator mapping belongs
   to the trusted host, not this module.

5. Original Save report guard/cursor, exact User/Save sources, storage ownership,
   room binding, Driver admission and SEH failure handling are retained. The
   default `Owner::Submit` function is **byte-for-byte source-identical** to the
   frozen predecessor and still refuses `readyFence`. New admission is separate;
   it does not transiently call ReadyFence(false) or Gate.Hold(false).

6. Gate reserves the request while holding its mutex; the Owner reserves the
   matching generation under its control mutex. Gate.Hold, direct ReadyFence
   changes and period retirement refuse while this reservation is outstanding,
   including the interval after native Save completion but before Copy. The
   old direct CopyArtifact API also refuses this reserved checkpoint, preventing
   export without its matching Controller/evidence/generation wrapper.

7. User enters the unchanged actual Save lane and the existing upstream cut
   suppresses its covered planning work. The original Driver continues through
   its existing save phases, report checks, original returns, FINALLY and storage
   readback checks. On Copy, exact retained metadata is checked again, current
   date/binding/Ready are checked, and the original completed-artifact checks are
   applied. Stop or report drift denies the result and does not retry a save.

The code deliberately does not label a sampled report as a whole-engine lock.
Unknown Root/device/input consumers, external writers, original background army
coordination and external source publishers remain outside this bounded lane.
Fatal Stop/source replacement can remove valid coverage; the operation then
fails and cannot produce a successful artifact/permit. This is not a claim that
all external native activity stays paused under arbitrary interference.

## Lock order and lifetime

- Controller Snapshot occurs before the Gate reservation transaction.
- The registry lock only copies fixed callback/context/report data and is
  released before invoking a Gate or Owner callback.
- Admission and Copy take **Gate lock → Owner control lock → existing Driver /
  storage internals**. The new Owner path never calls Gate, Controller Snapshot,
  MatchesOwner or CurrentController while holding its lock. It reads the
  already-local lifecycle record directly inside that same translation unit.
- This matches the existing Gate User-tail callback's Gate→Owner direction.
  Storage providers retain their original non-reentrant/no-Owner-call contract.
- Controller observation registration takes its Controller lock then the short
  registry lock, after its existing reads have released Owner/Gate locks.
- Objects, code and registered contexts remain retained until process exit.
  Failed initialization does not reset a once-claimed physical Owner or registry.

Copy does not need the old Controller `observed` flag to remain true during Save:
Snapshot normally clears it while the Save lane is active. Copy uses the exact
reservation that consumed the sealed observation. A new Submit cannot consume
the same observation twice. A later ordinary observation can be performed after
Copy; the fixture demonstrates explicit Controller release afterward.

## Tests and honest execution boundary

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research'
py -3 work/mod_research/planning_checkpoint_save_test.py
```

The runner compiles production-flag objects/static library and separate fixture
objects. It uses only fixed private research profile/planning-library inputs,
new own-process memory and dedicated run directories. Native business Save
payloads remain diagnostic doubles; the result is not a valid newly generated
game save. The actual bridge ownership, callable scopes, upstream transformation,
Save Driver phases, file/native-storage readback and callback/FINALLY checks run
in the owned process. This is not an actual game or two-client test.

The 22 scenarios cover: normal and wrong-metadata Copy; post-commit Stop/report
drift; missing observation; wrong Owner/Gate/Controller/binding/serial/observation/
Ready revision/Gate revision/cut/period/date; native date drift; extra actual
held User or Game call; pending reports; published source-slot conflict; and
submission from a different thread. Normal execution also checks direct release
refusal, duplicate submit/copy, early Copy, retirement before Copy and no global
input/production permission fields.

Final result:
`planning_checkpoint_save_runs/20261008-223656-231147/result.json`

- 22/22 PASS, 1493 fixture assertions; 60 source hashes unchanged.
- Result SHA-256 `b57f8f9e6512cb59fd1d3b37b96b90e213d61276696f49de2ad32a22edf37a82`.
- Fixture SHA-256 `7c9581da17ef33142ca01aac65a609b955c1a343bcb328e10e7106340ca026ed`.
- Private profile is checked before/after compilation/testing by the runner.

Retained failure:
`planning_checkpoint_save_runs/20261008-223443-495885/result.json`, 19/22.
Two stale-observation tests exposed a real implementation bug: the initial
version trusted refreshed Snapshot counters. The new EndObservation sealing
fixes it. The source-conflict fixture initially wrote directly to its own
read-only vtable page and faulted before exercising admission; it now explicitly
changes that owned page's protection, replaces the source, restores protection
and verifies rejection. No game page was involved; failed records remain intact.

## New source fingerprints

| File | SHA-256 |
| --- | --- |
| `planning_checkpoint_save.h` | `c7f1f6603c371e2b0eaecd171c38199e57241338f774745a4647cc541587e105` |
| `planning_checkpoint_save.cpp` | `047f9d693b750abc4e2c4183eacd25c4ac8840c27391271ef61babf3083a833c` |
| `planning_checkpoint_save_owner.cpp` | `b868d56c773757b76093d1e8c5b484d2e44104eaba9d79de6ea0c100564c4788` |
| `planning_checkpoint_save_gate.cpp` | `0a4cccf7211e885bc0f0e691b8a4b06ec9850bfb03b9ff9143f6b2a3f3d8ee59` |
| `planning_checkpoint_save_interlock.cpp` | `2c9bc2e4ea7f3137b54775e80ad571b04ad080caa5807e8665707319195093a2` |
| `planning_checkpoint_save_owner_entry.inc` | `c791c313a5b1fb7f889f7ed07f9718d2a0c7d70b79e144459eaf7144d39cc23b` |
| `planning_checkpoint_save_gate_entry.inc` | `87b5efbee24935351172f89ec24358c9043195cd762c67385e8d5721ffe06b39` |
| `planning_checkpoint_save_lifecycle.inc` | `ee4d8f203a662564b4d780745d228bae4fc5a49c9a8c0c4d88ef8934a845246c` |
| `planning_checkpoint_save_fixture.cpp` | `4aa092e470de832962cafda0d585feb7ac15edcd0aef4f4c738e540c6f277938` |
| `planning_checkpoint_save_test.py` | `df3f9632ffcb27ce0bbf9cdf05486884adea9c0a8b0e13a2a7c16acd0adbac59` |

Next: root's explicit held-IPC successor can call these Submit/Copy functions
on its trusted execution thread. Current-period/same-date wiring must be tested
before defining the separate post-simulation checkpoint phase. An old date-bound
Controller must not be relaxed to accept a旬末 request from another date, and a
new Room scope must not be invented before the authoritative stage transition.
