# Bounded Root activation successor

This module removes the direct fixture call to Root `Begin` for an isolated long-lived native runner. It is not a live game installer and does not support taking over an already-running, unwrapped pool.

## Source and identity

`b_reload_root_activation_parent.cpp` is an ABI-compatible successor to the frozen bound parent source. The hardware context at `50B598` is first accepted by the generation-bound Provider; only then does it register the immutable task and attempt initial worker publication. A resume accepted at `50B4AE` must match state, vtable, worker, formal slot and callable at its next `50B598`; it neither creates a second record nor calls activation again. This logic includes the strict resume-vtable check from `b_reload_yield_parent.cpp`.

A new worker is admitted only while its actual thread unwinds to the original initial wait return `83A9D7`, with the original RSI/RDI/RBX object/control/function-slot relationship, `done=1`, `stop=0`, original `834D10` entry, and a real unsignaled auto-reset wake event. Publication suspends that exact same-process thread, verifies the initial wait, atomically changes only object+38 to a retained PE wrapper, and resumes it. Prior suspension, wrong thread, wrong object or a later runner wait are refused. The observed `834DFD` wait of an already-running unwrapped pool is deliberately not an activation source.

The original `834D10` runner then runs inside a dedicated retained PE bridge. A separate dedicated bridge replaces one IAT pointer at `base+123C0D8`; production requires the slot to belong to that MEM_IMAGE and be read-only/aligned, and the prior function to equal the actual `GetProcAddress(kernel32, LeaveCriticalSection)` target. These checks are repeated before the CAS. A third-party replacement is not adopted. The owned fixture explicitly permits its private archived-image allocation and PE no-op critical-section double under `B_RELOAD_ROOT_ACTIVATION_FIXTURE` only.

The actual IAT return `834D88` supplies the per-task start. It must have the existing outer PE owner, exact current thread and a real `RtlCaptureContext` / PE-unwind result with native RBX=control and RDI=thread object. It selects the matching pending immutable task and calls the existing nested Root observer. Root's actual `50B730` hardware event still validates record ownership through Provider's locked `ObserveExpected`; a snapshot or fabricated context is not used as a substitute. The actual IAT return `834DC8` finishes that task. Native outer exception unwinding also finishes/abandons the active task, preserving the original exception.

Activation does not rewrite the archived thread-entry/runner/thunk bytes, return addresses or shadow stacks. Its parent source still requires the separately published two call-site patches inherited from the existing parent owner. The distinct MASM bridge has normal PE unwind metadata and supports real exception FINALLY. Root retains its original strict four-DR and nested lease rules, including the yield observation point. This isolated suite does not execute yield or nested Load; those remain separately tested by the nested/yield suites.

## API and composition

Link `b_reload_root_activation.cpp`, its bridge C++/ASM, and `b_reload_root_activation_parent.cpp` in place of the old bound/yield parent implementation. Keep the existing nested Root/start/completion/input successors. Initialize once with image base and Provider, then explicitly publish the verified IAT wrapper. The source successor invokes `OnCreation` only after actual parent creation capture. `Stop` prevents future activation; retained wrappers still forward original functions, and active work still receives FINALLY cleanup. The module is retained until process exit, with capacity 8 worker identities and 64 one-use task contexts. No uninstall, live discovery, hot-reload or production permit is provided.

Any first error prevents later registrations/starts. A Begin failure saves its Root report; uncertain hardware restoration is visible in the aggregate report. Existing active task cleanup remains enabled even after an error or stop. Successful publication does not claim that the remainder of the B loading chain is installed.

## Owned execution and remaining scope

The independent test constructs one owned native thread object and uses archived `83A930`, `509FE0`, `834D10`, `50B730`, and their real call sites. Constructor storage, pool selection, callable copy/swap, critical-section service and Update business are explicit doubles. In particular it retains the real initial `done=1` branch; callable copy/swap doubles implement storage for the original scheduler, instead of bypassing its creation branch.

Three cases cover two successive tasks on one persistent runner, native business exception unwinding, and a thread waiting outside the native initial-wait source. They do not run full queue finalization, perform two real game loads, execute real game business, exercise running-pool takeover, or establish room readiness. The full queue still requires replacing its fixture worker constructors / starting point with this activation source and a separately authorized production installer.

## Reproduction

Set `SAN14_PRIVATE_FIXTURE_ROOT` to the immutable private archive directory and run `py -3 work/mod_research/b_reload_root_activation_test.py` from the repository root. The suite verifies archive/image hashes, compiles all new C++ production objects without fixture macros, then builds/runs the isolated owned executable. Public source contains no private runtime image or raw game save. See the final run recorded below; failed diagnostic history is retained locally.

## Diagnostic history

- `20261008-170043-090610`: new production objects compiled; fixture `/WX` rejected one unused parameter. Corrected the fixture declaration.
- `20261008-170122-710260`: all three cases failed before activation at native `50B546` with return `50B548`, because the old owned callable table omitted its copy operation on the now-correct initial `done=1` path. Added explicit copy/swap fixture business, without changing native initialization preconditions. Diagnostic rebuild then demonstrated both task sources and exceptional cleanup; old fixture assertion classification still omitted the new exceptional/non-native-wait case names. Added those names in the new harness only. The directory includes diagnostic rebuild artifacts, and its original FAIL result is not a passing attestation.

Previous passing run: `b_reload_root_activation_runs/20261008-170459-083925/result.json`, **3/3 PASS**, 144 source inputs unchanged, private input hashes unchanged. Result SHA-256: `82ca43ac36a4def2304a47da0b6809e50d7b6be1cdf8e5bdadb4c4a8ce4dad68`. Three production-mode C++ objects and the isolated executable are individually fingerprinted in the result. Two-task case: 2 registered tasks, 2 real Root entries and finishes, 2 bodies, one initial-wait verification and one outer runner entry/finally. Exception case: one real Root entry, actual exception/abandonment, restored hardware state. Wrong-wait case: `Error::Wait`, no initial-wait publication proof, no Root entry or business, no outer wrapper invocation. Full queue activation composition remains untested.

Final staged-source verification: `b_reload_root_activation_runs/20261008-171010-186699/result.json`, **3/3 PASS**, result SHA-256 `45aa9d75aee4cf504fb696b2cc3d69ed09cd1a1fa379edc12bf1e026e0831591`. The only source adjustment after the previous passing run removed one trailing blank line flagged by `git diff --cached --check`; the three cases and production compilation were rerun, all 144 source inputs and private inputs remained unchanged. Public aggregate evidence points to this final run.
