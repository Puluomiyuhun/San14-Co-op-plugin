# B warm bounded stable planning capture

2026-10-09. This successor is read-only. No old module was edited and this task did not access the game process, Steam files, UI, or any native entry.

## Trigger and exact scope

The parent reported real run `b_warm_refresh_diagnostic_runs/20261009-215610-770741`: first native refresh/load completed with real retirement and released target lease. The second independent bank DLL was loaded and native Handover authorized it, but its subsequent planning capture raised `ValueError('Attachment/planning changed during capture')` before the second Install. This does not authorize replaying that terminated diagnostic, clearing its claim, or installing into it again.

The frozen `b_warm_profile_capture.capture_planning` requires two **complete equal** observations, including task pointers and the current scheduler state. Its last error also covers birth drift. A running but idle scheduler can therefore cause a read-only mismatch; the real record alone does not identify which sampled field changed. This helper does not pretend that the observed failure specifically proved a task/current transient.

New API:

```python
from b_warm_stable_capture import capture_planning
evidence = {}
try:
    planning = capture_planning(
        reader, profile, expected_ruler,
        expected_pid=retained_pid, expected_birth=retained_birth,
        evidence=evidence,
    )
finally:
    # Caller persists evidence to a new record, including on refusal.
    ...
```

The expected birth must be the retained owner's fixed incarnation, not a value reacquired to excuse a failed identity check. Defaults are three attempts, 0.75 seconds, and 20 ms between retryable refusals. Hard argument bounds are five attempts/two seconds/100 ms interval. It retries **only** an exact built-in ValueError with the original one-string argument; different messages, subclasses, wrong date/player, hooks, queues, permissions, or OS errors terminate immediately.

PID, birth, image base, supported game SHA and profile bytes are checked before and after every attempt. The fixed incarnation check separates the predecessor's birth-drift case from its generic mismatch message. Each attempt invokes the unchanged full sampler from scratch; an earlier sample/address set is never reused. A successful sample must still bind the same PID/birth/base/profile. No field is deleted from equality, no bool-ready substitute is introduced, and success remains `atomic_snapshot=false` with no installation authority.

The monotonic budget is checked before a new attempt and after every sample. A sample completing after the budget is rejected even if its two observations agree. The helper cannot interrupt an in-flight OS read; the budget bounds accepting/starting retries, not the OS call's execution time. It never retries Install, native FileWrite, loading, or any once-claimed native action.

## Reviewable evidence

An optional fresh empty `evidence` dictionary accumulates every attempt's start/finish timing, original exception type/text, whether the exact mismatch was eligible for another read, and the terminal status/reason. Failures also attach the same dictionary as `exception.stable_capture_evidence` where the exception permits attributes. It does not expose the predecessor's inaccessible unequal sample internals, so it does not claim to identify the specific transient field in a real failure.

No file is written by the helper itself; its owning coordinator must save this evidence on both success and failure. The parent is implementing that separate stable coordinator/diagnostic successor and approved-source binding. This helper alone is not a new standalone live entry point.

## Tests

`python work/mod_research/b_warm_stable_capture_test.py`

Final run: private `b_warm_stable_capture_runs/20261009-220004-423346/result.json`, SHA `d6cb178390febdab93e9f0b9dc67735595e360607c7b51016825e2a88d6ccffd`, **8/8 PASS**. No failed execution iteration preceded it.

The actual frozen full capture algorithm ran on its explicit fake-RAM Reader. Cases cover first-attempt current-field change followed by two new complete equal samples; changing task pointers on every sample until the attempt limit; wrong date with no retry; birth drift inside the original comparison; fixed expected birth mismatch before any sample; deadline expiry after an unstable sample; deadline expiry after an otherwise valid sample; and rejection of similar text/ValueError subclasses without retry. Timing tests use a deterministic clock substitute. No Windows/game process was opened and no native write/call was executed.

The result pins all imported local source modules and each per-case evidence JSON plus test log. The old sampler/profile/contract/test Reader sources are included. The source/artefact closure was rechecked after the run. These tests establish bounded orchestration while preserving the full existing predicates; they do not establish that the real second bank will now succeed or that the map is globally paused.
