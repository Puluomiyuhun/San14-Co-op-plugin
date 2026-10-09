# B observed-boundary formal completion (2026-10-10)

`b_observed_completion.GuestCompletion(session).apply(received, request, profile)`
closes the formal-completion seam left by `b_remote_session.py`. It uses the new
`observed_completion_contract` action/domain and `a_observed_room.ObservedRoom`,
not the frozen strong-held protocol. No old source was changed.

## Actual path

The constructor accepts exactly one fresh actual `Session`, retaining its key,
TLS connection and native graph. Apply locks both owners, checks the Session's
typed received file, SQLite journal, source pins, native incarnation and current
period/attachment lineage, then obtains a new typed planning observation.

The sequence is: exclusive durable signed-begin record → authenticated begin →
validate A's finite observation and exact intent → `Journal.reserve_load` →
another real B observation → the same `Session.apply_native` → original native
completion and full declared-table sample checks → another typed observation →
`Journal.complete` → exclusive durable signed-completion record → authenticated
complete → validated authority response/progress → retained next-period lineage.
The unchanged Session owns refresh, rules rebinding, native retirement and bank
handover; the new Guest owns formal receipt delivery. Session's original local
status still says it did not itself send a formal receipt; Guest status/history
records the actual formal completions separately.

Before/after observations bind the exact checkpoint, wire epoch/period, native
profile, PID/birth, sequence, sampled date and player. B's after-observation uses
the legitimately transformed current-view profile from the frozen Session
(before=loaded, currentForce=target), while the envelope separately retains the
original native profile hash. A replies must retain one PID/birth and strictly
advance sample sequence. All boundary envelopes preserve explicit human
no-new-commands=true and input exclusion/scheduler fence/atomic snapshot=false.
Formal completion does not grant Ready, enable gameplay, or claim full-world
coverage. The legacy Journal `safe_boundary` field is interpreted under this
explicit finite-observation contract; it does not stand for a held engine lock.

Failure is terminal for Guest and Session. An unknown/lost begin response may
have consumed A's intent, and an unknown/lost complete response may already have
advanced A. Neither is retried; native loading is never reissued. Objects,
exclusive files and SQLite records remain. No hidden Stop, Revoke, unload,
disconnect/reconnect, native reset or permission relaxation occurs. A secondary
error writing the failure record is attached without hiding the primary error.
Exact duplicate receipt handling on A is an idempotent protocol response only;
Guest does not automatically resend or reconstruct after failure.

## Combined validation

```powershell
python work/mod_research/b_observed_completion_test.py
```

Final private result:
`../mod_research/b_observed_completion_runs/20261010-003948-526128/result.json`

- **5/5 PASS**; SHA256
  `114960f9cf85a3d5ab2f3c031f1edec550d115de21b0b0cdd0b03edbc81485cb`.
- 76 actual imported source pins, 71 private artifact pins, all rehashed against
  current files; `inputs_unchanged=true`.
- One joint case executes actual `ObservedRoom`, `ObservedFreshSaveBinding`,
  `BootstrapCoordinator`, `RoomTurnControl`, TLS transport, SQLite Journal,
  A's new `AObservedBoundary.observe/world_observation/sample`, B's unchanged
  complete planning algorithm, the retained `Session`, actual rules transition
  predicates and the new Guest formal completion.
- Observed order is `submit-1 → loaded-1 → sealed-turn → request-next → submit-2
  → loaded-2`. First loaded remains **203-08-11**, clears Ready and requires real
  Ready/seal/begin messages. Second becomes **203-08-21**. The same B Session,
  Resident, lifecycle and bridge remain, with two banks and three rule module
  generations. Both Journals become COMPLETED through signed formal messages.
  No `run_model`, `complete_model`, old strong adapter or `verify_held=True`
  drives this joint path.
- Lost begin reply: A has an intent, B journal remains STAGED, **zero loads**,
  Session terminal, reconstruction/replay rejected.
- Lost complete reply: A has advanced to period 2 at the same date, B journal
  is COMPLETED, **one load**, Session terminal and no second native attempt.
- Pending native-input field refuses before signed begin. A correctly signed
  false fence claim refuses before native loading. Exact old completion replay
  returns duplicate without changing the final period or issuing another load.

The game RAM, installed hook bytes, typed Runtime/Plans reports, native Save,
Load and rule publication remain **explicit owned-fixture substitutes**. A's
actual provider predicates and both sides' actual samplers execute over those
substitutes. TLS seats share one Python test process; there are no two running
games and no independent B OS process in this suite. Production `Session.open`
is not executed here. Windows temporary checkpoint files/leases, private key
protection and TLS are real; no game, Steam directory or UI is accessed.
All owned servers/handler threads/connections are joined/closed by teardown;
no installed native publisher or game process was launched.

Earlier `003639-412262` also passed five cases, but used an explicit A typed
observation fixture. It remains unchanged. The final run replaces that fixture
with the actual new A provider and includes the shared envelope's explicit
year/month/day checks. No failed run was discarded.

Frozen B sources:

| File | SHA256 |
|---|---|
| `b_observed_completion.py` | `7bff1e1e61e65bc4f00a76cdab0ea52d54e10bacdf9a60c3bacc14bc33dcbf9b` |
| `b_observed_completion_test.py` | `c32c8d8f04418ecd1e66e5ce3bce6d26c0047407d3af8b41713665b512d3b41b` |

## Next concrete step

Wire this pair of observed-completion ports into explicit A/B launchers with
approved native builds, fresh local process and source identities, the actual
private key and TLS configuration, and the established cleanup owners. Do not
describe the old local `a_native_turn_start` CLI or the test runner as that
two-computer launcher. The initial diagnostic budget remains two checkpoints:
same-day bootstrap plus one旬末 correction. This work closes the protocol seam;
it does not add a third native bank or continuous engine/input exclusion.
