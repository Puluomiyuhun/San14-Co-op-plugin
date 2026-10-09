# Turn identity observation: missing addresses, not a simulation implementation

The old real-game records prove that the planning states leave and later return to the stack. They do not record their instance addresses. This small reader retains those addresses during a future already-planned native turn; it does not request another turn, advance dates, install hooks, or implement the missing advance integration.

## Existing real-game evidence reused

Private `lockstep-traces/rng-pairs-live-n/trace.jsonl`, SHA256 `694418cbb579ebd7792d3c0100bf0d2a5f2c97509e4eb58ce45cec36d7827cd8`:

| Line | Observed state transition |
|---|---|
| 5 | 203-08-11, Root/Motor/Game/Strategy/User |
| 41 | User replaced on the stack by OtherStrategy |
| 248 | Root/Motor/Game/Progress; Strategy also absent |
| 422 | 203-08-21, Root/Motor/Game/Turn |
| 439 | Strategy/OtherStrategy present |
| 1569 | Five-state planning User present |
| 1581 | ReportDisplay above User |
| 1584 | Five-state planning User again |

The two other successful real turns also retain only names:

- `human_rules_activation_live_runs/20261008-001113-003013/prepare-before.json` to `round-state.json`: PID 2904, August 11 to August 21; 120 AI entries/1044 income predicates. Before SHA256 `29dd0907195e8047caedfdf16b6b876cc2a788f62cef17e484d62bc860966138`, after `efbb593199d9bb6dfa696edc740e472d02d11635ddc29f3e8f03595fb562e655`.
- `human_rules_stage_live_runs/20261007-222556-471691/inspection-223353-188728.json` to `inspection-223937-475490.json`: same PID and dates, passthrough turn. Before SHA256 `9055c0fcf48289b228fe822bc61310e5452060d12198919d4f85358e5a314e1d`, after `4860465cc7bd917afae6f3ff2b57e2a887a770e485e9a72b3361cc8b21b15dd5`.

All 2211 state-bearing events in the retained lockstep `trace.jsonl` files contain name arrays, not instance addresses. The activation captures' `expected_user_hook` is a function address, not a User instance. Thread `stack_hex` is not the state-manager object array and was not interpreted as one. No claim that an object was newly allocated follows from these logs.

## New command

`a_turn_identity_capture.py` defaults to help without importing the live reader. Execution requires a positive explicit current PID. GameReader opens query/read-only process rights and checks the supported executable hash; there is no process discovery fallback, debugger, write, native call, remote transport, or UI action.

From repository root, alongside the next independently authorized normal-turn test:

```powershell
py -3 work/mod_research/a_turn_identity_capture.py --pid CURRENT_PID --capture
py -3 work/mod_research/a_turn_identity_capture.py --pid CURRENT_PID --watch 600 --interval 0.25
```

Replace `CURRENT_PID` with the freshly verified actual PID, never a historical value from this document. Watch begins before the already-planned turn and can span the ordinary report closure; it never tells the game to proceed. Do not use it to justify operating the unresolved old failure process.

Output is always outside the repository in private `work/mod_research/a_turn_identity_runs/<timestamp>/`. `intent.json` pins the reader and its two live-read dependencies. `samples.jsonl` preserves each accepted snapshot or rejection. `result.json` compares first/last accepted samples in a watch.

Each accepted sample contains PID, process birth, base, executable hash, root/world, date/force, each state's name/address/vtable/task pointer, manager current, stack address/count/capacity, queue address/count/capacity and bounded raw queue entries. It reads the entire shape twice and checks birth twice. Same-name object replacement, world replacement, date drift, queue changes or task changes detected between reads reject the sample. Watch retains rejected reads and continues so normal transitions are not mislabeled as stable observations.

Equal addresses mean only equal addresses: allocations can be reused. Double reads are not atomic, do not eliminate ABA changes, do not prove object lifetime or destructor execution, and do not establish a full-world or worker barrier. No permission to save/advance/restore is generated. Polling may miss short-lived states; rejected samples and gaps must remain visible.

## Validation

`a_turn_identity_capture_test.py` runs three pure fake-read tests: stable exact addresses/null queue, same-name different-address race, and world/date drift (two subcases). It does not import GameReader or open a process. Default no-argument help was also executed without opening the game.

Final private result `a_turn_identity_test_runs/20261009-150924-004496/result.json`: 3/3 PASS, both source hashes unchanged. This is reader validation only; no live capture was run. No existing game files, frozen modules or shared public documents were changed.
