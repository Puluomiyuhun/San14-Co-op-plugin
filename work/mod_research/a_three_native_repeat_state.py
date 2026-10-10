"""Inspect the dedicated three-save ABI; never grant gameplay permission.

The native successor clears requested after each successful controller handoff.
The frozen two-save decoder deliberately rejects that state and is unchanged.
"""
import a_save_three_repeat_contract as repeat
from a_save_runtime_control import require


def repeat_state(sample, expected):
    require(type(sample) is repeat.Snapshot and type(expected) is repeat.Next,
            'Exact repeat ABI objects required')
    repeat.decode(repeat.Snapshot, 'RepeatSnapshot', bytes(expected.nonce), bytes(sample))
    require(not sample.header.result and not sample.error and not sample.stopped,
            'Native repeat stopped or failed; retain sources')
    require(0 <= sample.state < len(repeat.STATES) and not sample.bLoadedProven and
            not sample.simulationEnabled, 'Unknown state or unsupported gameplay claim')
    require(all(getattr(sample, k) in (0, 1) for k in ('requested','stopped',
        'previousArtifactMatched','nativeDateMatched','lease','frame','drainPending')),
        'Invalid flag encoding')
    require(bytes(sample.request) == bytes(expected.request), 'Native request changed')
    old, new = expected.request.previousGeneration, expected.request.generation
    require(old in (1, 2) and new == old + 1, 'Only consecutive three-save generations supported')
    if sample.state == 3:
        require(sample.requested == 1 and sample.hostThread and sample.previousArtifactMatched == 1 and
                sample.retiredCount == old and sample.retiredSerial and sample.activeGeneration == old and
                sample.drainPending == 1 and not sample.lease and not sample.frame,
                'Running lacks current retired/no-lease evidence')
    elif sample.state == 4:
        require(sample.requested == 0 and sample.activeGeneration == new and sample.retiredCount == old and
                sample.retiredSerial and sample.hostThread and sample.previousArtifactMatched == 1 and
                sample.nativeDateMatched == 1 and not sample.lease and not sample.frame and not sample.drainPending,
                'Successor binding lacks matching native retirement/date evidence')
    else:
        require(sample.state in (1, 2) and sample.requested == 1 and sample.activeGeneration == old,
                'Unexpected state for accepted successor request')
    return dict(next_save_binding_ready=sample.state == 4, generation=new,
                two_player_ready=False, can_advance_game=False)
