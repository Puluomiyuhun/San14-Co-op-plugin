# First live normal Save: result and smallest useful follow-up

Status: the root's user-driven Save has one complete observed serialization span,
zero observed army-body spans, and verified observer cleanup. This agent only
read that archived record and pinned historical code; it did not access the game,
Steam, current saves or UI. No live tool, patch, permit or request was created.
No root documents or Git operations were changed by this agent.

## Evidence now available

- Run: `a_save_observation_status_runs/20261008-232414-909674`.
- `result.json` SHA-256: `fceaef9008828bd710e273f20605a6647e124eb9ca35d5489f8047f0677fa094`.
- `trace.jsonl` SHA-256: `6e73f0cbbcf431b4cbf27b142cc6c9aaaf567a9ed3e9634fa49d1b2a88d556e0`.
- One Save entry and matching return, same thread/RSP/archive; no army entry or
  return; two contiguous selected records, zero lost events, no analysis issues.
- Both arming and restoration report 102 threads; restoration checks all six
  debug registers and owned queued events. Observer exits 0 and detaches cleanly.
- Classification remains `NO_WORKER_SCOPE_OVERLAP_OBSERVED`, not exclusion.
- The user reported saving slot49. The observer itself does **not** attest a
  filename, valid save bytes, completed file close, or a return to the map.
  Root's separate file/phase verification is required for those claims.

The four observed addresses cover world serialization (`2F7C28/2F7C2D`) and
army body (`16C1A0/16C2B7`), not army dispatch decisions. Consequently army0
cannot distinguish an empty work list, skipped dispatcher, previously finished
work, or another native coordination mechanism. It also does not cover other
writers or establish zero worker activity after the observer ended.

## Small offline branch verification

Using the existing frozen `a_save_writer_scope_audit.VM`, archived native
`16CB30` instructions were executed for start, pending, joined, and empty queue.
Result: **4/4 bounded cases PASS**, not four live tests.

Private result: `a_save_first_live_review_runs/20261008-233113-587399/result.json`
SHA-256: `3d267540c9d379f88eb57cd1ce99e5a39bef0d2de119e45f10353a7f86c5789a`.
The runner was a one-off review command reusing the frozen VM, not a new live
entry point or standalone production module. No new executable was built.

| Branch | Actual archived behavior | Doubled parts |
| --- | --- | --- |
| inactive, pending0 | `16CB90` count check → `16CB95` → `16CBE5` return; no poll/join/start; active remains0 | owned manager/list memory |
| inactive, pending1 | transfer, construct and start calls; then native active publication | transfer and OS services |
| active, completion0 | `16CB4F` test → `16CB51` → return without join | completion query |
| active, completion1 | native join call, then `16CB60` active clear | completion query and join |

This gives a concrete alternative explanation for the live zero-army result:
ordinary idle saving may have no pending path work. It does not determine which
branch the real game actually took. The archive SHA is
`5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`;
the unchanged VM source SHA is
`36885d10878f9ad5f80a3e8946c8895e020a50130b192c7fc46d20e5d4e56c05`.
No failed run occurred in this review. Earlier failures remain untouched.

## Four-point branch observation proposal

Do not ask the user to repeat the same four-point body observation without
changing the information collected. A narrow successor could distinguish the
actual dispatcher branches using these **pre-instruction** sites:

| Event | RVA | Required values and interpretation |
| --- | --- | --- |
| dispatch active decision | `16CB3A` | RCX=fixed manager; active=`u32[RCX+90h]`; thread/RSP; zero selects pending-count path |
| pending count decision | `16CB90` | RDI=manager; RAX=registry count array; RCX=unsigned list index; actual qword count; zero selects immediate return |
| poll result decision | `16CB4F` | RDI=manager; EAX actual completion result; zero selects immediate return; nonzero reaches join call |
| Save start attempt | `4DA366` | RDI=Save; RCX=Save+478h; phase; exact manager active and validated pending/working list snapshots |

The first three sites share the adjusted `16CB30` frame (push RDI/sub40), so
thread/RSP/manager are useful per-invocation links. A missing terminal branch,
unexpected recursion, a field read failure or wrong branch order is incomplete
evidence, not permission. At `16CB90`, validate the index against the live
registry capacity and every pointer before reading; do not assume a fixed safe
index. Registry addresses/layout are in the prior parent observation contract.

Keep all source/attachment identity, all-existing/new-thread coverage,
contiguous sequence, event loss, DR6 ownership and clean restore requirements
from `a_save_observation_status`. A saved count is a sample, not a lock.
This proposal is **not implemented or approved for live execution**.

The distinction from the prior parent's four-point pack is important:

- `16CB5B/16CB60/16CBD6/4DA366` observes paired join and start attempts.
  It can show that a completed join was followed by another start. With an
  empty list it can still return only Save-start evidence and leave army0
  unexplained.
- The proposed branch pack explains empty/inactive/poll decisions. It does
  **not** prove join completed, start succeeded, a worker body executed, or a
  serialized file was committed. Nonzero pending count only means the native
  branch proceeds toward transfer/start, not that those later operations finish.
- Separate runs with different four-point packs cannot be merged into one
  causal timeline or a continuous exclusion claim.

Use the branch pack only if the remaining production design actually needs
that distinction. User-driven valid saved files can meanwhile unblock separate
B file/continuous-load validation; proving the army branch is not a reason to
stop independent work or to replace the two-client objective with diagnostics.

## Producer and writer coverage: what a Game gate can and cannot claim

The archived direct-call byte scan for `16CB30` has only `3F85DF`, inside
Game.Update. This supports a narrow candidate: owning the covered Game path
could stop that known **future start**, while retaining a paired completed join
for an exact manager/generation. It does not stop an already active worker.
The scan is not an indirect-call closure or a thread proof.

Known queue producers:

- The three ordinary producer source sequences after singleton calls `A8DA8`,
  `2374A6`, and `2A9DF6` reach `8D3D0`. Existing work executes enqueue body and
  its optional registry lock, but has not traced every caller to the covered
  Game task/thread. They cannot all be asserted to lie inside the same Gate.
- Game initialization `3F7B60` has an independent inline producer, storing the
  army pointer at `3F7C6D`; it also writes `army+48h` before enqueue. Initialization
  and world replacement need lifecycle ownership, not only an Update gate.
- The army body itself is a distinct asynchronous task. Its `2CD3E0` path writes
  fields that are serialized from live army pointers. A completed Game.Update
  does not establish completed army work.
- The same `2CD3E0` field-writing target has other direct-call byte candidates,
  including `24B409`, `24B73A`, `24BF9C`, `24C17E`, `24D3D3`, `24D5E1`,
  `24F9AB`, `266397`, `2A8EDD`, `2AFAC0`, `2B12A2`, `2B12F3`, `2B7FC7`,
  `2C97EC`, `2CD3AB`, and `2CD821`, beyond worker call `16C238`.
  These candidates need instruction/function/thread attribution; they are not
  proof of 16 additional concurrently active writers, but prevent claiming
  that covering the one army worker closes all paths to those fields.

There is therefore no basis yet to say “all producers run on Game's thread”.
There is equally no evidence requiring suspension of the entire game. Prefer
reusing and proving normal native Save ownership, or retaining only the exact
necessary producer/start/lifecycle boundary, with explicit coverage limits.
Do not call `16C160` as a drain: its known cleanup changes objects/queues.

## Shortest production-oriented next work

1. Root finishes this run's slot49 and map-state verification and backup policy.
   Keep observer evidence separate from filename and file-validity evidence.
2. Connect the existing held-save/date-boundary path to a trusted game-thread
   scheduler and normal Save lifecycle, preserving Config/Save ordering and a
   native return/close observation. The current 32-byte diagnostic driver and
   synchronous fixture callback are not production save execution.
3. Establish retained ownership for the actual serialization interval. If normal
   native Save already provides it, reuse that exact mechanism. Otherwise close
   the specific known start/producer/lifecycle gaps before issuing a production
   permit; an earlier join or sampled active0 is insufficient.
4. Then prove two new legitimate saves from one retained Owner/room across two
   periods and send them to B's same retained loading runtime. The first live
   manual save result does not replace this acceptance test.

This handoff adds no production gate and makes no new full-writer-exclusion,
complete-input-blocking, automatic-save, or two-PC-playable claim. There is no
pending user action from this review and no active recorder/patch from it.
