# A native current-state scope composition

2026-10-09. Offline owned-process work only; this author did not access the game, Steam, current saves or UI. Frozen predecessors were not edited. Root separately performed the real parent observation; that evidence is not this fixture's output.

## Why this test was needed

The live parent sample observed manager `+48` as zero at the parent boundary. During an actual Game callback it is the Game state, and during User it is User. Earlier fixture bodies left it at User, hiding the original inspector's overly narrow User-only assumption. Writing the actual game's manager field to fake User is not a fix.

Root's explicit successors `a_save_scoped_input.cpp` and `a_save_scoped_gate.cpp` preserve previous checks, adding only scoped standalone acceptance and moving the already source-checked Game claim before layout inspection. `a_save_native_input_scope` authenticates the claim. Initial review found generic Parent ownership alone would also admit an idle gap inside the scheduler body. The adapter now exposes `CurrentBoundary(base)`, a TLS phase valid only during its actual Controller/Host before and after callbacks, with `__finally` cleanup. The scope helper additionally requires this exact boundary; original-body current zero remains rejected.

For Parent zero, all five formal state worker fields must be clear and actual User/Gate bridge active counts must be zero. For Game, the already authenticated Game bridge must have matching slot/token/thread/depth. Only Standalone inspection gains these paths. Other pending/layout/selection checks and User entry/after semantics remain unchanged. This does not prove all native writers are excluded.

## Executed composition

`a_save_scoped_input_test.py` derives a private fixture from the frozen `a_save_parent_adapter_fixture.cpp`; `a_save_scoped_input_fixture.cpp` supplies explicit scheduler-position models. The generated fixture sets parent current to zero, uses Game/User/Save self inside the corresponding actual callback, then restores the previous scheduler position on return. These are fixture writes, not production state repair.

Executed one normal period through actual ParentBridge → Parent Adapter → Host → Controller → scoped Gate/Inspector → actual Owner/Driver → Copy → mailbox/IPC. Original Save business/storage and parent source instructions remain owned doubles. The actual Scope helper and Inspector compile without fixture macros; executed Gate/Owner/Driver and Adapter retain the inherited fixture macros, while their production objects are also compiled. Those separate production objects do not replace the narrower execution coverage.

Three precise negative checks invoke the actual inspector: unclaimed current zero, an unrelated current state, and current zero inside the genuine Parent bridge's original body. All reject with Pointer. The authenticated before/after and Game paths complete one observation, Submit, Copy and host-thread release. Received diagnostic packet is decoded with the frozen Python decoder, validating generation/period, payload, phase mask 31, byte verification and worker join.

The previous fixture's second-period Retire/Rebind block was removed because it invokes Controller outside the new parent boundary. **This test proves one period, not consecutive periods or cross-turn coordination.** A future real cross-period parent schedule must execute those operations in the correct authenticated scope; no old success is relabelled as coverage for this new semantic contract.

## Evidence and reproduction

Final private result: outside repository `work/mod_research/a_save_scoped_input_runs/20261009-112428-899761/result.json`.

- Result SHA256: `7830111a09b5bdb140227eb76dc83b4dc56098d7473eabb521ab4a0367053191`.
- One normal scenario PASS, containing all three negative checks.
- 77 source pins, 41 binaries/objects, six generated sources/build files, three private inputs; all rechecked against current files, source unchanged.
- `112208-558276` is a retained compile failure: the new Scope helper accidentally called the Span `data` field as a function. Root corrected it; no guard was weakened.
- `112252-263707` is the retained first successful composition. The final run only adds explicit scoped-result metadata and the corrected test description.

Run `py -3 work/mod_research/a_save_scoped_input_test.py` from the repository. Private inputs remain in the established outside-repository directory, and all generated fixtures, builder diffs, raw output and binaries stay there. The generated builder explicitly substitutes scoped Gate/Inspector, adds the actual Scope helper, and links the real Parent bridge and adapter. No original source is mutated by the generator.

Final host/client/service processes completed normally; no active owned process/debugger from this test remains. No live publisher, game installation or production permit is provided by this test. Root owns public documentation and Git integration.
