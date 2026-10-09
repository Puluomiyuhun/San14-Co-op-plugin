# Two-period received/apply/projection joint check

2026-10-09. This joint test connects the real Python protocol and file-receipt components in one retained room. It does not access SAN14, Steam, game UI or another process, and does not install hooks or start a debugger. No new user operation is needed. The earlier real-game shutdown uncertainty is unchanged.

## What is now combined

`b_warm_joint_test.py` retains one actual `WarmRoom`, `PeriodCoordinator` and `FreshSaveBinding` across two checkpoint transfers. Each iteration executes:

1. The coordinator seals the modeled command prefix and enters its actual `RUNNING` state. The new top-level `host_observation` reads the declared two-table projection independently of the save file/profile, before reservation and again before publication.
2. `FreshSaveBinding` verifies the explicit A artifact double and publishes through the real TLS checkpoint service. B downloads through the existing pinned TLS client, Receiver, and durable/reopened Journal.
3. `TrustedProjection` reconstitutes its Receiver from B's actual Journal bytes, samples the authority, invokes actual `received`/`begin_guest_load` and persists the actual Journal reservation.
4. `ReceivedApply` consumes that exact reservation, persists its separate once-only local intent, invokes the explicit bridge double, pairs its completion to the local process/profile, and saves a partial world sample through its optional `sample_loaded` callback. Its actual TLS diagnostic ACK reaches A while the formal Journal is still `INTENT` and the old period remains active.
5. The projection adapter samples both sides under the explicitly modeled boundary, compares the declared contract, commits `Journal.complete`, and calls actual `Journal.apply_to_coordinator`/`PeriodCoordinator.loaded`. Only then does the protocol rotate its epoch and B attachment and enter the next planning period.

This succeeds twice: protocol period 1 → 2 → 3, with two distinct checkpoint IDs, two persisted `COMPLETED` Journals, two fresh B attachments, two native-double invocations, and two actual coordinator replacement trace records. There is no call to `complete_model`. Existing room selection, fixed scope and retained A save-binding history stay intact between the two transfers.

The manifest declares exactly `san14.partial-world.object3001-force52-date.v1`. Its legacy `world_sha256` field is the canonical digest of that named partial projection, **not** the save-file SHA or a full-world hash. The test explicitly checks that it differs from the file SHA. Ready/full-world/native-gameplay/fence-release flags stay false. The next loop's modeled Ready/seal calls are fixture activity, not authority derived from the ACK or a native game permission.

## Substituted dependencies and remaining limits

- Save artifact bytes and native completion evidence are explicit models. The profile knows those fixture bytes before the modeled Save; production A observation no longer requires a future-file profile.
- `BridgeDouble` substitutes all native load/rules business. It returns the actual expected nested completion shape and paired PID/birth; there is no `Resident.load` or publisher execution in this test.
- This successor adapts the reused double's older two-argument preparation callback to the real `prepare(expected)` single-argument convention and checks the observed placeholder passed to it. The frozen six-case apply test retains its old `(request, observed)` double convention; that is not the production API. `ReceivedApply` transparently forwards callbacks, and the real native rules/lifecycle combination was tested separately.
- Full fake memory implements all 3001 object slots and 52 force slots. The actual sampler/canonicalizer reads them repeatedly, including separate A/B addresses and viewer identities. Only fake memory dates are changed; no game date is written and no battle is simulated. This does not prove that native loading reconstructed the fake tables.
- `verify_held` and guest safe-boundary callbacks are explicit true-valued doubles. They are not native input or writer exclusion evidence.
- A and B are actual separate TLS control connections but share one test-process coordinator. There are no two real game clients or remote PCs.
- The declared projection does not cover persons, armies, cities, tasks, RNG, events or the full shared world. Advancing this explicitly limited protocol contract is not approval for full gameplay. The output continues to deny Ready and full-world coverage.

The earlier six-case `b_warm_received_apply_test.py` remains frozen. Its handoff correctly says that optional sampling was not combined in those six cases; this later joint check now executes that branch without rewriting the old evidence.

## Reproduction and evidence

```powershell
py -3 work/mod_research/b_warm_joint_test.py
```

Final private run: `../mod_research/b_warm_joint_runs/20261009-185112-332808/result.json`.

- Result: PASS; one joint success case contains both complete protocol periods.
- Result SHA-256: `2c89576635277e53bf0ab714f46088ade5113dd339dca3e9d71e6fdb9cb42d08`
- Test source: `d9a8ec2ef6233f0fa87718cb7e59d7db45c3a4aebe029ee49966471487e7663b`
- Projection source: `c75de6b32c536a9824bbcea987a2f1197391af7d74ec8e8c760da44c3501a4e6`
- Received apply source: `4bd5fcf9bf9e7df398e08911606618ae70e77777f831be2d038c4f4d1e31917d`
- All 26 Python sources and 19 private output artifacts independently rehashed unchanged. TLS credentials, fixture files, SQLite Journals, and local completion/sample/ACK records stay private.

Retained failure: `20261009-184757-359936` failed before publication because the in-progress projection API had moved `host_observation` from an instance method to the top-level file-independent function. The new test was adapted to the final interface; no production guard was weakened. The final run used `receiver_from_journal`, so B does not need A's package object to reconstruct its validated receiver.

Intermediate `20261009-184815-721829` also passed both periods. `20261009-184952-748380` then passed after the projection source added exact room build and before/loaded date checks. Both are retained; the last run additionally applies the narrow preparation callback adaptation above. No production guard or completion logic was changed for that fixture correction.

The next useful integration is a retained real B owner supplying the actual rules/warm bridge, native fence and fresh reader to these existing interfaces. That must still be validated in one game lifecycle and then across both PCs; these Python results do not authorize reusing the unresolved old game process or replaying native load intents.
