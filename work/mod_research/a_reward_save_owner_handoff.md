# Same User owner: reward queue and save successor

## Result and boundary

Final owned-process run: `a_reward_save_owner_runs/20261008-190836-956268/result.json`.

- 11/11 PASS: nine native composition/failure cases and two persistent worker protocol cases.
- Result SHA256: `4d7521cecb369fde9b87dd11878f337080e03e5f7c3386d17dc00b87bd28282c`.
- Fixture SHA256: `805b99a02b65f91eccb5af2c74f014bd7bcc5195611779dca97fbd82aefd038e`.
- 51 public-source fingerprints checked unchanged. The result also fingerprints the actual frozen PlanningHold DLL, new reward fixture DLL and production owner library.
- Production Owner/bridge and reward objects compile without the fixture macros under `/W4 /WX`; fixture also uses `/EHa` for real SEH unwind.

This is a new implementation successor. No frozen files were modified and no game, Steam, UI, current save or live-entry script was accessed. Actual shared User/Save vtable publication, PE claim/FINALLY, pooled command ownership, PlanningHold authorization/replay and the existing save lifecycle execute in owned processes. Reward effects and User/Save/storage business remain explicit fixture doubles; generated saves are diagnostic files, not SAN14 saves. The updater/source profile and thread-publication restrictions of the upstream predecessor remain. There is no production install permit, all-thread fence, full-world proof or network Ready grant.

## Composition

Link `a_reward_save_owner.cpp` instead of `a_save_upstream_owner.cpp`, and `a_reward_save_owner_bridge.cpp` instead of `a_save_user_owner_bridge.cpp`. Keep the frozen User bridge ASM and upstream gate/source modules. Do not link or publish the older Dispatcher beside this Owner.

The new header exposes sidecar functions for the exact retained `a_save_user_owner::Owner`:

- `Bind(owner, Config)`: one immutable planning binding plus trusted fresh Source sampler.
- `Submit(owner, binding, sequence, Command)`: copies values into a single bounded queue; sequence must be the next local admission ordinal.
- `Cancel(owner, binding, sequence)`: queued cancellation prevents invocation; active cancellation only revokes and keeps resources alive until the synchronous call exits.
- `ReadyFence(owner, binding, bool, revision)`: a local whole-input-prefix admission fence, intended only after the room has both players ready and no pending commands. A single player's Ready must not engage this fence: the other player can still submit remote commands. This function is not a Ready acknowledgement or complete input lock.
- `Snapshot(owner, Report)`: exact lane outcome and actual owned replay/admission reports.

The sidecar and Save/Hold admission use the same Owner control lock. A queued or executing reward excludes save requests, User hold changes and Ready sealing. Active Save, User hold or Ready sealing excludes rewards. Requests cannot relabel an already executing User scope. The test covers both reward-then-save and save-then-reward on the same actual published slots.

At the real User callback the selector rechecks the frozen original/source profile, idle manager/cache identities and report guard. It selects a new reward-only suppressed branch. The bridge creates its genuine Before owner scope for this branch, while explicitly omitting original User Native/After. The reward callback claims that exact frame and verifies thread, slot, generation, depth and call ID; then the trusted sampler must return the same pinned base/root/world/user and exact binding. Production checks the fixed native reward target. The provider checks actor authority, eligible people, funding, resources, expiry and deep command content at preparation and consumption.

The branch uses `RewardOwnedCreate -> PlanningHoldCreate -> Hold request -> RewardOwnedPrepare -> RewardOwnedExecute -> synchronous cleanup`. It never calls the old Dispatcher or installs another User wrapper. Each reward owns its own pooled list and adapter context on the actual callback thread. Original SEH crosses the reward/PlanningHold layers and real PE FINALLY; it does not manufacture an original User return. The sticky error/uncertain state refuses later work. Running cancellation is conservative: the native operation may already have applied, so its eventual success cannot silently become a clean replicated acknowledgement.

Cancellation and local sequence values are not peer execution receipts. A cancelled admission leaves a visible gap/outcome; the surrounding authority/journal must account for that state rather than infer that every lower ordinal applied.

## Executed cases

- `two-rewards-save`: two distinct forces, two concrete reward owners, two completed commands/cleanups, then original save lifecycle to Complete.
- `save-first`: reward denied during Save; after Save completes two rewards execute.
- `hold`: requested and actually observed suppressed User hold denies reward.
- `ready`: local final-prefix fence denies reward/save, real User suppression occurs, explicit release permits two rewards.
- `cancel`: queued command cancelled; no reward native body or list allocation.
- `cancel-running`: real second OS thread revokes during the synchronous body; list survives through return, cleanup completes, result stays uncertain and future work is denied.
- `wrong-world`: world pointer drift denies reward before its body.
- `wrong-binding`: generation mismatch denied at Submit.
- `exception`: explicit fixture SEH traverses actual PE FINALLY; resources are released, abnormal count is 1, uncertain is retained and further work refused.
- `worker`, `worker-b`: persistent stdin/stdout worker, different local viewer values, sample -> B reward -> sample -> A reward -> sample -> close. State stays live in each process. Both replay returns and cleanup evidence are true, with two semantic captures per command.

## Persistent owned worker protocol

From the final run directory, start a fresh fixture using an exclusive scratch directory:

```text
fixture.exe worker <scratch-directory> 805b99a02b65f91eccb5af2c74f014bd7bcc5195611779dca97fbd82aefd038e
fixture.exe worker-b <another-scratch-directory> 805b99a02b65f91eccb5af2c74f014bd7bcc5195611779dca97fbd82aefd038e
```

Keep `reward.dll` and `checkpoint_planning_hold.dll` beside the EXE. `worker` has viewer 12; `worker-b` has viewer 2. The latter does not simulate actual game menus, merely the explicitly different fixture viewer identity. These are self-owned native processes, not game clients. Each accepts at most 256 JSON lines; request grammar is a deliberately bounded JSON subset for the fixture, not a production parser.

```json
{"op":"sample"}
{"op":"reward","force_id":2,"district_id":2,"officer_ids":[101,264]}
{"op":"close"}
```

There is no stdout greeting. Each input produces one JSON reply. `sample` returns `ok`, `source="owned-native-fixture"`, and `sample` with:

- `date={year:203,month:8,day:11}`, `viewer_force_id`;
- `forces` in stable order, each with `force_id,district_id,city_id,ruler_id,gold,action_points,officers`;
- each officer includes `id,loyalty`.

The two initial forces are:

| Force | District | City | Ruler | Gold | AP | Officers / loyalty |
|---|---:|---:|---:|---:|---:|---|
| 12 | 11 | 19 | 666 | 83308 | 18 | 97, 759 / 80 |
| 2 | 2 | 13 | 500 | 20804 | 10 | 101, 264, 411 / 70 |

Ruler 500 is fixture data and is not the real Liu Bei identity. The effect double subtracts 100 gold per selected officer and one action point per command, then adds four loyalty capped at 100. It executes only through the actual new Owner/replay route. Sample does not edit world state. Viewer may be excluded only from an explicitly viewer-independent fixture comparison contract, never implicitly from a real full-world claim.

`reward` also returns `sequence,submitted,error,exception,uncertain,native_returned,args_released,owned_slot_cleared,capture_calls,native_calls` and the post-call `sample`. Those booleans come from the actual replay report. Callers must require `ok` and all relevant evidence, not turn any received JSON into an applied receipt. No native thread addresses are exposed or accepted. The root integration may compute a canonical digest from the stable semantic sample.

Full actual replies are retained in `worker/stdout.jsonl` and `worker-b/stdout.jsonl`. Initial B [101,264] reward produces gold 20604, AP9, loyalty74/74; the subsequent A [97] reward yields A gold83208/AP17/loyalty84 while B stays at its preceding result.

## Retained failures

- `20261008-190234-954110`: initial compilation failed because the Windows `min` macro expanded the fixture's `std::min`. Corrected invocation syntax; no production guard changed.
- `20261008-190312-773754`: reward completion was already correct but fixture assertions used the original User return magic for a deliberately suppressed User result. Save setup also omitted the required actual Game observation.
- `20261008-190412-797033`: added diagnostic evidence showed Save cancelled before scheduling because the fixture had not performed that Game observation. Added the same real Game boundary used by the upstream fixture; did not fabricate a receipt or weaken source checks.
- `20261008-190527-968903`: nine core cases passed before worker addition.
- `20261008-190735-361711` (see retained build directory): worker compile warning treated as error for signed/unsigned fixture loop bounds. Corrected unsigned constants.
- Final run above includes the two persistent worker cases and all nine core cases. Earlier failed artifacts remain separate.

## Reproduction

From repository root:

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<private archived research inputs>'
py -3 work/mod_research/a_reward_save_owner_test.py
```

Requires the frozen private `checkpoint_push_profile.h`, reward fingerprints and original PlanningHold DLL/import library. Tests create their own run directory and processes. Production source integration with the live bootstrap, runtime world/force sampling, UI refresh and actual two-client command synchronization remain unverified.
