# Normal Save parent and scheduler coordination audit

Status: **11/11 bounded offline cases PASS; sources frozen.** This round did
not discover, open or control the game, Steam, UI or current saves. No debugger,
patch, native save request, production permit or pending user action exists.
No Git operation or root-document change was performed by this agent.

The useful new result is narrow: the ordinary seven-state menu stack still
schedules Game before Save. In the archived branches, Game.Update can return
while its separately started army task remains active; the subsequent Save
Update can then start a different Save task. The fixture supplies OS completion
answers, so **this is not a real observed race or a corrupted-save result**.
No transitive lock or coordination inside unresolved native services has been
proved absent.

## Files and entry

- `a_save_parent_coordination_audit.py`: bounded archived menu and scheduler
  execution, actual army queue-transfer path, source checks and a second
  diagnostic event specification. No live entry exists.
- `a_save_parent_coordination_test.py`: explicit private-archive runner with
  before/after source, image and pdata identity checks.
- This handoff. Frozen predecessors are unchanged.

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<local existing private archive directory>'
py -3 work/mod_research/a_save_parent_coordination_test.py
```

The runner reads only `game-runtime-image.bin`, `runtime-pdata.bin` and the
`python_deps` directory under that explicit research archive. It loads only the
two existing harness **class ASTs**; historical top-level runners and
`disasm_chained`'s implicit archive lookup are not imported or executed.
Large instruction traces and all raw archive-derived output stay in ignored
private run results; no whole function dump is added to source.

## New bounded findings

1. The actual menu/queue fragments produce
   `Root → Motor → Game → Strategy → User → Config → Save` through the normal
   Config/SaveLoad empty-slot route. The existing explicit lifecycle callbacks
   record User pause, but this queue path does **not** invoke Game's pause
   callback. UI and lifecycle callback bodies in this experiment remain doubles;
   the observation is callback selection, not their transitive effects.

2. The actual `509FE0` scheduler fragment `50B441..50B669` walks that seven-state
   order. At `50B59C` it starts a Root state task, calls `834EF0` at `50B5A5`,
   queries completion at `50B5AE`, and on the completed branch releases the
   state's `+50h` association at `50B603` before walking forward. The fixture
   takes completed Root tasks, **not** the separate suspended/yield path.
   Root's OS dispatch is a named service double which calls the archived Game,
   User and Save Update bodies synchronously on one emulated CPU. Other state
   Updates are explicitly doubled. No actual OS pool/thread claim is made.

3. The independent Game army lifetime is visible at `3F85DF → 16CB30`:
   `manager+90h != 0` and the supplied `834460` result of zero takes `16CB51`
   directly to the normal return, without joining. Actual Game.Update then
   returns with army active. User's actual Update returns at its not-top check.
   Actual Save phase0 only records a clock and changes to1; phase1 proceeds to
   `4DA320`, constructs worker `508CA0` at `save+478h`, and calls start at
   `4DA366`. This is a different thread object from `army_manager+20h`.
   The held-army cases, with registry locking enabled and disabled, both reach
   that Save start while the fixture army active value remains1.

4. The former pending-to-working copy double has been narrowed: actual
   `16BB70..16BC9A` now executes. It clears the working list through the named
   container service, walks the pending list, appends working nodes, writes the
   **same army pointer** at `16BC01`, and clears the pending registry list at
   `16BC74`. Allocator/list-clear and critical-section services are still
   explicit doubles. This transfers a queue of object pointers; it does not
   create a frozen copy of army object fields for serialization. The field
   writer/serializer intersection remains the earlier `a_save_writer_scope`
   evidence, not a new serializer execution in this test.

5. A positive control identifies a real parent coordination point:
   `50B63B..50B63F` compares the state-transition pending count against the value
   before that Update; a changed count stops the remaining frame, deferring Save.
   The counter change in this case is an explicitly synthetic service response;
   the conditional comparison and stop are actual archived instructions. This
   barrier concerns **state-transition queue mutation**. It is not a retained
   army writer lease, and army active alone does not take this path.

6. Separate prior-drain counterexamples execute actual native join and then
   the real ordinary producer `8D3D0` before the next frame. To isolate a prior
   join claim, these cases explicitly insert another phase0 frame by resetting
   the fixture Save phase. They are **not** presented as uninterrupted natural
   Save timing. Without a new producer, Save starts with army inactive; with a
   producer, actual `16CB30` starts army a second time before Save starts. A past
   join without retained producer/start ownership does not prove continued drain.

Menu-produced state order is remapped into new owned frame-VM objects. This is
not a full native menu-to-worker lifetime integration. No army worker body,
world serializer or file-writing service runs in the new frame experiment.
Unresolved Game/UI services, normal Save preparation/serialization descendants,
and other callers/producers remain outside the result.

## Reusable point and smallest next observation

Keep the existing `a_save_observation_status` four-point Save-read/army-body
observation as the **first real observation** when the user is available. It
can determine whether the actual matched scopes overlap. No overlap observed
does not grant exclusion; overlap alone does not prove conflicting field access.

If a second bounded record is needed, `observation_spec(raw)` supplies small
version fingerprints and pre-instruction field requirements for four points:

| Event | RVA | Binding |
| --- | --- | --- |
| army join call | `16CB5B` | RDI=manager, RCX=manager+20h, thread/RSP |
| army join return | `16CB60` | same thread/RSP/RDI; active is still pre-clear |
| army start call | `16CBD6` | RDI=manager, RCX=manager+20h; active is still pre-publication |
| Save start call | `4DA366` | RDI=Save, RCX=Save+478h, Save phase; army active/queue snapshot |

This specification is **not an implemented observer**. A current-process
identity check, validated source, supported DR ownership/recovery, all-thread
coverage and contiguous event accounting are required before any future use.
A start-call hit is only a dispatch attempt, not a worker-body entry or completed
start. Join-return observation precedes the active-clear instruction. Separate
runs cannot be merged into a single causal timeline. Queue observations need
validated pointers and indices; read failures remain incomplete evidence.

The normal join return remains a possible future coordination point, provided
the same owner can retain the exact generation and block fresh producers/start
until serialization ends. This round does not implement such ownership and does
not recommend invoking destructive `16C160` as a drain. Prefer evidence of an
already existing native Save coordination mechanism over adding another gate.

## Validation, failures and identities

Final: `a_save_parent_coordination_runs/20261008-220838-995091/result.json`

- Result SHA-256: `08e97aaea1f7ca6faf5438a02243845bfb99a8197a12b3f5e09b1cdf18005db2`
- 11/11: one static source check, one actual menu/queue control-flow case,
  eight frame cases (empty/held/join without producer/join then producer, each
  with registry lock disabled/enabled), one native state-transition barrier.
- Earlier `20261008-220702-279224` is retained: also11/11, before adding explicit
  army-inactive initialization, Update alignment, transfer-store and ordering
  assertions. No failed execution occurred in this round. Earlier research
  failures are untouched.
- All five source pins match at start/end; image and pdata are rehashed at end.
  No native executable binary is produced: archived instructions run in Unicorn.

| Source | SHA-256 |
| --- | --- |
| `a_save_parent_coordination_test.py` | `9f30d1ba8b90340138c7982213a197bf83d7db29db6b442e17dfac61049b6580` |
| `a_save_parent_coordination_audit.py` | `75bf6e9e9480b2a47ddb4d3533ed4ba01cebf963090c34a02b916f68bbc9b23d` |
| `a_save_writer_scope_audit.py` | `36885d10878f9ad5f80a3e8946c8895e020a50130b192c7fc46d20e5d4e56c05` |
| `private_checkpoint_save_apply_regression.py` | `14c36c4dd807426fc057ca1cb792fb805c34280e32f5f8b7a9286074e8b058ee` |
| `save_return_menu_regression.py` | `da9ab6a1f1cb00e00b03959d515e8a43de2c8fa7fce670f66ebcfaa6a9af2baf` |

Image SHA-256:
`5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`.
Pdata SHA-256:
`74e018f15ec009af5fd0e0d91ce981b82d7d970150b3dce5861f17d11eea2e9f`.

The conclusions are offline branch/ordering evidence and an observation plan.
They do not make A save production-ready or make the first two-PC test ready.
