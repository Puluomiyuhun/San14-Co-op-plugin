# B warm slot-63 file staging

2026-10-09. This module only stages verified file bytes. It does not load the game, establish B retirement, prove no native readers, or grant the next DLL permission. No actual game/Steam/current-save directory was accessed or changed. Parent owns integration and any later real authorization.

## Existing code and the concrete gap

`checkpoint_cc_stage.py` established slot 63 ↔ `svdexccSC03.s14` and same-volume publication, but hardcodes the original machine, fixed historical file and empty-target proof, imports live capture, and prohibits overwrite. It must not be executed as the new staging tool. `outputs/san14-link/checkpoint_journal.py` persists verified transfer bytes and a load intent, but does not install the native file. New `b_warm_staging.py` preserves the proven exact slot/name; it introduces neither another network protocol nor unknown filename mappings.

The first version requires an existing target and always backs it up. An absent target is refused; original empty-slot staging is a different workflow. Source bytes must have an explicit expected SHA-256 and exact integer size (no bool/float), at most 16 MiB matching the B profile limit. “Legal save” here means that a future upstream producer must deliver an actual verified A Save; the staging tool does not parse or certify game-format legality. Test payloads are synthetic owned bytes, not newly generated legal game saves.

## Default and explicit application

With no arguments, the command prints help and does not even open a directory. With source identity and target directory, it returns a read-only plan to stdout and writes no lock, intent or target. All paths are explicit absolute fixed-local-drive paths; no process discovery or default Steam path exists.

```powershell
py -3 work/mod_research/b_warm_staging.py --source <absolute-source.s14> --source-sha256 <64-lowercase-hex> --source-size <bytes> --target-directory <absolute-target-directory>
```

An apply call additionally requires `--apply --permit <absolute-local-authorization.json> --permit-sha256 <sha> --records-directory <existing-dedicated-local-directory>`. The authorization schema is strictly:

```json
{
  "schema": "san14.local-file-overwrite-authorization.v1",
  "nonce": "32 lowercase hex characters",
  "plan_sha256": "SHA256 of module canonical(plan)",
  "expires_unix": 0,
  "retirement_reference": "absolute path to independently obtained retirement evidence",
  "retirement_sha256": "SHA256 of that reference file"
}
```

Expiration must be in the next ten minutes. The reference is pinned as an **opaque local evidence reference**: its contents are not interpreted as a native permit. There is no boolean claiming engine exclusion. The trusted future coordinator must separately verify the genuine prior-generation retirement receipt, absence of all native file readers, source/profile/file binding, and explicit local authorization to overwrite this target. Creating this JSON by itself does not satisfy those requirements. The authorized local startup coordinator will generate this record automatically once integrated; this is not a request for the user to approve every period or handwrite JSON. No production authorization generator or live apply was run in this task.

## Transaction behavior and exact limits

Every path ancestor is opened without write/delete sharing; handles reject reparse objects, file hardlinks, traversal, alternate streams, network/device paths and trailing Windows name aliases. File identities include volume/file index, size and modification time; source/target bytes are hashed. Source remains open without write/delete sharing during application. The target is held without write sharing; its READ/DELETE sharing is necessary for the real `ReplaceFileW` operation.

A fixed target-directory lock handle serializes this tool. Existing lock files are retained and reopened exclusively; crashes release the OS handle. After acquiring it, the tool rejects any prior transaction files for the authorization nonce and rechecks source/target against the plan. It writes and flushes a one-shot intent, writes/flushes the incoming temporary file on the target volume, and verifies it byte for byte. Before replacement, it writes/flushes an independent old-byte archive and verifies that too. The OS then atomically replaces the target while producing an actual displaced-file backup. Both actual backup identity/bytes and final target bytes must match before `STAGED` is returned.

This is not a filesystem name compare-and-swap. An uncooperative process can use `ReplaceFileW` to exchange the target name between the last check and replacement. The tool checks the **actual displaced backup**, detects that race, returns `UNKNOWN_NO_RETRY`, and retains the planned old bytes plus the other writer's displaced bytes. It does not silently restore or erase either. This behavior was executed with a real competing thread and two real atomic replacements. It prevents false successful receipts, but cannot guarantee that no conflicting replacement ever occurred; the future coordinator's exclusive lifetime window remains necessary.

After intent creation, any failure is uncertain and not retried automatically. `replaced` records successful return of the replacement API; false is not a generic proof that a failed OS call had no partial effects. Every uncertain record requires explicit reconciliation, not deletion of the intent. One-shot history is scoped to the selected records directory and nonce, not a globally authenticated room claim. File hashing and flushed intent/bytes also do not make the complete sequence power-loss atomic.

Every result retains `engine_exclusion_proven=false` and `load_permitted=false`. Even `STAGED` must be consumed by the independent native loading coordinator, with its own fresh checks.

## Executed verification

`py -3 work/mod_research/b_warm_staging_test.py` only uses owned directories below the private archive. Final run:

- `b_warm_staging_runs/20261009-165120-566461/result.json`, **7/7 PASS**.
- Result SHA-256: `b80a7e2eaa2a4b6baf8cffb64f9b1266f9ddcaaee4dff70e083811b77184095b`.
- Production script SHA-256: `e8498061d8656777b499ee5a5ecd3cef8a86db8eaa3d134da1ee19b369a3a5a1`.
- Test SHA-256: `aaa6e2a0128f3d0a733c54cca1a097b4c5368002006e16f93e088138d01c1c43`.
- Both source identities unchanged; 53 generated private files have size/SHA pins, independently rechecked.

Cases: two successive atomic replacements and exact backups, with default-plan no-write check and duplicate refusal; wrong source/authorization hash and stale target; exclusive tool lock conflict; actual open reader withholding DELETE sharing; junction/hardlink/ADS/traversal rejection; actual open writer conflict; and competing atomic name replacement returning uncertain while preserving both histories.

Preserved runs: initial five-case success `164718-318087`; `164819-996591` failed only because the race fixture's `os.replace` was itself blocked by Windows sharing semantics, before any competing name swap; the fixture was corrected to the actual allowed competing `ReplaceFileW` path and seven cases passed in `164841-417467`. `164943-397092` additionally includes stricter directory sharing and fixed-local-drive/name checks. Final `165120-566461` aligns the 16 MiB B-profile limit and rejects boolean/floating sizes, with these assertions added inside the existing hash/bounds case. No production safety check was weakened.

Next integration is the real B coordinator: verify first-generation retirement/no-readers and explicit slot overwrite authorization, stage each verified legal A file, consume the staged identity in `b_warm_profile` configuration, then permit the new isolated DLL load. This module is ready for that file-operation connection; it does not replace the missing native lifetime evidence. No new user game operation is required by these offline tests.
