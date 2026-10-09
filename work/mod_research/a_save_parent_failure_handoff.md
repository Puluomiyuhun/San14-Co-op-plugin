# A parent initialization failure: bounded retained-object diagnosis

2026-10-09. This subtask compiled and executed only an owned layout helper and decoded local archives. The root agent separately performed the explicitly reviewed RPM-only observation described below. No native export was invoked for diagnosis; no old module was retried, patched, unloaded or given a new claim.

## Actual failure and exact location

Real run `a_save_runtime_live_runs/20261009-222056-638412` ended `INCOMPLETE_RETAIN_EVIDENCE`: the parent reported error 7, Host was not initialized, and Save generation/bind/queue/phase counts were zero. This was before IPC Submit, not another serializer or native storage error54. Stop and independent publisher restoration succeeded (mask127), post-preflight passed, and all 84 pre-existing saves were unchanged with no added file. The current lifetime is still consumed; successful source restoration does not authorize retrying it.

In the actually linked `a_save_runtime_publish_parent.cpp`, 7 is `a_save_parent_adapter::Error::Initialize`. Its `initializeHost` consists of Controller.Initialize, Controller.Request(true,1), Mailbox.Initialize, then Host.Initialize. The old public Snapshot merges these failures, so the code number alone cannot identify one predicate.

Root's read-only retained-object observation now proves **Controller.Initialize returned error Config (1), with initialized=false**. Thread/revision/gateRevision/requested are zero and Host is entirely uninitialized. Therefore Request, Mailbox.Initialize and Host.Initialize were not reached.

Full decoding of the cached Controller report proves every `Controller::clean` predicate is true: reward bound and healthy with no queued/active/uncertain work; Owner armed and healthy with no hold/save lane/scopes; Gate armed and healthy; all two Owner and three Gate bridge active counts zero. Hook reports both contain exactly two initialized entries, no exception, all four entries known/published/error0/non-null slot and hook. Each cached publication `observed` equals its hook.

This narrows the failure without pretending to identify a missing predicate. In `Controller::read`, MatchesOwner, CurrentController, initial date guard, reward Snapshot and Owner/Gate Snapshot have all run far enough to populate the retained report. Its final **immediate `*slot == hook` dereferences** and exception handler are not recorded independently. `Entry.observed` comes from earlier publication, not that later dereference. Consequently the remaining alternatives are that read tail, or `planning_period_owner::ClaimController` (quiet, binding/date, fresh sampler/Inspector and existing-period ownership). Do not label ClaimController or a particular native field as the proven root cause yet.

The smallest next source-level diagnostic is a bounded publish-once initialization DATA record separating read, clean, ClaimController and fresh Inspector outcomes at their real original boundary, preserving their exact returns and all guards. The other agent owns that explicit successor. No additional game action or probe replay is needed on the current lifetime.

## How the private address was justified

`a_save_parent_failure_layout.cpp` compiles the frozen Runtime/header definitions with private access exposed only in this owned executable. It calls no Runtime method and emits sizeof/offsetof metadata. Same MSVC x64 /W4 /WX /MT output confirms Runtime size18232; Controller at12456; its Report at+136 (Runtime+12592), size2032. The only initial compile failure was referencing a nonexistent Host.Report.error field; the real Host state/thread/lease/frame fields replaced that erroneous helper field, and the failure log is retained.

The exact approved DLL SHA is `8125ec17de92bd46f9fcda780008990b5c8c1b9456630f895de8bb39886054cb`. Snapshot export RVA104B0 dispatches through invoke C020; its C12D cmp references DATA RVA60F08. The actual Snapshot callback's FC80 mov rcx references the same RVA60F08. This gives the retained Runtime pointer location, not a guessed memory search. The reader checks both exact instruction byte sequences in the pinned PE and loaded module, full bounded PE headers, DATA protection, PID/birth/base, exact module path and image SHA.

`a_save_parent_failure_read.py` defaults to help. Its opt-in operation is:

```powershell
py -3 work/mod_research/a_save_parent_failure_read.py --observe --run <restored-failure-run>
```

It only opens QUERY/VM_READ/SYNCHRONIZE rights. It validates a readable private non-executable Runtime range, checks Runtime Config PID/birth/base, and takes two equal 18232-byte reads with pointer and identity checks around them. It does not call Controller.Snapshot or any native function. Raw object data stays private. The reader source remained exactly `d00b8bc54bc6e0b0c65dc67568d192b8705fe572e88275e07a1edc4f4b6beb28` throughout root's observation and this analysis.

`a_save_parent_failure_detail.cpp` is a separate owned layout extension for all hook and bridge fields; it does not edit the already-observed reader or basic layout. `a_save_parent_failure_decode.py` consumes the saved RPM JSON and both fixed-hash layouts, checks the original observer identity, and evaluates the complete cached read-shape and clean predicates. Its synthetic active-bridge and missing-publication mutations reject, without altering the archived bytes or manufacturing native reports.

## Evidence

- Basic layout compiled/executed: `a_save_parent_failure_layout_runs/20261009-222350-412512/layout.json`, SHA `7a90099ca6313310ea9386226476f7d737ecbb845816baa2ccddda71686855ec`. Failed compile `222318-905039` retained.
- Owned native layout rebuild and four bounded decode checks: `a_save_parent_failure_test_runs/20261009-222741-089421/result.json`, 5/5 PASS, SHA `3bc90ea62f5cd5ab1b455a2612cc36690cbc3b51a328e6ec5a288d80d451f258`.
- Root's actual RPM-only observation: `a_save_parent_failure_read_runs/20261009-222719-621334/result.json`, SHA `06662375c24ee1073333cb8cb3b54d4c76980123c874ca299a2899f679635628`.
- Additional MSVC detail layout: `a_save_parent_failure_detail_runs/20261009-222855-390752/layout.json`, SHA `33713769e2a294b9f5d4879584455d2c86fd06e040f51b011d0c483bc0d36ea3`.
- Final detailed offline audit and two refusal checks: `a_save_parent_failure_decode_runs/20261009-223155-186281/result.json`, SHA `efd2a8c25b87211f2b0e93ae23ca455fe09afc544683888b2621940af6df326f`. Earlier passing `223110-615386` is preserved; the final decoder additionally pins the detail layout and original observer, with all detail build artifacts included.

These outputs are diagnostic observations only. They provide no restore, repeat, Save, Ready, full-world or multiplayer permission. Root owns current process exit and independent live closeout; no additional process access is requested by this handoff.
