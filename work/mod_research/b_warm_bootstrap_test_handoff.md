# First B-view bootstrap and retained second bank verification

2026-10-09. `b_warm_bootstrap_test.py` exercises real Windows file staging and the actual Python `ResidentPort`/`WorldLifecycle` logic with explicitly modeled native memory, rule publisher and warm loader. No game, Steam, UI, process memory, hook, debugger or network is accessed. No user operation is required by this test; the unresolved old game shutdown state is unchanged.

## Scope

The existing owned native fixture fixes `viewer=12` and has only two worlds (`human_rules_world_lifecycle_fixture.cpp`). It cannot express source 12 → target 2 followed by another target-2 world without changing that frozen fixture. This test therefore supplies a byte-memory and publisher double to the **unmodified actual** `ResidentPort` rather than substituting its type or methods. The actual port checks the Config, immutable descriptor, six source bytes, module binding and two active-counter fields before/after each modeled publish. `WorldLifecycle` and the new bootstrap successor execute their actual lifecycle checks, history, fresh module/nonce tracking and retirement. The bytes, counters, process identity and publish receipts are all models, not native evidence.

Temporary files are real. CC03 already exists, each replacement takes the real staging path, backups preserve exact previous bytes, and the load/abort callbacks actually attempt `CreateFileW` for writing. Windows returns sharing violation 32 while the loader's lease is held. Successful cleanup releases those handles; that does not prove native engine drain or allow reusing uncertain native work.

The starting state already has installed two-human rules in source view 12. This test does not implement a rules-free installation/bootstrap. It keeps the same warm object and actual lifecycle through bank 0 (12→2) and bank 1 (2→2); it does not reset or reuse a retired module. Three distinct modeled rule modules are retained, with the first two retired.

## Six final cases

1. First source-view load then next target-view load: exact warm order `open0 → load0 → open1 → handover1 → load1`, exact rule order install/restore/source then install/restore/target then fresh target install. Two real backups preserve the original slot and the first checkpoint respectively.
2. First native-double load raises after its modeled viewer changes: abort runs while the actual file lease blocks writers, no new rule module installs, and retry is refused.
3. First profile claims an already-target current view while installed rules are source-view: rejected before staging or native load.
4. Second-bank handover refuses: first checkpoint bytes remain, no second backup/load, and no retry.
5. Invalid second current-view profile sets both bridge and lifecycle `HELD`, invokes the hold callback, and a corrected request cannot retry that consumed bridge.
6. `BootstrapReceivedApply` consumes an actual chunk Receiver and reopened SQLite Journal. The source-view profile reaches the actual bootstrap/rules/file chain; the local control **double** receives exactly one diagnostic ACK. Local intent/completion/ACK records are persisted, the Journal remains `STAGED`, and replay is refused. A non-null first formal reservation is explicitly rejected with the specific source-view boundary error and zero load. No target-view pre-observation is fabricated to reserve the old Journal.

Case 6 deliberately performs its diagnostic call with a new apply wrapper after a pre-validation rejection that issued no native work. It is not a retry after uncertain execution; its bootstrap bridge is still unused and its external modeled fence remains held.

## Remaining gap

The frozen formal Journal requires B's target view before a load reservation. That contract cannot truthfully describe the first source-view bootstrap. The new bootstrap adapter therefore allows only the diagnostic `STAGED` path for its first load. This suite does **not** combine initial identity switching with formal `Journal.complete`/`PeriodCoordinator.loaded`, grant Ready, or claim a complete two-player opening flow. The later target-view bank retains the existing reservation-compatible path, but it is not a third bank or unbounded session.

Real `Resident.load`, native identity initialization, actual rules publication, native input/execution exclusion and game world observation still require a single combined game validation. A successful Windows file operation or modeled receipt is not permission to run them.

## Reproduction and evidence

```powershell
py -3 work/mod_research/b_warm_bootstrap_test.py
```

Final private result: `../mod_research/b_warm_bootstrap_runs/20261009-190111-161029/result.json` — 6/6 PASS.

- Result SHA-256: `4dcd97fb51bc6f544d939c59256f4884c5c346589b792613d42880c134c2cd07`
- Bootstrap source: `a764e83bcd4342a21d6a7576f0b236fe53579bd4d49284ad02715871c52b4812`
- Test source: `43edfa74ace595ea346ab558a07268df91a5520ac1654986ceb3d05f942861b6`
- All 21 Python sources and 65 private artifacts independently rehashed unchanged. No compiled product or owned native child was used.

Retained failures: `185838-241673` had two fixture failures because the initial warm double omitted the actual `accepted` completion shape; `190038-293614` rejected an unsupported fixture room adapter-contract string before any load. The doubles were corrected to the unchanged production contracts. Intermediate `185857-032996` (four cases) and `190047-563832` (six cases) passed; final `190111-161029` strengthens the first formal-reservation test to assert the specific rejection. No production validation was relaxed to pass a fixture.

An independent review also found second-profile validation originally occurred outside the successor's terminal hold handling. The root agent fixed only the new successor, and case 5 exercises that correction. Frozen old rules, staging, lifecycle and apply modules remain unchanged.
