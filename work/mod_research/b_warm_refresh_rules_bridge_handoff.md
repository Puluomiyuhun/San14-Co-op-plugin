# Rules replacement through the tested native refresh loader

2026-10-09. New files only: `b_warm_refresh_rules_bridge.py`, `b_warm_refresh_bootstrap.py`, and their dedicated test/handoff. No game, Steam file, UI, native publisher, or real process was accessed for this task. Frozen predecessors and protocol classes were not changed.

## Public interfaces and actual flow

`b_warm_refresh_rules_bridge.WarmRulesBridge(lifecycle, warm_port, *, target, records)` preserves the predecessor's replace signature:

```python
bridge.replace(request, profile, source,
               observe_loaded=observe_loaded,
               prepare_rules=prepare_rules)
```

`b_warm_refresh_bootstrap.BootstrapRulesBridge` uses the same constructor/replace and retains `validate_current_profile`. It exports no ReceivedApply class. The root agent owns exact protocol/RemoteOwner type adaptation and TLS integration separately.

The bootstrap class intentionally has MRO `NewBootstrap -> OldBootstrap -> NewWarm -> OldWarm`. The entire frozen first A-view to B-view rule validation and lifecycle sequence therefore remains intact. Its first `_load_first` uses the new loader; its second-generation `super().replace` reaches `NewWarm.replace`. The two-period test executes this dispatch rather than merely asserting a desired MRO.

The ordinary bridge still calls the actual `WorldLifecycle.replace`: old six-entry rules restore/readback -> load -> observe actual new world -> prepare fresh resident rules -> install/readback. First bootstrap retains the old explicit viewer change, same PID/birth, room/rules/settings, human district checks, unique resident module/nonce, and held failure behavior. No rule Revoke/unload or silent AI takeover is added.

Only the checkpoint file portion changes:

1. Construction pins the initial physical CC03 identity as a baseline. Before a replacement, read the exact current target and compare against that baseline or the prior completed target; save a separate verified old-byte backup.
2. Pin parent paths and the independent received source. Verify its exact profile size/hash and ensure its file identity differs from target. **Do not hold a target deny-write handle across loading.** Do not call `files.plan`, `files.apply`, or any target replacement operation.
3. Call the retained provider's `open_bank`, and for bank two its actual `authorize_second`. Call `load(bank, profile, raw, target=target, previous=old_identity, backup=backup_path)`, matching `b_warm_stable_refresh_coordinator.Resident.load`. That provider owns native FileWrite, original load/identity/retirement and its native target lease.
4. Correlate the trusted local completion to rule PID/birth, profile, factions, date/viewer and actual warm retirement. Require the refresh summary's one write, old/new full double reads, exact old/new size/hash, attempt/generation and clean released lease; independently read the newly published physical target and compare all bytes. Only then permit lifecycle observation/preparation/install to continue.

The bridge does not decode a peer JSON as native authority. The local provider remains trusted and is responsible for its deep native receipt verification; `check_completion` correlates its already checked return value. A user-provided arbitrary object with these methods is not thereby a verified native loader. Existing lifecycle guard/on-hold callbacks must still be supplied by the real owner; this module does not manufacture an input fence or grant Ready.

Return shape remains `WARM_LOAD_AND_RULES_REBOUND` with `details.rules` and `details.completion`; old staging details become `details.publication` plus old identity/backup. Frozen ReceivedApply consumes rules/completion, not a staging receipt. All readiness/full-world/fence-release flags stay false. Any refusal holds the lifecycle/bridge; a failed generation cannot be replayed, reset, or switched to a new DLL to bypass its state. Abort delegates to the retained provider, which suppresses Stop after completed retirement or unknown control; this bridge never releases a native target lease itself.

## Bounded evidence

Run `python work/mod_research/b_warm_refresh_rules_bridge_test.py`.

Final run: private `b_warm_refresh_rules_bridge_runs/20261009-221734-359458/result.json`, SHA `667923ebc2f30dd0f195e5a6dbdc3164b013dfb80ac56e3d5417a2f25eef0baa`, **6/6 PASS**. No failing execution iteration preceded it.

These tests execute actual Windows source/target files, identities, deny-write source leases, backups, the real `ResidentPort` predicates, and the actual `WorldLifecycle` plus bootstrap code. The memory samples, rule publisher, native refresh/load and input guard are **explicit substitutes**. Native load writes the actual test target, demonstrating there is no outer target read lock; this is not a new actual Steam or game-load result. Tests do not call any live script or create a debugger/background process.

- First A->B bootstrap then regular B-view replacement, with exactly restore/load/observe/install for both generations and a second-bank handover call. `files.apply` is patched to fail if called.
- Wrong initial viewer refuses before warm calls or target mutation.
- Modified initial target refuses before opening the bank.
- Native failure after publication retains the old backup and held state, does not install new rules, and cannot replay. Source remains deny-write pinned during abort.
- Second handover failure preserves the first target, leaves the owner held and cannot replay.
- Held target-lease or wrong previous-hash refresh receipt prevents new rule installation.

`WarmRefreshDouble` and `NativeRulesDouble` are reusable by the root's separate TLS integration tests. Their names and evidence explicitly distinguish substitutes from actual native authority; no fixture behavior is enabled in production bridge source.

Remaining integration belongs to the root: select the new bridge classes in retained RemoteOwner/ReceivedApply, preserve native factory/approved-build identities, and run its two-period TLS test. This change by itself does not demonstrate real rules-patched gameplay replacement or two PCs connected.
