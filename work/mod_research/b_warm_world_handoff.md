# Partial world witness for warm-load diagnostics

`b_warm_world.py` adds a read-only sampler accepting an already attached `GameReader`, plus a canonical comparison. It never constructs a reader, discovers a process, calls the game, writes memory, decodes a save file, calls `PeriodCoordinator.loaded`, or grants Ready. This work did not access the game or Steam.

## What existing coverage actually supports

`game_reader.py` supplies checked date/player/stack identity, not world state. The earlier `checkpoint_world_snapshot_reader.py` and `checkpoint_world_compare.py` intentionally cover partial archives. Their active person/army sampling omits inactive slots, task sampling lacks stable task identity and full raw fields, and discovered RNG values are not exhaustive. Additional economy/troops readers likewise enumerate specific observed dependencies, not a complete shared world. Those records cannot be relabelled as a complete world digest.

Two tables do have precise existing native-serialization field inventories: `checkpoint_world_coverage_extension_schema.py` defines all 3,001 physical `CObjectData` slots, eight bytes per slot at offsets `0x10..0x17`; `checkpoint_world_next_table_schema.py` defines all 52 physical `CForceData` slots and their exact ordinary version-92 field order. This sampler reuses those unchanged inventories. The contract `san14.partial-world.object3001-force52-date.v1` contains exactly those two field projections and the date. It includes slot zero/inactive slots, preserves physical order and opaque field values, and excludes no bytes from either selected inventory. It does not assume a native allocation stride or guess pointer-like bytes.

The force inventory originates in the ordinary version-92 archive audit. This sampler projects the audited memory fields; it does not establish the version/transform flags or contents of a supplied encoded save file. It also does not prove that every selected field is independent of player-view initialization in the actual game; a real difference remains a reported difference, never a new exclusion.

## Caller interface

```python
observation = sample(
    reader, scope=current_room_scope, epoch=checkpoint_epoch, period=period,
    profile=validated_warm_profile, side='A',  # or 'B'
    receipt_key=accepted_local_save_or_load_receipt_digest,
    read_birth=lambda: trusted_local_process_birth(reader),
)
diagnostic = compare(a_observation, b_observation)
```

Both sides use the same checkpoint/profile and saved date. A's actual viewer must match `profile.source`; B's must match `profile.target`, and each must match the room's fixed force/district binding. Scope, epoch, period, profile hash and the caller's local receipt digest are attached separately. The receipt digest is only bound, not interpreted as a new permission or verified by this sampler. The caller must retain its actual native evidence and attach the result only to that successful operation.

Each sample checks the approved game fingerprint, root/world RTTI, actual five-state addresses, process birth, date and viewer. It reads both complete tables twice, including pointer arrays and exact vtable/serializer slots, and rechecks context between/after passes. Repeated reads of the same native span must agree. This detects sampled drift, including the same state name at a different address, but is not an atomic snapshot, a lock, or a proof of object lifetime. `read_birth` must be the local trusted process-time reader, not received network data.

`partial_sha256` covers only the explicit shared projection; it omits process addresses, PID, viewer labels and receipt metadata from shared equality. No field is named `world_sha256`. `compare` validates payload coverage/digests and the context binding, then returns `PARTIAL_MATCH` or `PARTIAL_DIFFERENCE`, changed-byte/slot counts and bounded examples giving table, physical slot, native field offset and old/new byte. Even a match keeps `full_world_verified`, `atomic_world_snapshot`, `loaded_authorized` and `ready_authorized` false.

## Remaining coverage

Persons, armies, cities, districts, all hexes, tasks/commands, RNG, events, diplomacy dependencies, policies/traits and other world fields are outside this contract. Passing this comparison cannot satisfy an older, broader world contract or authorize the existing `loaded()` transition. The root coordinator can use it as an extra A/B diagnostic or rejection on a known difference; a match does not close the world/Ready requirement. A live A/B capture remains untested.

## Executed tests

`py -3 work/mod_research/b_warm_world_test.py` builds complete fake memory tables and exercises the actual sampler/comparer. Final private result `b_warm_world_runs/20261009-182758-911531/result.json`: **5/5 PASS**, SHA-256 `9b618158fc32a348629c35edce1490a2c285591e2c44cc13ba9f912fce324373`. Eight repository Python sources and two private outputs are pinned and rehashed.

- Different A/B viewers and relocated module/root/world/state/table/object addresses produce equal shared hashes for identical selected fields.
- Object slot 3,000 offset `0x14` and force slot 51 offset `0x164` changes remain visible with exact locations; no economy/business difference is masked.
- Mid-sample byte mutation, same-name state replacement, duplicate physical slots, wrong serializer target and date drift are rejected.
- Wrong profile date, foreign epoch, modified payload and false full-world claims are rejected.

First run `182737-021601` is retained: four tests passed; the wrong-serializer negative case used an unaligned target, so the earlier pointer validator correctly refused it before the asserted serializer predicate. The test now uses an aligned wrong target. No production check was weakened.

Source hashes: sampler `a9c6b6fe3233acc7fb4df074572a78776e63ea5789bdfa9f28d3b318cf08be3f`; test `5eaa406197b3699ad369c9129f8382e62dbd83d6f384d01c565d0557bfcb0df9`. Only new `b_warm_world_*` files were changed; root owns integration/public docs/Git.
