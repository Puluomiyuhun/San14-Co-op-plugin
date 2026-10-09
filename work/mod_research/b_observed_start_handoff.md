# B observed startup and cleanup

`b_observed_start.py` is an explicit successor entry. No frozen Session, GuestCompletion, native bank, rules factory, lifecycle, or protocol implementation was edited. Import/default help performs no process access. No game process, Steam directory, or UI was accessed during this work.

## Entry and configuration

```text
python work/mod_research/b_observed_start.py --config <private-B-config.json> --check --no-new-commands
python work/mod_research/b_observed_start.py --config <private-B-config.json> --execute --no-new-commands
```

`--execute` is a live operation, not executed by this task. `--check` verifies local file/build/source/key identity and reads the explicitly configured game process; it does not join a room, create a claim, load a DLL, or call native code. Its temporary planning profile uses the actual existing target file identity, never a fabricated future checkpoint.

The exact configuration schema is `san14.b-observed-start.v1`, defined by `SCHEMA`, `LOCAL_KEYS`, and `validate_config` in the source. Top-level keys are `schema`, `network`, and `local`.

- `network`: the private invitation from `observed_room_service.HostService`; exact fields `schema`, `host`, `control_port`, `download_port`, `fingerprint`, `profile`, `credential`, `force_id`. Credentials are not printed or copied into results.
- `local.pid`, `birth`: explicit current process identity; no discovery or reuse of old claims.
- `target`: absolute `svdexccSC03.s14`; `initial_target`: exact `b_warm_staging.read_file` identity (`size`, `sha256`, seven-element `file_id`).
- `initial_node`: `year/month/day/phase=PLANNING_BOUNDARY`; `source_player` and `target_player`: exact `force/ruler/district` objects.
- `records`: a fresh private directory path; `adapter_key_path`: the separately provisioned protected local key. Only the key fingerprint is reported.
- `pair_build`, `helper_build`, `source_manifest`: each an absolute `path` plus exact `sha256`. Pair/helper validation uses existing strict approved-build closure checks. The source manifest must be a successful, unchanged run with `sources`, including the startup/completion/service/shared-contract successors.
- `rules_build`: `stage` and `publisher` paths; only existing fixed production hashes are accepted.
- `steam_paths`: exact `steam_api64.dll` and `steamclient64.dll` paths, with existing production identity checks.
- `rules`: the exact supported `human_rules_activation_room.rules(...)` object, whose digest must match the authenticated room.
- `wait_seconds`: integer 1–1800; `native_timeout`: integer 30–1800.

The callable interface is `run(config, link)` / `Runner(config, link).run()`, with the actual retained `GuestLink` supplied by `join_guest`. `main` checks before joining. The runner checks again before native preparation. The production path constructs the real GameReader and calls `Session.open` with all explicit bindings.

## Sequence and cleanup

The authenticated context supplies scope, attachments, manifest, epoch and period. The first offer must have the initial date; the second must be exactly the next planning node. First loaded leaves the coordinator at period 2 with its old manifest; the runner waits through PLANNING/SEALED/RUNNING and only consumes a matching RECONCILING offer. It never seals, advances, or sends player commands. It sends B's own `period_ready` only after the first known formal reply.

The same Session, GuestCompletion, rules lifecycle and two native banks remain retained throughout. Incoming bytes use actual TLS receivers and durable Journals. Both formal operations use the existing signed begin, local reservation, native refresh/load/retirement, partial world validation, Journal completion and signed complete path.

After two known formal completions, normal cleanup requires actual helper `finish`, current ResidentPort restore, full boundary observation, six original AI sources, no debugger and exact final target hash/size. Native modules stay resident. `sources_restored` is separate from `local_handles_closed`; only after both are proven does `native_cleanup_verified` become true. The single `pilot_guest_finished` notification is sent while TLS is still available. On the successful path B then samples the read-only `pilot_host_finished` barrier until A's native entry has returned and A explicitly calls `mark_host_finished`. Only then does B close the connection; A waits for that actual disconnect before closing its service. This prevents B's faster cleanup from disconnecting while A is still polling its second formal receipt. Neither message independently verifies the other process's native cleanup.

The close barrier uses the configured bounded wait. False replies may be sampled again; any lost reply is terminal, and a timeout reports INCOMPLETE without replaying either load or the finish notification. Existing native failures retain their primary error and do not wait for a successful host barrier. Those failure notifications already put the authority in HELD.

Any native failure, unknown publisher result, lost reply, or failed postcondition is terminal. The raised exception retains `retained_runner`, which retains the Session and native owner graph. There is no load replay, reset, automatic unload, kill, or optimistic restore. Failure logging cannot replace the original exception. If native preparation has not allocated a retained Session, its read-only GameReader is closed safely. Unknown/failed owners remain retained; normal game exit may be required.

The original target bytes and identity are backed up before any native work. **CC03 is never physically restored while the game is running**: doing so would recreate the proven Steam cached-metadata mismatch. Successful cleanup leaves the second checkpoint in CC03 and reports `target_file_restored=false`, `requires_game_exit_before_original_file_restore=true`. Restoring that backup after confirmed game exit is separate work.

## Verification and limits

The new tests execute the actual HostService, join_guest selection/confirmation, TLS control/download, observed Room, both Journals, same Session/GuestCompletion, full owned planning sampler and ResidentPort read/publish/readback predicates. A's actual finite observation provider reads owned RAM. The native Save/Load, Prepare/Seal/publisher, helper and process-memory environment are explicit doubles. Production `Session.open` is wired but its native installation was not executed here; no live end-to-end multiplayer claim follows from these tests.

Cases cover normal two-checkpoint cleanup, native load failure, final rules restore uncertainty, invalid configuration/preflight, preservation of the primary failure when logging also fails, process birth mismatch closing only the read handle, local handle close failure withholding a clean notification, and read-only check with actual private key/file/source verification. The actual HostService test delays A's explicit finish marker after B's cleanup and verifies that B remains connected. An absent marker must time out without any native replay. Neither an input fence nor full-world equality is claimed. A's own rule/AI coverage remains the A entry's independently stated scope.

Intermediate runs are preserved: `005935-568691` exposed string paths passed to the Path-only staging reader (and a test expecting the wrong missing-file exception); `005959-915687` exposed the inherited fixture's unrelated rules digest. Both were corrected without changing frozen implementations. `010048-177356` passed five cases; `010156-352070` passed seven before the final check-path case was added.

`010322-905937` preserved a further useful preflight failure: a source manifest omitted the Resident's lazy `b_warm_start_support.py` dependency. The new entry imports the delayed native support/API/ABI modules before approval, and the test manifest pins the complete Session-required closure.

Previous pre-barrier result: `b_observed_start_runs/20261010-010514-931159/result.json`, **8/8 PASS**, `inputs_unchanged=true`, 86 sources and 185 artifacts. Result SHA256: `8ed278e88696f5e56a4adb96ffae89864a81fc2413ecd6ffa6a64ef3447fbe20`. It is preserved. Root's subsequent combined-entry review identified the disconnect-before-A-poll race, so it is superseded by the close-barrier evidence below.

Final private result: `b_observed_start_runs/20261010-010911-672897/result.json`, **9/9 PASS**, `inputs_unchanged=true`, **86 sources / 225 artifacts**, all current hashes rechecked. Result SHA256: `c3caee7cf5fa24a9f3a13a530f20d9f615c7c0d8499fc66eb36817c4b15ef485`. Entry source SHA256: `364bcbb7ecc21149ab3a50a05f39c3b4fcab13aabe5a0919ac29c99f93250a9a`; test: `214c9de22a50653a431ed51cab8554c01c6bea0e37ea1da136782330ffcdd5da`.

This result can provide the B `source_manifest` approval input with that exact result SHA, subject to every pinned source remaining identical at startup. It does not replace the separate approved native pair/helper/rules artifacts. It pins the actual shared HostService used by the test and B's startup/completion closure. It does **not** claim to execute the A native launcher: A's separate native bundle/launcher checks and its source manifest are independent required evidence. The integration here runs actual shared service APIs and an explicit A owned-environment driver that calls the real host-finish marker after B reports cleanup.

All owned TLS listeners/handlers and test workers were joined/closed by teardown; no game process or native publisher was started. The test-only unknown native lease is released only during explicit owned-fixture teardown, never by the production failure path.
