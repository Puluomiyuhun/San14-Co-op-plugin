# A Runtime: first actual save attempt

2026-10-09. The new exported DLL and publisher were installed in the actual
supported game. A real local IPC request reached the native Save state and
created one independent file. **Acceptance failed; this is not a successful
checkpoint or a playable two-client build.**

## What ran

`a_save_runtime_start.py` composes the concrete typed ABI, publisher, natural
parent initialization and existing IPC client. It backs up every existing
`.s14`, reserves a process-lifetime once claim and a unique filename, verifies
build/source identities, and issues exactly one Submit. It never advances the
date, loads a file, replaces a slot or retries an uncertain operation.

The Python ABI is checked against a C++ `sizeof`/`offsetof` schema. The control
helper keeps a remote buffer on uncertain thread completion. Publication uses
the separately tested publisher; only a clean, zero-write held-window refusal
may be sampled again. Stop and source restoration are separate operations.

```powershell
# Read the current HANDOFF and establish a fresh local process/build first.
# This default only captures current state; it does not install or save.
py -3 work/mod_research/a_save_runtime_start.py --pid <current-pid>
```

The explicit `--execute --build-run <exports-run> --publisher-build <publisher-run>`
path is an internal single-save experiment. **Do not run it in the failed
process, reset its claim, or treat the command as a multiplayer installer.**

## Actual result and failure evidence

Private run: `a_save_runtime_live_runs/20261009-123703-876595`.

- Installation and natural parent initialization succeeded. The IPC server
  accepted one Submit; it returned no artifact.
- Driver observed one bind, one queue, native phases 0–4, worker join and
  finalizer return. The game returned to the same Zhang Lu planning map,
  203-08-11, without date advancement.
- One new 274,879-byte file was created. Its actual bytes are private evidence;
  it is not the approved shared slot34 fixture and must not be committed.
- Every original save is unchanged. The only added save is the reserved file.
- Driver ended `Uncertain/error54`, `fileVerified=0`. Read-only inspection of
  its retained `native_storage_read::Evidence` found `stage=context`, no OS or
  exception error, and **zero native exists/size/read calls**. This was a
  validation rejection before native file comparison, not an observed hash
  mismatch.
- The serialized storage gate recorded `ValidationFailed`, with underlying
  attachment `Owner` rejection. The report sidecar is revoked, with 25 AFTER
  rejections and one storage rejection. Current report cursor, empty tree,
  report flag, root and world still match the pinned values; this later sample
  does not establish their state throughout saving.
- The upstream Game gate recorded `Input` (not `Scope`). Its exact earliest
  rejected layout predicate was not captured. Do not claim the entire causal
  chain is already proved. The covered-User regression is documented separately.

Private layout evidence was compiled from the exact implementation successors,
not guessed from the public headers. An offline relink map was cross-checked
against actual loaded DLL section bytes. Reading these diagnostic fields did
not execute target code or write target memory. These private addresses and
offsets are tied to that build/process and are not a public runtime ABI.

## Cleanup boundary

The IPC thread exited and the debugger detached. The stopped Runtime retains
its DLL and seven patched sources. `saveLane=1` and the host producer lease is
still held: the existing Driver cannot leave Uncertain, Owner only clears the
lane on Complete, and Host only releases a committed save after verified
completion. Therefore `restoreReady=0` and restoration was correctly refused.

There is no safe abort API in this version. Do not directly release the host's
SRW lock from another thread, rewrite success flags, unload the DLL, remove
the claim or force source restoration. Normal game-process exit is the current
recovery route. The latest cleanup observation is in `docs/HANDOFF.md`; an exit
request alone is not proof of exit.

Future abort retirement must remain distinct from Complete: on the original
host thread, prove native tasks and scopes have drained, release only this
save's occupancy and lease, keep its error/claim/file, then allow independently
checked source restoration. No artifact may be exported from that abort.

## Next acceptance

The missed queue/covered-User scheduling cases now have an exact failure
reproduction and a five-case successor regression. `a_save_covered_gate.cpp`
accepts only the specifically reserved pending Save; `a_save_covered_owner.cpp`
retains report invariants during the exact owned covered-User path. Foreign,
multiple and wrong-generation queues, and report-cursor drift still reject.
These tests use explicit native-business and covered-return doubles; they do
not certify the fixed code in the game.

The complete successor DLL and original export ABI build passed in
`a_save_covered_runtime_runs/20261009-125624-320549`; its `abi` subdirectory is
the new `--build-run` input. DLL SHA-256 is
`0d5052b5f852a8a573d8bd4c63bbcf452313cfce37e0ad84b398781b4281659f`.
The launcher/native-schema test also passed with this build. The failed initial
builder preparation is preserved; it executed no compiler or game operation.

Rebuild offline with `py -3 work/mod_research/a_save_covered_runtime_build.py`.
The new Gate exports `ASaveCoveredGateFirstFailure` as data, with the packed
layout in its header. Its first nonzero stage is published last; read it twice
under the exact process/module identity, without executing another target
function. It is diagnosis, not a source-restoration receipt.

After confirming the old process exited normally, a fresh game process
must produce **one verified new save and a verified cleanup**. A second save,
B's two legal consecutive loads and full two-client integration remain later
acceptance gates. Full game-input and writer exclusion are still unproved.
