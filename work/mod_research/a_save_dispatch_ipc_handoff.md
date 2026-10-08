# A Save: actual named pipe → mailbox → host composition

2026-10-09. **5/5 owned-process scenarios PASS.** This successor connects the
mailbox to a real Windows named-pipe Server and separate client child process.
No game, Steam, UI, current save, live process discovery, TLS or patch was used.
Frozen Server/mailbox sources are unchanged; only `a_save_dispatch_ipc*` added.

## Actual path and production changes

The child sends the existing authenticated wire request. The Server thread
consumes its identity before invoking the mailbox Adapter's Submit port. That
port blocks on copied request state. The distinct trusted host thread Takes
once and signals Accept; only then may the pipe return Ok. Later a copied
artifact flows through the real frozen packet encoder/SHA and named pipe.
The child verifies framing, generation, bytes/hash, writes the actual received
packet, and the runner decodes it with frozen Python `decode_packet`.

`a_save_dispatch_ipc.h/.cpp` are explicit successors copied from
`a_save_held_ipc.h/.cpp`. Each run retains normalized source diffs. Changes are
limited to the namespace/header, mandatory execution-cancellation callback,
monitor state/lifetime, cancellation checks and monitor startup/join. The
production Config still requires the concrete `a_save_user_owner::Owner*`;
its Snapshot/Stop calls and all Owner admission checks remain. No generic
peer-supplied snapshot or arbitrary pointer API was added.

Authentication, actual client PID/process validation, nonce-shaped local
pipe name, ACL, one connection, fixed 168/56/60-byte ABI, monotonic sequence,
two consumed requests, consume-before-submit, artifact identity matching and
the real packet codec remain the frozen implementation. `dispatch_ipc.lib`
contains the production Server object; that exact object is linked into tests.

## Cancellation now interrupts a blocked Submit

Run starts one retained monitor after the kernel client identity is checked.
Per-request secret authentication remains in process(). The monitor observes
shutdown/client-process handles and calls PeekNamedPipe
without consuming data to detect EOF. Thus it detects pipe-only disconnect
while the client process remains alive, even when the Server is inside a
synchronous Submit callback. The monitor sets cancellation and calls only the
trusted executionStop callback, wired here to mailbox Adapter.Stop. That wakes
the blocked Submit; it does not call Controller or native Save.

Server Stop invokes executionStop before Owner.Stop. Submit also rechecks
availability after the callback, so an acceptance racing cancellation cannot
be counted as a successful pipe submission. Queued work becomes Cancelled;
claimed work becomes Unknown and is never reissued. Late host acceptance is
refused. The monitor is signalled and joined before Run returns; Server and all
callback owners must outlive Run. During Run, Owner calls remain on its Server
thread. The destructor can call Stop on the destructor's caller thread, as in
the predecessor; do not claim universal thread confinement for Owner.Stop.

executionStop must be thread-safe, idempotent, short, and must not reenter the
Server or wait for the host/Controller. It may be called from the monitor and
Server/destructor paths. The tested mailbox implements this with its own lock
and condition-variable wakeup. Repeated cancellation is harmless. Joining the
monitor relies on that trusted callback returning; it is not a hard real-time
termination guarantee.

A wire Stop queued behind a Submit on the same serial connection cannot
interrupt that Submit. Immediate paths are external shutdown, pipe closure,
or client process exit. The normal wire Stop response is still drained before
EOF; no protocol multiplexing was introduced.

## Precisely what remains doubled / unconnected

The fixture TU explicitly supplies **only diagnostic implementations of
Owner constructor, Snapshot and Stop**. Those report the host business double's
state. No production Owner/Controller/Root callback or serializer executes in
this test. The fixture artifact has deliberately supplied lifecycle fields
and four diagnostic bytes, with an actual computed hash; passing the packet
codec proves transport shape and integrity, not native Save provenance.
Do not link this fixture TU into production.

The real integration still needs an evidenced stable native host boundary,
held planning/writer permission, real Submit completion and actual copied
storage artifacts. Existing mailbox Take/Accept remain trusted host calls,
not evidence by themselves. The production library resolves Owner methods
from the real retained implementation when that integration is built.

## Tests and evidence

```powershell
py -3 work/mod_research/a_save_dispatch_ipc_test.py
```

No private archive is needed. The existing C++ toolchain builds a static
library and owned fixture. Its separate child authenticates the actual kernel
Server PID; Server checks the child's actual PID. Three owned synchronization
events are intentionally inherited. This owned-only fixture uses the broad
handle-inheritance flag, not an explicit handle whitelist; other inheritable
host handles may also reach the child. The complete scenario list is required
for PASS.

- Normal: two real Submit/Copy transactions, different periods and saved dates,
  exact returned Snapshot.generation, two strict Python-decoded packets, normal
  Stop acknowledgment followed by EOF, both records Delivered.
- Queued / claimed pipe-only disconnect: before injection require a live Queued
  request; claim only in the latter case. The child closes its pipe and waits
  alive on a separate event. Both stop before the Adapter's five-second timeout,
  preserve Cancelled/Unknown and reject replay/late acceptance.
- Queued / claimed external shutdown: same no-deadlock/no-replay checks with
  shutdown signalling instead of EOF.

Cancellation timing starts **before** signalling the child/shutdown. Final
measured durations were 32/33 ms for EOF and 16/17 ms for shutdown. Tests assert
under 1500 ms against the 5000 ms Adapter deadline; these are test measurements,
not a production latency guarantee. Server monitor, service thread and child
all exited in every passing scenario before owned handles were closed.

Final: `a_save_dispatch_ipc_runs/20261009-010859-975323/result.json`, 5/5 PASS,
26 source/header/Python pins unchanged.

- Result SHA256: `ad7944be294de7954ad0cdde034340548559ecc03c6926188bc3ba0a7ade1401`
- EXE: `c7e9f95162c4fb71a6b8766ecf054b60296873faa86959599c409617323c5793`
- Production library: `398c2a3fb79a94fb1eb31d97cedd3771a3a0f388cd14df1392f1dcefc061db41`
- Actual linked Server object: `299e9d9ada003a338b60aa28d37d43342941c362db45fedfed00bcc2b3a1b36f`

Source SHA256:

| File | SHA256 |
| --- | --- |
| ipc.cpp | `326d84eb2a8c64fe72649f7a44b7abf3ae5b28d2fa027e799565007e52ee09a3` |
| ipc.h | `403d4f99079844192c7a5e0ef3860abc9b33f74b87c661d72af1d0067bd9c417` |
| ipc_fixture.cpp | `1426203eeccfb533e2f175de9b832fb0123c0d09a1700da233102f558b38b669` |
| ipc_test.py | `9aaaa3a638d79b11ec8497863c30d2fe1ea7ac9489eef4ad35d8db1625faab8b` |

Initial `010817-536341` also passed 5/5. The final run strengthens the pre-fault
queued-state assertion and cancellation timing origin. No failed test run
occurred in this successor; all logs, normalized predecessor diffs and received
packets remain in their run directories. The earlier mailbox compilation
failure belongs to its own documented run and is not hidden or recounted here.
