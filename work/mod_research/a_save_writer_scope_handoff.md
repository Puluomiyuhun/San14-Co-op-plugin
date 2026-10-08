# A native save writer scope — bounded archived evidence

Status: **17/17 offline audit cases PASS; no new live gate or production permit.**
This continues the frozen `a_save_upstream*` implementation. No predecessor, root
document, game process, Steam path, UI, or current save was changed or accessed.
No Git operation was performed by this agent.

## What this closes and what it does not

The remaining `509640` call before the upstream User cut is now classified on
the actual archived code. With an initialized manager and a warm thread-local
epoch, it only reads the manager stack and compares its last element to `this`.
The full native User entry returns before `3F9B16` when Save is above User.
The cold path must not be called read-only: actual `509060` initializes/clears
the manager. The stale-thread-epoch case uses an explicit CRT synchronization
double; actual CRT locking is not proved here. This closes the warm-path
uncertainty, not every possible singleton lifecycle in an arbitrary process.

Save on top of the state stack does **not** stop every other Update. The actual
`50B441..50B669` scheduler walk schedules Root, Motor, Game, Strategy, User and
Save in order. The fixture executes fresh pool selection, callable construction
sites, waits and completed-task cleanup. Callable storage and OS task services
are doubles; there are no actual game threads in this test.

One concrete background writer matters to checkpoint contents:

1. Actual full Game Update `3F8140` takes its non-top path while Save is top at
   phase 2, reaches `3F85DF → 16CB30`, and publishes an army worker as active.
   Thread construction/start are named doubles, not actual OS scheduling.
2. `B11E0` supplies global `1A24CF0`, whose archived RTTI is
   `ptr_list<CArmyUnitData>`. `16CB30` constructs worker `16C2C0`; that thunk's
   target is `16C1A0`. A separate executable VM case runs actual `16C1A0` through
   actual `2CD3E0`, with path-search/eligibility/list-cleanup doubles.
3. Actual `2CD3E0` writes army `+48` and `+1F8`. In the successful path fixture,
   those values become 102 and 108. In the unsuccessful path, `+48` stays 101
   while `+1F8` becomes `BD10`. These stores occur in archived instructions,
   not in the path-search double.
4. Actual `CArmyUnitData` serializer fragment `2133BD..2133DC` passes the two
   bytes at `army+48` into archived buffer writer `3A93E0`. Its memcpy service is
   explicitly doubled. The captured buffer receives 102 or 101 accordingly.
   This proves a shared serialized field; it is not a full serializer, archive,
   actual file save, full-world proof, or observed corrupted save.

By contrast, `15FAA0 → 16C2E0` belongs to **CTacticsEffectManager**, based on
archived RTTI. Its node countdown and related object lifecycle must not be
treated as an authoritative-world mutation merely because they write memory.
This audit does not add a gate for that display/effect subsystem, nor assert
that every transitive effect call is harmless. The other Game tail callees,
including `3AD580`, remain named unresolved boundaries in the executable case.

## Native Save coordination remains the preferred next investigation

Existing `checkpoint_push_native_chain_modes.py` already documents the normal
`508CA0 → 2EE740 → 2F7A10 → 2F7B50 → 2E7D30` path. This audit checks selected
additional archived anchors:

- The `root+85170` lock in `2EE740` is acquired at `2EE879`, **after** `2F7A10`
  has returned. This particular section clears the root error string, so it
  does not enclose the observed serialization call.
- `2E80EC` reads the global root, passes `root+7DF60` via `2E1680`, and the normal
  write loop at `2E0E20` dereferences each live army pointer before virtual `+28`.
  The immediate array loop is not a copied army snapshot.
- No enclosing shared lock/coordination has yet been established or exhaustively
  ruled out. Other preparation, native state callbacks, serializer descendants,
  and queue producers may provide coordination. Shared fields and asynchronous
  worker entry do **not** demonstrate that native saves actually race or corrupt.

Prefer proving/reusing the existing native save coordination. Do not infer that
a new global gate is mandatory from this evidence alone.

## Exact candidate ownership boundary, if extra draining proves necessary

`16CB30` has three observed native branches:

| Condition | Actual native sequence | What is established |
| --- | --- | --- |
| `+90 != 0`, not done | call `834460`, return with `+90` retained | pending worker does not join/start a replacement in this branch |
| `+90 != 0`, done | call `834460`, call `834BC0`, clear `+90`, return | native join-return precedes active-flag clear |
| `+90 == 0`, pending count > 0 | `16BB70`, construct `16C2C0` through `833CB0`, `834B60`, set `+90=1` | pending work can start on a later Game Update |

The tests execute the branch/store instructions; thread done/start/join are
doubles. They establish ordering, **not an actual OS drain**. Merely reading
`+90==0`, an empty queue, unchanged date, or unchanged reports is not a lease.

If native coordination is insufficient, the smallest concrete follow-up is to
bind the exact Game-owned `3F85DF → 16CB30` call and its native join-return
window, allow preexisting queued/working items to finish through their original
lifecycle, then prevent new starts for that same retained A Save generation.
Admission must come from that observed owner and exclude a concurrent producer;
it must not come from a caller-supplied `drained=true`.

The targeted direct-call byte scan found only `3F85DF` for `16CB30`, but found
17 candidates for `2CD3E0` including the worker's `16C238`. These are recorded
candidates, not a disassembly-level or indirect-call closure proof. Holding the
Game start source alone cannot be called complete army/world exclusion.

No new patch is installed this round. A future source patch at `3F85DF` lies
inside the Game body already validated by `a_save_upstream_gate`; it requires
one explicit owner successor with exact source normalization and combined
publication, not an unowned third patch. The existing A Save/report Owner must
reject admission until the real native sequence is established, and continue
to withhold production authorization for unresolved external writers.

## Run and evidence

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research'
py -3 work/mod_research/a_save_writer_scope_audit.py
```

Final evidence:

- `a_save_writer_scope_runs/20261008-173810-608475/result.json`
- Result SHA-256: `579b5b42c254479c486aef01f25db29c14e72d61aa87512508dd5df507da3490`
- Source SHA-256: `36885d10878f9ad5f80a3e8946c8895e020a50130b192c7fc46d20e5d4e56c05`
- Fixed archive SHA-256: `5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`
- Source and private archive are rehashed at completion and unchanged.
- Native instructions executed: warm/top cases 24–49 each; actual scheduler
  640; Save phases/poll/join 271; actual worker/path/serializer case 241;
  full Game below Save case 177. Static provenance and lock review are reported
  separately, not disguised as complete native execution.

17 cases cover warm User/Save/empty top checks, full User early return,
stale/cold manager lifecycle, scheduler order, Save pending/completion phases,
two path results and their serializer buffer, actual army worker-to-writer,
three army-worker lifecycle branches, full Game under pending Save, object
provenance/direct-call candidates, and bounded Save-lock review.

Failures retained:

- `20261008-173118-986960`: VM STOP address typo produced an unmapped return;
  fixed test stop placement, no native code changed.
- `20261008-173334-622526`: bounded CTacticsEffectManager range omitted its final
  `ret`; corrected the range end, without stubbing/skipping that instruction.
- Earlier passing evidence `173140-328817` (14), `173350-078700` (16), and
  `173613-872367` (17) remains; final run improves the scheduler fixture to use
  its actual fresh-task branch rather than preassigning a reused worker.

Pending operations: none. No recording, debugger, injected code, live hold,
save request, production permission, or background process was started.
