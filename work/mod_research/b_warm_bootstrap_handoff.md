# First source-view load, then a retained B-view continuation

`b_warm_bootstrap.py` is an explicit successor to `WarmRulesBridge` and `ReceivedApply`. Frozen predecessors are unchanged. It starts with a real `WorldLifecycle` whose installed two-human rules still have `viewer=profile.source.force`. The warm port must belong to the same process and have its first bank available. This is not a rule-free game launcher.

```python
bridge = BootstrapRulesBridge(lifecycle, resident, target=cc03_path, records=private_records)
result = bridge.replace(request, profile, received.file,
    observe_loaded=lambda request: capture.capture_loaded(
        request, side='B', expected_ruler=profile.target.ruler),
    prepare_rules=prepare_new_native_rule_module)
```

The first call checks the current source-view Config and fixed human forces/districts, restores the old six rule sources while their world remains valid, stages the exact received bytes with a backup, and holds the actual Windows file lease through bank0 loading. Its result must pair to the retained rules PID/birth and exact file Profile. The observer then reads the actual new target world; only the first viewer transition source→target is allowed. Room identity, rules digest, game image, faction/district bindings and settings must remain fixed. A fresh resident rules module is prepared and installed under the existing trusted execution/input fence.

The original lifecycle retains old modules, nonces and history and adopts the newly observed B binding. The first result is retained as `completed[0]`, including its staged file identity. A second call uses the original strict same-view `WarmRulesBridge.replace`: the same warm instance opens bank1, performs its actual handover, verifies the prior file identity, loads and rebinds another new rules module. No once flag is reset, no module is unloaded, and no third bank is implemented. A first-load or second-precondition failure is terminal and invokes the retained hold callback; it does not restore an old file over an uncertain native reader.

The new `BootstrapReceivedApply` checks the real initial source viewer instead of copying a Profile with a fictitious target currentForce. The unchanged parent still handles the persisted local intent, completion validation, optional partial sample and diagnostic ACK. The initial STAGED diagnostic path is supported. **A first-call formal reservation is explicitly refused:** the old `CheckpointJournal` requires the guest already have B's target viewer before loading. That cannot truthfully describe the source-view starting point. A dedicated bootstrap journal/observation contract remains necessary before this first call can join the formal `TrustedProjection.loaded()` flow. Later B-view reservations can retain the existing policy.

The native epoch in `NextWorldRequest` remains a trusted local generation binding. `RulesWorldCapture` independently pins the room binding epoch and can supply the `observe_loaded` and `ResidentPort.export_current` reads. A production `prepare_new_native_rule_module(observed) -> ResidentPort` still needs to be extracted from the existing actual Prepare/Seal/publisher script path; the capture adapter does not supply it.

This module neither discovers or opens a game process nor issues a network-authorized native command. It requires the retained local owner, approved rule/warm modules and actual fence. Its return continues to deny Ready, input release and complete-world verification. For a minimal two-load diagnostic, the first load may combine the first received checkpoint with B identity selection; for a formal initial setup plus two later corrections, three loads are required and the current two-bank owner is insufficient.

The [six-case test handoff](b_warm_bootstrap_test_handoff.md) records the actual Windows backup/replace/lease operations and original `ResidentPort`/`WorldLifecycle` predicates. Native memory, publisher, loader and fence are explicit doubles, and the first-received diagnostic uses a control double rather than TLS. This turn did not access a game process, Steam files or UI; it does not add evidence that the previously failed game exited normally.
