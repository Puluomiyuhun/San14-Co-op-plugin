# Warm refresh: production owner and ABI

New `b_warm_refresh_owner.h/.cpp` and `b_warm_refresh_contract.py` connect the
refresh core to the existing warm owner without modifying its frozen ABI.
The root agent owns the separate request/retirement successors, production
build and combined native tests. Their evidence is required in addition to the
compile/ABI check below; this handoff does not claim an actual game refresh.

## Native entry contract

`InstallBWarmRefreshOwner` captures one immutable wrapper Config, then calls
the original `InstallBWarmProfileOwner` on its nested `warm`. Capturing does not
call FileWrite. The wrapper is process-lifetime storage and is not reset after
failure. Native `Capture(const Config&)` exists for composition; it neither
captures the warm profile nor installs hooks, so an owned fixture can keep its
existing explicit profile setup without capturing that profile twice.

Only the successor's real `CommitGameBefore` may call
`Execute(authenticatedApi)`. That API must retain the original active-call
guard and input Inspector as its validator. The wrapper verifies the exact
configured storage object and original read/exists/size endpoints, repeatedly
calls that validator, and separately checks FileWrite slot zero, module bounds,
MEM_IMAGE executable page and first 32 bytes. The approved module/lifetime
checks remain the original validator's responsibility. The owned read bridge
at slot eight is supported by that original validator and is not removed.

Before publication, actual Windows handles validate the private new source,
old destination and private backup against their full expected hashes. Source
and destination additionally match their captured file identities; they must
be different files. Handles reject directory/reparse leaves and hardlinks.
Paths are explicit absolute local paths with no traversal or ADS. The trusted
local coordinator remains responsible for the approved destination namespace,
parent-directory protections and backup authorization; the config is not a
remote filesystem capability.

The old destination handle closes before FileWrite; private source and backup
remain pinned. The core verifies the previous native contents twice, persists
one intent, writes once and verifies the new native contents twice. Success
then opens the destination read-only with deny-write sharing, verifies its new
physical bytes, and retains that handle until retirement. It never performs
the old coordinator's prior physical replacement of the destination.

`ReleaseAfterRetirement()` has no exported entry and invokes no stale
GameBefore validator. The root's successor must call it only after the actual
paired retirement seals admission and restores all six slots. It closes only
this owner's target lease. Release failure remains terminal. Any failure after
acquiring the target lease keeps it held; no recovery, rollback, new intent or
automatic retry is provided. A refresh success is not a load or Ready permit:
the original request read/intent/CAS and complete loading lifecycle still run.

## Fixed wire ABI

Windows x64 defaults, version 1, magic `0x53414E1457524631`:

- Config: 14552 bytes, nested old warm Config at offset 16. The write Endpoint
  is at 11352; old size/hash at 11400/11408; source/old-target Identity at
  11440/11460; target, backup and intent wchar paths at 11480/12504/13528.
- Report: 304 bytes. This contains no remote pointers, only state/error,
  actual write/read/intent counters, target lease status, hashes, stages and
  attempt/epoch/generation. `firstFailure` preserves the earliest failure;
  a failed readback records the core's precise readback stage and OS error.
- Description: 152 bytes, with nested old warm Description at offset 24;
  Python accesses the underlying owner description as `description.warm.bank`.

Exports are `InstallBWarmRefreshOwner`, `DescribeBWarmRefreshOwner` and
`GetBWarmRefreshReport`. Existing warm/owner/retire exports remain unchanged.
Successful final validation requires state Released (4), error zero, matching
attempt/epoch/generation and old/new hashes, one execute/write/returned write,
durable intent, two old reads and two new reads, matched, leaseReleased=1,
releaseCalls=1 and leaseHeld=0. Those fields supplement the existing deep warm
retirement validation; they do not replace it.

## Executed check

`py -3 work/mod_research/b_warm_refresh_abi_test.py`

The owner TU compiles with actual MSVC `/W4 /WX /O2 /MT /EHa`, without fixture
macros. A separate native ABI executable reports C++ sizes and offsets, which
are compared with the real Python ctypes contract. This check executes no
refresh IO, exports, hook installation, game or Steam operation.

Final result outside the repository:
`../mod_research/b_warm_refresh_abi_runs/20261009-214400-527781/result.json`,
SHA `8e490c13b1f3c23cccc5123ec2edb814da9bef171fc5d1da6f444a78743c9815`.
It pins the transitive native headers, production source, Python contracts,
test, generated build and native objects/executable/logs. Earlier successful
214313-691056 is retained; a subsequent precise failure-reporting improvement
was compiled and checked again in the final run. No failure was discarded.

The root's combined factory test is responsible for executing this owner at
the authenticated callback and retirement sites. Successful compilation alone
is not evidence that FileWrite has refreshed the real Steam storage view.
