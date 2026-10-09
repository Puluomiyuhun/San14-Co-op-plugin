"""Two-period local control over actual typed Runtime exports and A IPC.
No process access at import; no native date writer or B-loaded assertion.
"""
import hashlib
import time
from types import MappingProxyType
import a_save_runtime_contract as wire
import a_save_repeat_contract as repeat
from a_save_runtime_control import require
from checkpoint_fresh_save_binding import SaveReservation


def next_date(year, month, day):
    require(day in (1, 11, 21) and 1 <= month <= 12 and 1 <= year <= 9999, "Planning date required")
    if day != 21:
        return year, month, day + 10
    if month != 12:
        return year, month + 1, 1
    require(year < 9999, "Date overflow")
    return year + 1, 1, 1


def reservation(prep, generation, filename, date):
    year, month, day = date
    request = dict(generation=generation, room_epoch=prep.nativeRoomEpoch,
                   period=prep.period + generation - 1, cut=0, room_id=bytes(prep.roomId),
                   year=year, ruler=prep.ruler, month=month, day=day, force=prep.force,
                   reserved=0, filename=filename)
    binding = hashlib.sha256(bytes(prep) + filename.encode("ascii")).hexdigest()
    return SaveReservation(generation, binding, MappingProxyType(request))


def next_request(prep, artifact):
    require(0 < prep.epoch < 2**64-1 and 0 < prep.period < 2**64-1, "Next binding overflow")
    raw = bytes(artifact.data)
    require(raw and hashlib.sha256(raw).hexdigest() == artifact.sha256, "Previous artifact hash mismatch")
    value = repeat.envelope(repeat.Next, "RequestNext", bytes(prep.nonce))
    q = value.request
    q.previousGeneration = 1
    wire.put_bytes(q.previousSha256, bytes.fromhex(artifact.sha256))
    q.generation, q.period, q.epoch = 2, prep.period + 1, prep.epoch + 1
    digest = hashlib.sha256(bytes(prep.roomInputDigest) + bytes(q.previousSha256) + b"controlled-native-turn").digest()
    require(digest != bytes(prep.roomInputDigest) and any(digest), "Distinct period digest required")
    wire.put_bytes(q.inputDigest, digest)
    q.year, q.month, q.day = next_date(prep.year, prep.month, prep.day)
    return value


def repeat_state(sample, expected=None):
    status = repeat.describe(sample)
    if expected is not None:
        require(bytes(sample.request) == bytes(expected.request) and sample.requested == 1,
                "Runtime repeat request differs from consumed local request")
    require(not sample.error and not sample.stopped, "Native repeat stopped or failed; retain sources")
    if sample.state == 3:
        require(sample.hostThread and sample.previousArtifactMatched == 1 and sample.retiredCount == 1
                and sample.retiredSerial and sample.activeGeneration == 1 and sample.drainPending == 1
                and not sample.lease and not sample.frame, "Running lacks actual retired/no-lease evidence")
    return status


def cleanup_gate(sample):
    # Stop can leave terminal Running: no attempt to unlock or publish restoration.
    repeat.describe(sample)
    require(not sample.lease and not sample.frame and not sample.drainPending,
            "Repeat/Running is unresolved; retain sources until normal process exit or proven drain")


def drive(channel, prep, filenames, call, keep, event, *, wait_seconds=600,
          clock=time.monotonic, pause=time.sleep):
    require(type(wait_seconds) is int and 1 <= wait_seconds <= 1800, "Bounded human turn wait required")
    require(len(filenames) == 2 and filenames[0] != filenames[1], "Two unique filenames required")
    require(0 < prep.epoch < 2**64-1 and 0 < prep.period < 2**64-1, "Next binding overflow")
    first = reservation(prep, 1, filenames[0], (prep.year, prep.month, prep.day))
    event("submit-1", dict(filename=filenames[0], binding_sha256=first.binding_sha256))
    channel.submit(first)
    artifact = channel.wait_artifact(1, timeout=30)
    keep(1, filenames[0], artifact)
    command = next_request(prep, artifact)
    event("request-next", dict(previous_sha256=artifact.sha256, native_request=wire.values(command)))
    response, _ = call("RequestNext", command)
    require(bytes(response.request) == bytes(command.request), "RequestNext response changed request")
    deadline, announced = clock() + wait_seconds, False
    while True:
        sample, _ = call("RepeatSnapshot")
        status = repeat_state(sample, command)
        if status["second_save_binding_ready"]:
            break
        if sample.state == 3 and not announced:
            event("running-await-human", dict(message="可以正常推进一旬；不新增命令。关闭普通报告后停住，遇到需要选择的事件请先停止操作。", automatic_game_advance=False))
            announced = True
        # Real pipe Snapshot keeps the same authenticated connection alive; it
        # neither submits commands nor asserts that the engine has advanced.
        channel.snapshot()
        require(clock() < deadline, "Human turn wait expired; native Running may remain unresolved")
        pause(.25)
    second = reservation(prep, 2, filenames[1], (command.request.year, command.request.month, command.request.day))
    event("submit-2", dict(filename=filenames[1], binding_sha256=second.binding_sha256))
    channel.submit(second)
    artifact = channel.wait_artifact(2, timeout=30)
    keep(2, filenames[1], artifact)
    return dict(two_native_artifacts=True, running_observed=announced,
                game_advance_called=False, b_loaded_proven=False, two_game_ready=False)
