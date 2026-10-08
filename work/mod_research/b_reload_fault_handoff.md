# Nested input fault and debug-register conflict evidence

## Result

`b_reload_fault_runs/20261008-172227-409156/result.json`: **30/30 PASS**. This is the 26 frozen yield scenarios plus four new isolated Root/input fault scenarios, not 30 complete reloads. Result SHA-256: `13f24f35cd4608a580e01beea196401152156f0a47d6f99d0da055672b42028d`; executable SHA-256: `5626f43fb9187d8ceac3621eefceaccce7b069092a3864712ddc70f2d1d269bd`. All 141 transitive source fingerprints and private inputs remained unchanged. The five existing nested/yield production C++ units compiled without fixture macros. No production source changed.

## What actually ran

The archived Root runner/thunk executes in an owned standalone process. The new nested input scope borrows hardware slots from the real Root observer, executes the existing exact prefetch fixture, and uses OS exception delivery and thread contexts. It does not manufacture a `Capture` or a successful input authorization receipt.

| New case | Observed result |
| --- | --- |
| `root-input-exception-before` | An explicitly injected SEH exception before prefetch causes the child FINALLY to restore its borrowed registers and report `MissingCapture`. Root has entry only, restores its own registers, and abandons its provider scope. |
| `root-input-exception-after` | The real prefetch is captured, then an injected SEH exception unwinds both FINALLY layers. Child observation itself is complete, but Root has no return/done and the provider records abandonment. A child success does not become task success. |
| `root-input-foreign-dr` | An owned helper changes the current fixture thread's free DR2 and enable bit through the OS. Child restoration detects the mismatch; both child and Root retain uncertainty and preserve the changed registers. A new child scope on that thread is rejected before hardware mutation. No return/done is accepted. |
| `root-input-observer-exception` | The observation callback raises SEH. The existing handler contains it, records `Observer` and the exception code, and restores borrowed slots. Unchanged fixture business can return normally, so Root has its three captures; the input error and lack of authorization remain visible. |

Each child FINALLY runs once. Foreign register state is read back after both the child and Root cleanup; neither overwrites another owner. The helper duplicates only its caller's current thread handle and fully joins its own helper thread. The uncertain process is allowed to terminate with its tombstone intact; the test does not reset a once-claim, clear the foreign registers, or pretend restoration succeeded.

All four cases assert `queue_authorized=false` and `full_input_hold=false`. The three abnormal business cases have only three provider events, including Root entry, and retain the abandoned worker rather than fabricating completion.

## Scope limits

Root activation in these four isolated fault cases remains fixture-driven. The new automatic activation/full-queue suite is separate: see [activated queue handoff](b_reload_activated_queue_handoff.md). Do not combine their results into a claim that these faults were tested through that complete activation chain.

The injected failures are real OS-level exceptions and register mutations in the owned process; they are not observed failures in the game. Nested Load start/join exceptions, fault paths under the automatic activation owner, production installation, legal two-save reloads, continuous world/input exclusion and room Ready are still separate work. The predecessor suite's second input remains a diagnostic byte variant, not a legal new game save.

No game process, Steam, UI or current save directory was accessed. No live hook or debugger was installed. No user action is pending.

## Reproduce

From the repository root, with the existing immutable private archives:

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<immutable private archive directory>'
py -3 work/mod_research/b_reload_fault_test.py
```

The runner validates the existing input hashes, compiles production objects and the owned executable, preserves each scenario's output, and rechecks all source/input fingerprints before reporting PASS. Generated profiles, raw logs and binaries remain ignored.

## Failed history

`b_reload_fault_runs/20261008-172054-894405/build.log`: production objects compiled, but `/WX` rejected a local `root` variable shadowing the fixture's global name. The new fixture renamed it to `rootResult`. Before the final run the foreign site was also made a unique, unused function to avoid linker folding into an executed function. No production constraint or warning level was relaxed. The next run is the final 30/30 result above.
