# Player input policy / retained window Owner

## Status, 2026-10-10

This is an explicit successor to the physical window path in
`planning_input_resident`, with a separate phase policy and an admission veto
around the existing `a_reward_save_owner::Submit`. Frozen modules are unchanged.
No game, Steam, current save, debugger, or live installer was accessed. Tests
created only hidden message-only windows and native resources in their own
processes, which exited normally. There is no active game patch from this work.

The meaningful closed gap is **local Ready need not prohibit a trusted remote
reward**. The predecessor `planning_input_interlock::Request(true)` invokes
`ReadyFence`, which also rejects remote native Submit. This successor does not
set that fence. It changes audited local window input independently, then calls
the actual existing reward Owner on its configured serialized local lane.

## Files and contract

- `player_input_policy.{h,cpp}`: immutable room / attachment / epoch / period /
  seat binding; Planning, Save, Load, EventWait, Running and Terminal phases.
- `player_input_owner.{h,cpp}`: one retained physical WndProc publication,
  revisioned HWND delivery, identity/source checks, and `SubmitRemoteReward`.
- `player_input_owner_fixture.cpp`, `player_input_owner_test.py`: production
  compilation plus native owned-window / existing reward Owner execution.

`Owner::Initialize(Config)` must run on the intended HWND thread with a trusted
sole publisher. `Config` retains the existing native reward Owner and its exact
binding; it does not discover or construct a second native User/Save Owner.
`Request(binding,state,revision,duplicate)`, `SubmitRemoteReward(...)` and
`Snapshot(...)` run on the configured serialized local owner thread, never a TLS
callback. The policy binding and native reward binding must have the same period.

Revisions must increase by exactly one. Identical retransmission is idempotent;
old, conflicting, skipped, foreign-binding and foreign-thread requests reject.
Closing holds audited messages immediately; opening waits for the matching
registered HWND message. A receipt becomes acknowledged only on that delivery's
FINALLY, with no pending/active callback. It is not an OS queue-drained receipt.
Terminal cannot reopen. Fixed callback slots / retained Owners are not reset,
reused, unloaded or restored by this module.

| Phase | Audited local command input | Receive remote data policy | Submit new remote reward |
| --- | --- | --- | --- |
| Planning, not Ready | Open after actual window ACK | Allowed | Allowed on trusted owner lane |
| Planning, locally Ready | Held after request | Allowed | Allowed on trusted owner lane |
| Save / Load / EventWait / Running | Held | Allowed | Rejected |
| Terminal | Held | Rejected | Rejected |

The receive column is policy only, not an installed network callback. Before
entering a critical phase, the actual reward Owner must report bound, nonerror,
nonuncertain, not queued and not active. An already accepted native reward blocks
that phase request without consuming its revision; the caller must finish the
existing command first. This avoids changing to Save/Load while an older queued
reward can still execute. It is not a universal native execution fence.

## Physical and native evidence boundaries

The self-owned HWND executes the exact archived `0x5122F0` WndProc (0x78 bytes).
Its `0x510BE0` message business is an explicit C++ fixture replacement. Production
source checks require the original full body, RX MEM_IMAGE pages, class/current
WndProc, the expected ANSI process/thread HWND and engine HWND pointer. Fixture
builds explicitly relax the image mapping and substitute that body. No game
window bootstrap has been proved.

The tested command route invokes unchanged `a_reward_save_owner::Submit` and its
actual retained native User callback / command argument lifetime. Constructors,
world and reward business remain explicit fixture doubles. This is not evidence
that a real game's loyalty, menu or UI has updated.

Only the existing audited Enter / Backspace / Escape key transitions, mouse
move, left/right button transitions and mouse leave are classified for blocking.
Paint, timer and window lifecycle traffic is forwarded. Uncovered keys, wheel,
raw/controller and unclassified messages are forwarded and counted honestly.
Running has **no game report-confirmation whitelist**: current evidence cannot
distinguish a plain report acknowledgment from a decision. A true report whitelist
requires a verified game state/command source, not merely forwarding Enter.

SetWindowLongPtr has no compare-and-swap. Initialize requires sole publication;
the deliberate foreign-publisher race reports uncertainty and the possibility
that a foreign source was replaced. It never compensates by blindly restoring.
Do not install this owner together with `planning_input_boundary` or
`planning_input_resident`. It does not write AI, User, Save or Game vtable slots.

## Final verification

Final private result:
`work/mod_research/player_input_owner_runs/20261010-013434-920485/result.json`

- Result: **9 / 9 PASS**, 662 checks, no case failure or abnormal exit.
- Result SHA-256: `630ec0439d8642b5d90fb8920ec39b69357f778ddd28b3a654237ac7c0f2c9e0`.
- Production library SHA-256: `caf98073ebbd36d6907607aaa522071ba0fbe87453613da646a5da0e3045d7f0`.
- Owned fixture SHA-256: `18bf78b3b2be945fff168ad3098ee7d180c3fbf1a555cf3d9ad429dc65da434c`.
- 60 source pins, 4 absolute private-input pins and all 44 generated artifacts
  independently rehashed after completion; zero mismatches. The artifact table
  excludes its own result.json to avoid a self-referential hash.
- Production and fixture compile with MSVC C++17 /EHa /W4 /WX /O2 /MT.

Cases cover ordinary Ready + remote execution + later release, pending actual
HWND delivery, binding/revision errors, owner-thread mismatch, foreign WndProc,
source drift during our own callback, deliberate publication race, terminal
closure, and already-queued reward preventing critical-phase entry. Save, Load,
EventWait and Running reject new remote Submit; these rejections do not consume
the existing native command sequence. A second accepted reward executes after
returning to Planning. Lifecycle/timer forwarding and uncovered wheel forwarding
are also observed.

Earlier runs are retained: `20261010-013145-322659` (8 cases before the queue-drain
case), `20261010-013236-921978` (9 cases), and `20261010-013347-364122` (9 cases,
renamed production library). There were no failing build/test runs in this
module's development. The final rerun adds complete private-input/artifact
metadata; it is the evidence to use for the current six source files.

To reproduce only on a workstation with the approved private archive/profile and
planning library, set `SAN14_PRIVATE_FIXTURE_ROOT` to that private research
directory, then run `python work/mod_research/player_input_owner_test.py` from
the repository. This is an owned-process test runner, not an installer.

## Remaining integration

1. Provide the actual game HWND-thread bootstrap, trusted sole-publisher lifetime
   and retained reward Owner accessor. Current `a_observed_start` does not export
   the actual reward Owner pointer needed by this adapter. Do not load a second
   User/Save Owner to satisfy the pointer type.
2. Drive this policy from the shared authenticated room phase on the serialized
   owner lane. A successful policy request is an extra veto/observation, never
   permission to save, load, Ready, invoke a native command from TLS or skip the
   existing command journal / authority checks.
3. Establish safe cross-period/world binding retirement and rebinding. This
   fixed attachment refuses a next-period binding; it has no reset or unload API.
4. Prove device/root consumers and other input paths, plus the exact simple-report
   acknowledgment source. The current coverage cannot block all new commands.
5. Validate real menu, native result and UI behavior in a later authorized game
   session. No user operation is required for the completed offline work.

`allInputHeld`, `gameReportWhitelistVerified`, `physicalReleaseProven`,
`osQueueDrained`, `saveAuthorized`, `roomReady`, production bootstrap and native
gameplay capability remain **false**. This is a tested component, not a usable
whole-game input barrier or a two-PC gameplay completion claim.
