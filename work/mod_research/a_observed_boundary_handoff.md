# A finite planning observation provider

`a_observed_boundary.py` supplies a retained read-only `AObservedBoundary` for the explicit no-new-command diagnostic contract. It does not open/discover a process, install hooks, call native control, retry a request, or claim a continuously held input/execution fence. Construction requires the actual approved typed `Plans`, runtime nonce, retained reader and typed `Snapshot` callback, exact PID/birth/base/root/world/cache/source identity, and the explicit human no-new-command condition.

## Callable interface

- `observe(node, profile=None)` returns a frozen `Observation`: sequence, PID/birth, actual requested date/source force/ruler, optional raw profile SHA, sample SHA, and explicit false coverage flags. A's actual date comes from `node`; B's `profile.before` is not used as A's date.
- `world_observation(node, attachment)` reads the complete existing audited 3001-object/52-force projection twice and returns the existing `LocalWorldObservation` shape for `ObservedFreshSaveBinding`. Its `safe_boundary=True` means observed idle planning in this explicitly weaker contract; it must not be wired into a held-fence contract as proof of exclusion.
- `sample(scope=..., epoch=..., period=..., profile=..., receipt_key=...)` brackets the existing `b_warm_world.sample` with full planning/runtime observations and preserves its exact sample schema, binding and partial-world completeness limits.

The provider reads both complete planning samples with repeat-read stability checks. It verifies actual object addresses, types, five-state stack, current/task pointers, queue consistency, pending input/transition fields, empty report tree/cursor, planning mode zero, root/world/cache, date/source viewer, four approved installed A slots and all three installed inline calls. Strategy/User addresses are re-read each time; they need not remain the old generation's addresses.

Both runtime snapshots must be successful, initialized/ready, inactive, error-free, non-stopped and without a host lease/frame or unknown mailbox entry. A previous save must have actual Complete, five phases, worker join, verified file and Delivered mailbox evidence. Parent pairs must have completed; seven bridge active counts must be zero. Host identity is fixed while counters/sequence may advance between snapshots. Explicit Snapshot result 10 raises `NotReady`; this is a refused read, not authorization or an automatic retry.

## Evidence and limits

Final test: `../mod_research/a_observed_boundary_runs/20261010-003644-592578/result.json`, **7/7 PASS**.

Result SHA256: `415a1d8e5191e6a3a4ed2fdf6d5d809d8ab7242c1c8d1bd82952939e145044f7`.

All 16 source, 4 archived-input and 3 output artifact hashes were independently rechecked against current files with zero mismatches. Provider SHA256: `08d25b2defc528ea121bb860d0b189b759a626af380f3809df608683c1e3cb9f`; test SHA256: `159a9b540c022df51a5be959d5e622c8dc85d351d816e299af3eb5cb3026de87`.

Tests exercise installed A hook acceptance, real typed report parsing, different A/B views with equal full audited projection, a new Strategy/User after a completed save, report/input/task/source drift refusals, busy/failed/foreign runtime reports, same-name object replacement races, and table drift. RAM and live callback behavior are explicit owned doubles. Four inputs are real archived Plans/Snapshot bytes from the successful two-save native-turn run `20261009-233736-417328`; its initial 016 Snapshot is accepted, busy 008 and stopped 172 are rejected. No game, Steam, current process, or current save was accessed.

The three production Plans inline sizes are each five bytes. The runtime's `runtimePublishHost` cache is one module-static object, not a per-Host pointer. Archived initial 016 and final stopped 172 have identical cache address `140717798224080` and host TID `37768`, sequence 38 to 2650. This is not a claim that a full Ready2 Snapshot was archived; the second-generation state test uses an explicit report double.

An active parent or snapshot race may conservatively refuse a read. Matching two reads is not an atomic snapshot, native input exclusion, scheduler fence, full-world verification, or permission to issue gameplay commands. All corresponding coverage/authority flags remain false. A retained production launcher still must supply the approved live reader/runtime callbacks and compose this provider with the explicit observed Room; this module's test is not a live installation or a two-machine completion claim.

The new root-owned `a_observed_room.py` and `observed_completion_contract.py` were also reviewed read-only: the distinct action/domain and enrollment reject the predecessor's strong action, profile/context/native-process checks are retained, and explicit year/month/day observations are checked against the manifest-derived date. The copied fresh-binding constructor states its limited boundary semantics; the inherited artifact/context checks remain intact. No additional blocker was found in this bounded review.
