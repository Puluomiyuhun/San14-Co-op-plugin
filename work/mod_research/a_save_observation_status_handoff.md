# A normal Save observer: shared DR6 ownership repair

2026-10-08. New successor only; frozen `a_save_observation*` files were not modified. No game/process discovery, Steam, UI, current saves, live preflight/record or Git operations were performed. All test debuggees and recorders exited. There is no pending user operation.

## Why this replaces the former next-step observer

Review of the new menu observer found an inherited cleanup gap in the frozen normal Save observer: it compared DR0–DR3 and DR7 but did not distinguish foreign DR6 event bits before restoring the original registers. Matching breakpoint addresses did not prove ownership of BS/BD/BT or a multi-point event. Therefore the old normal Save recorder must not continue to be recommended as the current live entry.

`a_save_observation_status.cpp` now uses the same corrected debugger core as `reward_menu_observation.cpp`, with only the descriptive comment and the two payload/binding includes changed back to the normal Save versions. The production source is explicit and independently compiled. A source-composition assertion checks this exact difference on every build. It directly includes the single shared `reward_menu_observation_debug_status.inc`; no second ownership predicate was reimplemented.

The guard treats DR6 mask `0xE00F` as ownership, not reserved bits:

- Initial thread admission refuses nonzero event bits before arming or clearing them.
- Cleanup permits the original event-bit state.
- A differing state must be an exactly recognized currently delivered owned debug event, or match a previously frozen pending-owned RIP/layout/DR6 snapshot.
- A caller boolean or a map entry containing the thread ID is insufficient: the shared guard verifies `ownedTrap` again and checks exact pending identity.
- Foreign status is logged as `cleanup_foreign_debug_status_retained`, retains the debugger/pending event or suspension, and does not overwrite it. The launcher marks that event incomplete even if another later record looks clean. It never kills a retained recorder to meet a timeout.

Original raw Save/worker payload, fixed anchors, process birth/EXE/User checks, real-debugger cleanup/queued-event drainage and Save/worker pairing remain unchanged. The existing strict register readback remains; this change does not normalize event bits away or weaken restore checks. It does not write game memory, submit a Save/Load, suppress gameplay, or prove producer drainage.

## New launcher and identity

Use `a_save_observation_status.py`, not the old launcher. It has independent `san14.a-save-observation-status-*` schemas and pins the exact successful build's complete 20-source set plus the production observer EXE. Sources include the shared guard, shared status fixture, menu core and its compiled fixture dependencies.

Default invocation is help only. Both CLI and Python `preflight` API require an explicit positive integer PID before importing the game reader; no implicit discovery is allowed. `--record` additionally requires the exact passing `--tested-build`, and performs preflight before attaching the observer. The recorder repeats birth, executable hash, fixed anchors and formal User checks. These live branches were not invoked in this development task.

This still targets the supported Zhang Lu slot34 planning baseline. It is a manual normal Save observation, not an autonomous save producer or production installation. A clean timeout without Save remains inconclusive; worker-overlap/no-overlap classifications never authorize a save or full world state.

## Reproduce offline

```powershell
py -3 work/mod_research/a_save_observation_status_test.py
```

MSVC uses the existing VS2022 Community path. This runner compiles normal/fixture observers and launches only owned test children. No private runtime archive, game installation or current save is read. The default-help and invalid-PID checks exercise only non-accessing branches.

Final result:
`a_save_observation_status_test_runs/20261008-202814-533972/result.json`

**39/39 PASS**, all 20 source fingerprints unchanged and independently rechecked:

| Layer | Cases | What actually ran |
| --- | ---: | --- |
| Debugger | 9 | Owned real process/threads: ordinary hits, timeout, cancellation, wrong birth, production rejection of fixture, preexisting foreign breakpoint, propagated exceptions, adaptive layouts and pending-owned cleanup/error |
| Save/worker semantics | 12 | Frozen native decoder using owned memory and explicit CONTEXT models; no real game Save |
| Launcher lifecycle | 12 | Complete/empty/partial/lost/limit/foreign-status log models, all incomplete cases refused |
| Parser | 1 | Truncated final JSON refused |
| Launcher | 3 | Default help and explicit PID refusal, including API refusal before reader import |
| Source composition | 1 | Shared repaired core plus unchanged Save payload and semantic fixture |
| Shared status guard | 1 | 26 internal checks: nine actual OS Set/Get roundtrips and seventeen explicit CONTEXT ownership models |

The OS roundtrip detail is essential: on this Windows build, SetThreadContext on the ordinary suspended owned thread cleared all requested nonzero DR6 event bits. The actual count `nonzero_event_bits_retained_by_os` is **0**. The BS/BD/BT/multi-point and exact-owner refusal proofs are explicit CONTEXT models calling the production guard, not actual foreign hardware exceptions. The nine debugger cases separately supply real observation/restoration/queued-event evidence. Do not combine these layers into a claim that an actual foreign BS/BD/BT cleanup event was induced and handled end to end.

- Result SHA256: `ab59987ee5b246d02ec5d7146e3582a0dfc8b76697aa79e53708c316a9e1e855`.
- Production observer SHA256: `e932b0881b9beb9a79bfe9e4b09ce418a91a5cccdcd1d09ada24898ccd21f796`.
- Fixture observer SHA256: `1e1f069fc7f9a303b6f2e6ea0da6c5e05937f10c2dcc50d28d1d0a485f93ae5e`.
- Shared status fixture SHA256: `62bbf24ef017b6fba0f85f58349dfa492d4d03e33aeb5bf01d001cca38af6b68`.
- Semantic/debuggee fingerprints are recorded in the result alongside the full source manifest.

This successor's first complete test run passed; no failed run was deleted. The earlier shared menu status-fixture run that incorrectly expected Windows to retain requested DR6 bits remains in the menu observer's test history. The corrected shared fixture preserves raw observed values and states the model limitation; no production predicate was relaxed to satisfy that test.

## Next operational step

Root documentation should point the next normal Save observation to this successor and its exact passing build. When the user is available, first review the current process identity and explicitly run the new preflight; only after the new recorder reports READY should the user perform one normal Save. This document is not a request to run it now. After any incomplete/retained cleanup, do not kill the recorder, claim successful sampling, or reuse the observation as a save permit.

A real normal Save record, full writer/input exclusion, actual two fresh game saves and cross-turn lifecycle remain unresolved. This change repairs diagnostic ownership; it does not advance those production capabilities by assertion.
