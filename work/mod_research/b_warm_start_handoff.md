# B profile-aware single-bank startup

2026-10-09. Explicit successor to the frozen fixed-file `checkpoint_complete_live_start_v2.py` and its classifier. New sources are `b_warm_start.py`, `b_warm_start_support.py`, and `b_warm_start_acceptance.py`. This turn did not access a game process, Steam saves, the game UI or a debugger.

## What is connected

The new entry accepts a current PID, immutable file/date/faction profile, expected current ruler, actual local Steam DLL paths, and an exact full-factory build result plus its hash. It checks all source/private/generated/binary pins and the production DLL. Previous partial factory families cannot satisfy this gate. Default invocation only displays help; `--check` uses the read-only reader and gives no installation permission.

Explicit execution holds the already staged `svdexccSC03.s14` open against replacement/write, copies those exact bytes privately for the native precommit verifier, freshly captures this process's planning objects and storage interface, and builds the typed warm configuration. This entry does not replace a save slot. Staging remains a separate component, so a coordinator must establish its own correct file before calling this entry.

A durable PID/birth claim is written before remote control. The launcher loads only the pinned production DLL, verifies its loaded code/module ownership and typed description, then calls `InstallBWarmProfileOwner`. Actual original slots and page protections are observed before installation and again after reported retirement. An uncertain remote call is never retried or overlapped with Stop; its memory and DLL remain retained. Constructor rejection closes the process API handle. Known completed installation failures may request Stop, but do not force source restoration or unload.

The local file/directory lease is released only after any known-completed Stop request, but Stop itself is not native drain evidence. A failed run must preserve the staged file until normal process exit or a later separately proved drain. `native_drained` and `staging_reuse_authorized` remain false; `cleanup_stop_completed` does not grant either permission. The CLI cannot promise to retain an OS file lease after its own process exits, and the durable terminal claim must be honored by any future coordinator.

Completion requires the actual Owner, immutable Profile and Retirement reports, two increasing Owner sequences with the same accepted completion evidence, paired byte/lifecycle/identity/planning receipts, and six restored sources. The classifier verifies profile file size/SHA instead of the old fixed file. Identity receipt force/person pairs are native pointers; numeric ruler/force IDs are checked separately against a fresh final game snapshot. A success is `PASS_WARM_DIAGNOSTIC_LOAD_RETIRED`, not a room Ready or full-world equivalence assertion.

Successful retired modules are not stopped: their frozen receipts must remain available for future native handover. This **first-bank-only** entry does not authorize a second invocation in the same PID/birth. The next coordinator must consume actual native handover and fresh file/state evidence; deleting a claim or copying JSON cannot grant it.

## Developer usage, not a playable launcher

```powershell
py -3 work/mod_research/b_warm_start.py
py -3 work/mod_research/b_warm_start.py --check --pid <current-pid> --profile <local-profile.json> --expected-ruler <current-ruler-id> --file <already-staged-CC03> --steam-api <local-steam_api64.dll> --steam-client <local-steamclient64.dll>
```

The profile uses the exact JSON schema in `b_warm_profile_capture.py`; expectations are data, not remote execution permission. `--execute` additionally requires `--build <factory-result.json> --build-sha256 <exact-result-sha>`. It is a controlled experimental entry and has not been executed against the game. Only the specifically verified game and Steam module hashes are supported; accepting local paths does not imply arbitrary versions are compatible.

Candidate factory result: `b_warm_factory_runs/20261009-172050-464741/result.json`, SHA256 `d08889ffb8cdbf517c141e8b3b2a8e05d38374008cd7833a041713fb48720499`; production DLL SHA256 `c4b32383ff4b278a835277d4e36308d21b4169fce59083e2b275a65ef2d7650b`. All build inputs remain private and are rechecked; the public handoff is not a replacement for them.

## Boundaries and next work

- The full native factory/guard chain now has owned-process evidence; game menu, world reconstruction and file business in that fixture are explicit substitutes.
- The startup tests exercise build gates, codecs, classifier and polling with synthetic reports. They do not prove remote loading, actual menu reconstruction or hidden loading-screen presentation in the game. See the separate startup test handoff and public milestone evidence for exact results.
- Next connect two complete factory installs, actual native handover, staging and fresh sampling into one persistent coordinator. Then validate two legal newly generated game saves in the same B process.
- The room coordinator, rule withdrawal/reinstallation, next-period acknowledgments, full input exclusion and screen cover remain separate integration tasks. This script does not claim them complete.
- The old failed process must not be reused; its normal restart remains unconfirmed. This turn made no new manual-operation request and did not reset any old claim.
