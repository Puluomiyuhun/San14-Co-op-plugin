# Warm completion at the existing TLS room boundary

This successor connects existing room checkpoint delivery to a local warm-load coordinator and returns a **diagnostic completion ACK** over the persistent authenticated control connection. It does not call `PeriodCoordinator.loaded`, invent a world hash, advance an epoch, stage into Steam, invoke a native loader, or grant Ready. No game process, Steam file, or UI was accessed in this work.

## Integration surface

Use `b_warm_room.WarmRoom` in place of `CheckpointRoom` when creating the host's existing TLS server. Its ordinary publication path remains `FreshSaveBinding`: bind the retained local A `ASaveClient.wait_artifact` provider, reserve the actual Scope/request before Save, and call `binding.publish` with the existing trusted local observation. This module does not replace that native provenance check. In particular, loading a historical artifact file is not an authenticated A provider.

On B:

```python
received = receive_staged(
    control, connect_download,
    checkpoint_id=checkpoint_id, scope=scope, epoch=epoch, period=period,
    cut=cut, attachments=attachments, directory=new_private_directory,
)
# received.file is a verified private world.s14, NOT a Steam slot or load permit.
# The trusted local coordinator performs approved staging/profile/native load,
# deep receipt acceptance and native bank retirement using its own interfaces.
reply = report_warm_completion(
    control, received,
    profile_sha256=validated_profile_sha, receipt_key=accepted_receipt_key,
    attempt=actual_attempt_uint64, pid=actual_pid, birth=actual_birth_uint64,
    loaded_date=actual_planning_node, viewer_force=actual_force,
    viewer_ruler=actual_ruler,
)
```

`connect_download(token)` creates the existing certificate-pinned `room_transport.Client` with method `checkpoint_download`, using the separate download listener and the same room profile. The helper consumes and closes that connection. The persistent `RoomConnection` retains its original control connection/heartbeat. Each new private directory contains both checkpoint parts, the immutable context, and a real SQLite `CheckpointJournal` reopened and reverified before exposing the file. Warm profile's 16 MiB limit applies before transfer. Scope, epoch, period, cut, part sizes and hashes are checked by the existing receiver and journal.

The completion call must follow the local coordinator's deep native validation; function arguments are not a substitute for that validation. Its output fields match the coordinator's attempt/profile/file/receipt/date/identity data. `attempt` and process `birth` travel as canonical decimal strings because they are uint64 values beyond the existing JSON safe-integer range. B writes a durable send-intent before sending; a lost reply disables another call on that received record. This is not automatic restart recovery or cryptographic native attestation.

A verifies the sender is its current B connection and the diagnostic references the exact current checkpoint, Scope, epoch, period, command cut, file hash/size, saved date and B force. An identical packet is an idempotent diagnostic duplicate; conflicting or stale packets are rejected. `status.state.warm_completion` exposes `GUEST_REPORTED_WARM_COMPLETE` with all gameplay, world, Ready and next-period permissions false. An existing local load intent is allowed: the separate download gate intentionally closes once such an intent exists, but that must not prevent reporting its eventual completion.

## Why this does not release the next turn

The original `PeriodCoordinator.loaded` requires a loaded-world digest under its explicit state contract and a fresh matching A observation. The warm loader currently proves the loaded bytes, native lifecycle, restored B identity and planning return, while its own acceptance explicitly says `full_world_verified=False`. A save-file SHA cannot silently become the required world digest. The new ACK therefore leaves the old coordinator reconciling. A future explicit controlled-test policy or an actual matching world observation must resolve that boundary; this module does not introduce a downgraded playable-room protocol.

## Executed verification

Run `py -3 work/mod_research/b_warm_room_test.py` from the repository. It uses private temporary directories and owned loopback TLS listeners, with no process discovery or native calls.

Final result: private `b_warm_room_runs/20261009-181123-252515/result.json`, **3/3 PASS**, SHA-256 `30a8a1902eb41fa4f8ac79c2c78012fdcea93ce120e5d13aec813603b88aea3b`. Thirteen repository Python sources and 27 private generated files are pinned. Raw unittest output remains in `test.log`. Earlier passing run `181032-730303` is retained; no failed run was discarded.

- Two actual TLS deliveries use the real `FreshSaveBinding`, receiver and reopened journal; both warm diagnostics are visible through A's actual control connection. Native A artifacts/world observations and B load completion are explicit test doubles. The test uses the existing **explicit `complete_model` only between deliveries**, because the first diagnostic ACK demonstrably cannot advance the room. This is not two real native saves/loads or two-client gameplay.
- Wrong sender, Scope, epoch, file, force, integer type, process identity range, stale generation and conflicting receipt are rejected. An existing load intent still accepts the matching diagnostic without completing that intent.
- Changed local bytes cannot be reported; a request delivered over actual TLS followed by simulated local reply loss is recorded once and cannot be resent through the helper. No Ready is granted.

Source hashes: `b_warm_room.py` = `71e32a9e2eeba9476268a831fc41e0903ced10a1fcab5552bd1fcdc7b56e2c44`; `b_warm_room_test.py` = `6c8fd346f0c33bbb8f4c45fe83c4d390f8017837e54395986e41c6737ecec6a8`. No existing frozen source changed. Public docs, integration and Git belong to the root agent.
