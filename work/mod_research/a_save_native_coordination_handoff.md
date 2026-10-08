# Native Save coordination observation contract

Status: **48/48 offline checks PASS.** The four-point read-only observation
contract and strict scope-pairing analyzer are ready for the root thread's new
`a_save_observation*` tool. No game, Steam, UI, current save, debugger, patch,
native-save request or production permit was used or created by this agent.
The user is temporarily unavailable; **this round does not run a live test**.

## Deliverables and direct interface

- `a_save_native_coordination_events.py`: immutable four-anchor profile,
  archived-source validation, field contract, and `analyze(rows, metadata)`.
- `a_save_native_coordination_test.py`: 41 synthetic pairing/counterexample
  cases, six bounded native-code cases and one static source/stack case.
- This handoff. Frozen predecessors and root docs are unchanged; no Git action.

```python
from a_save_native_coordination_events import EVENTS, PROFILE_ID, analyze
result = analyze(rows, metadata)
```

`metadata` requires `pid`, `birth`, `base`, `run_id`, and `capture_complete`.
The last field describes observer completion, not a native drain. Optional
`capture_errors` is a list of observer errors; optional `profile_id` must match.
Each row uses `seq`, `event`, `rva`, `thread`, `rsp`. Decimal integers and hex
strings are accepted for numeric fields; booleans and floats are rejected.
Per-row PID/birth/base/run_id may be absent when metadata is fixed, but any
supplied identity must match. Snapshot errors must be recorded explicitly.
`seq` starts at 1 and remains contiguous across all selected threads. A gap,
nonzero `lost_events`, or invalid lost-event counter makes evidence incomplete.
Malformed `capture_errors` metadata (including null or a string) is rejected as
`INVALID_CAPTURE`, not allowed to raise an unhandled parser exception.

| Event | RVA | Additional fields, captured **before** instruction |
| --- | --- | --- |
| `save_scope_enter` | `2F7C28` | `archive=RCX`, `stream=RDX`, `archive_stream=QWORD[archive+10h]` |
| `save_scope_return` | `2F7C2D` | `rbx=RBX` |
| `army_worker_enter` | `16C1A0` | `manager=RCX`, `return_pc=QWORD[RSP]` |
| `army_worker_return` | `16C2B7` | `return_pc=QWORD[RSP]` |

Save entry and return must have the same thread and RSP, and return RBX must
equal entry archive. The entry stream must equal the value read at `archive+10h`. Save's RSP is
inside its caller frame, so **QWORD[RSP] is not a Save caller return address**.

Army entry requires `manager == base+1A24CF0`. Army entry and return must have
the same thread, RSP and return PC. At `16C1A0`, `push rsi; sub rsp,20h` follow
the initial register store. The sole normal tail is `16C2B2 add rsp,20h`,
`16C2B6 pop rsi`, then `16C2B7 ret`. RSP is therefore already balanced at the
return observation point. An exception or non-normal exit is not forged into
a normal return pair.

The source file contains the four minimal 16-byte fingerprints. `validate_archive`
checks the full fixed private archive SHA and these bytes. This does not replace
the observer's current process/executable/module/thread validation. The profile
ID is:

`fafc5fb98986eb92af296c9bd01fbb6f3703d381aa3893c38015fe3e38c2a919`

## Result meaning

- `INCONCLUSIVE`: observer ended normally but no complete Save scope occurred.
- `NO_WORKER_SCOPE_OVERLAP_OBSERVED`: complete matched Save scopes, with no
  observed matched army-worker span overlap. This is **not writer exclusion**.
- `WORKER_SCOPE_OVERLAP_OBSERVED`: paired spans overlap in debugger-delivery
  order. Each overlap reports whether the threads differ; same-thread nesting
  is not concurrency. Span overlap is not a proven field-access race or a
  corrupted save.
- `INCOMPLETE_OR_INCONSISTENT_CAPTURE`: missing returns, orphan returns,
  wrong thread/stack/archive/manager/caller, snapshots that fail, observer errors,
  incomplete capture, missing or duplicate sequence, declared lost events,
  wrong source address or run binding.
- `INVALID_CAPTURE`: malformed attachment metadata or incompatible profile.

No analyzer outcome permits export or claims full-world exclusion. Original
records remain with the caller and are not mutated. Incomplete rows are
reported, never silently accepted as empty scopes.

## Narrow native investigation results

1. The direct call layers of normal Save initialize `4A29D0`, User pause
   `3F5920`, User exit `3F7A70` and pre-world serialization `2F7B50` have no direct
   `834BC0` or `16C160` call. Their UI/service descendants remain unresolved;
   this is not proof that all native coordination is absent.
2. The army queue producer `8D3D0` receives manager in RCX and army in RDX,
   optionally locks the list-registry critical section at `base+201D378`, calls
   `172D0` using `manager+18h`'s index, and stores the army pointer into the
   returned node. The actual instructions were run for lock enabled/disabled
   and allocator success/failure. OS locking and node allocation are explicit
   doubles. This is a **registry queue lock**, not a proven whole-save lock.
3. Game initialization `3F7B60` contains a separate inline producer: at
   `3F7C1F` it writes `army+48h=BD10`, then appends through `172D0` and stores
   the army pointer at `3F7C6D`. The bounded native fragment executes this
   path. Watching only `8D3D0` does not capture every producer.
4. `16C160` does call native join helper `834BC0`, but first invokes `16C060`
   (updater/scene-container cleanup), then clears active and both army lists.
   Its known source `509810 → 50986A` belongs to a larger cleanup path. The
   native-code test exercises the calls/flag clear using explicit OS/container
   service doubles. **Do not invoke this function as a pure Save drain**.
5. `161020`, reached from load initialization `487168`, clears queues and
   active before additional updater initialization; it is also not established
   as a normal-save coordination boundary. It was read, not invoked.

Targeted `B11E0` direct-call candidates were only nine: `A8DA8`, `16C2C4`,
`2374A6`, `2A9DF6`, `3F7C27`, `3F85D7`, `3F934D`, `48715D`, `509862`.
The three ordinary producers after `A8DA8`, `2374A6` and `2A9DF6` enter `8D3D0`;
the Game initializer is inline. This remains a targeted source map, not an
indirect-caller closure or all-writer audit.

## Smallest useful next step

Use the root's new observation tool with the first four anchors above around
one **normal user-driven Save**. It must retain original bytes, use its own
supported process identity and new run ID, watch existing and newly created
threads, and report clean debugger detach. Do not start a native save through
the analyzer, reuse an old receipt, or equate zero observed worker events with
drain ownership.

If Save/worker spans overlap, next isolate actual field-access order or an
existing shared lock; span overlap alone does not justify suppressing Game.
If additional draining is needed, the normal `16CB30` join path remains the
smallest candidate: observe original `16CB5B call834BC0` → `16CB60` return,
associate it with the exact Game/manager generation and queue producers, and
only then prevent re-start for the retained Save generation. No extra gate is
implemented or authorized this round.

A second four-point source pack can observe producer `8D3D0`, inline queue
store `3F7C6D`, native join call `16CB5B` and join return `16CB60`. It is listed
for follow-up and is **not** part of the active `EVENTS` or analyzer pairing.

## Validation and failures

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research'
py -3 work/mod_research/a_save_native_coordination_test.py
```

Final 48/48 result:

- `a_save_native_coordination_runs/20261008-180406-430341/result.json`
- Result SHA-256 `dd7c45c831cefa5fe4f55bfcafd9bf16a649c028a6d415c7544bae9f0f6d36de`
- Events source SHA-256 `95a601bda01b9ad1dc022a4cb509994582debea6b51660b4f94cc2c04913ef44`
- Test source SHA-256 `e56e6d7b824a02a7569d254975a5a2c4c2e7e10ca76a8a647cae6132fb021865`
- Frozen prior audit dependency remains `36885d10878f9ad5f80a3e8946c8895e020a50130b192c7fc46d20e5d4e56c05`.
- Source dependency and private image end hashes match their starting identity.

`20261008-175606-962835` failure remains: the cleanup fixture initially retained
archived heap pointers in the updater, causing an unmapped read. The fixture
now uses an explicitly empty owned updater; it does not skip native cleanup.
`175623-745937` and `175658-817384` intermediate 35/35 passes remain. The latter
corrected evidence fields to distinguish failed allocation (no queue store)
and inline army-field writes from ordinary pointer enqueue. Root review then
identified that increasing but noncontiguous sequence values could hide a
whole missing worker pair. The final 48/48 adds 13 parser cases and rejects
that gap, a missing first sequence, nonzero/invalid lost-event counters, and
malformed observer-error metadata. The four-anchor profile ID is unchanged.

Pending operations: none for this module. Await future user availability for
the root's separately reviewed read-only live observation; there is no active
patch, debugger, request, background recorder or permission from this agent.
