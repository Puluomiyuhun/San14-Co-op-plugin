# Received checkpoint to retained local load and room diagnostic ACK

`b_warm_received_apply.py` connects existing `ReceivedCheckpoint`, `WarmRulesBridge` and `report_warm_completion`. It is a local callable, not a network handler, process finder or new native installer. The caller owns the already verified resident modules and actual input/execution fence. Native loading is still performed by `Resident`, on its existing native path; this adapter does not execute game business on a remote control thread.

```python
adapter = ReceivedApply(bridge, control,
    scope=scope, epoch=wire_epoch, period=period,
    attachments=old_attachments, on_hold=retain_native_fence)
result = adapter.apply(received, next_native_world_request, profile,
    observe_loaded=read_new_native_world, prepare_rules=prepare_fresh_rules,
    sample_loaded=None)
```

The stored TLS context, actual SQLite journal identity, fixed room scope/attachments, checkpoint ID, exact received bytes, native file profile, date and A/B force/district bindings must agree before any bridge call. The warm reader PID must match the rules module's PID. The rules PID/birth are retained and the resulting native completion must match them. A swapped process port cannot be accepted merely because its file or faction is correct. Native epoch and wire epoch are separate namespaces; `NextWorldRequest.epoch` remains the existing trusted lifecycle caller's native binding.

Before invoking the bridge, the adapter creates `warm-local-load-intent.json` exclusively and flushes it. It then calls actual bridge replacement, pairs the completion with the requested profile, native process lifetime and new rule generation, rechecks the received bytes, and saves `warm-local-load-completion.json`. The optional `sample_loaded(received, profile, completion)` callback must return the exact `b_warm_world` partial observation tied to that completion. Only then is the existing diagnostic ACK sent over the room control connection. Its date includes `phase=PLANNING_BOUNDARY`, unlike the three-field GameReader date.

The adapter is single-use. Any callback failure, wrong completion, dropped ACK reply or record-write error leaves it held and invokes the trusted `on_hold` callback. Hold callback failures are exposed as `hold_error`. The file intent remains after failure or restart; a new adapter reopening the same receipt cannot invoke the load again. Neither a file intent nor a Stop response proves native drain. The caller must keep the original native claim/owner and records; creating a different directory does not authorize bypassing native lifetime checks.

By default the formal Journal remains STAGED: a diagnostic completion is not a complete-world receipt. For the explicit projected-world coordinator, `apply(..., reservation=permit)` accepts a current local Journal INTENT only after reading and matching its persisted coordinator intent. The already-reserved caller must retain the true native boundary; the dictionary is never sufficient by itself. The successful return includes the actual `completion` for that caller to perform fresh observations and formal Journal completion separately. This adapter itself does not call `loaded()`, release input, grant Ready or advance a period.

The existing bridge requires B already viewing its target force and a matching resident bank sequence. This module does not solve bootstrap or create a third bank. Native completion dictionaries come only from the retained local bridge; shape checks do not independently authenticate arbitrary network JSON or prove native execution.

Tests and exact evidence are documented in `b_warm_received_apply_test_handoff.md`. All development this turn is offline or uses explicit test servers/fixtures; no game or Steam save is accessed.
