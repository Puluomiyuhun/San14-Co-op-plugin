# Native refresh in the retained remote receiving path

2026-10-09. Successor of `b_warm_remote_owner.py`; frozen predecessors remain unchanged.

`b_warm_refresh_remote_owner.RetainedRemoteOwner` has the same constructor and apply API. Instantiate it with the new `b_warm_refresh_bootstrap.BootstrapRulesBridge` (initial A view) or `b_warm_refresh_rules_bridge.WarmRulesBridge` (already B view), the original B TLS connection and the actual retained WorldLifecycle. The provider load signature now matches the real-tested `b_warm_stable_refresh_coordinator.Resident`: independent received bytes plus target, previous identity and verified backup. Do not pass the old Resident expecting physical staging.

The new `b_warm_refresh_received_apply` preserves the frozen ordinary apply/completion implementation and exact bootstrap Journal validators. It adds native refresh/target lease completion checks. The owner preserves room scope, PID/birth, original object graph and guard, durable reservation, rules restoration/rebinding, world samples before and after advisory ACK, and formal completion. First source A to target B uses BootstrapCheckpointJournal; later target B uses the ordinary Journal. Replies do not release a native fence or enable gameplay.

File transfer still writes an independent private received file. The game target is no longer physically replaced or locked by Python across loading. New bridges back up exact old contents, pin independent source bytes, call the native refresh provider, require one publication plus old/new full double read and retirement, then check target contents and install the next rules generation. The native provider alone owns target write/lease. Failure after publication preserves both the backup and once-only failed state; it does not roll back or resend automatically.

This is wiring, not a standalone two-PC launcher. The strict real input/execution guard must still be implemented and supplied; a fixture callback is not an acceptable production replacement. Approved native builds, fresh local PID/birth and original-entry checks remain necessary. The previous real two-load diagnostic did not install these room rules or exercise TLS; the new offline integration does not turn it into a real remote result.

Run the following from the repository root (no game access):

```powershell
py -3 work/mod_research/b_warm_refresh_rules_bridge_test.py
py -3 work/mod_research/b_warm_refresh_remote_owner_test.py
```

The bridge tests execute actual Windows file identities, backups, source locks and real lifecycle predicates. The remote-owner tests additionally execute actual local TLS transfers, SQLite Journals, formal completion and the same retained two-period owner. Game RAM, rule publisher, native load and input guard are explicit doubles; two seats in this test share the Python test process. Physical `files.apply` is patched to raise, so any accidental fallback fails the test. The native double actually writes the test target while it is unlocked, holds a real deny-write handle during simulated loading, and releases it before valid completion. This is not a real Steam call.

Cases cover two periods, already-settled second correction, lost formal reply without replay, native failure retaining target lease, wrong PID birth, failed boundary guard, invalid refresh receipt without ACK/completion, and externally changed second target refusing before native load. The first six-case integration passed; the first expanded run correctly raised `files.Refused` but two tests mistakenly expected ValueError. Only those test expectations were corrected; production checks stayed unchanged and the failed run remains archived. Final run identity is recorded in the main HANDOFF evidence.
