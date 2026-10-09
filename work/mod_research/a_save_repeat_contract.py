"""Additive repeat-period ABI data only; no process or game access.

RequestNext acceptance means queued, never permission to advance the game.
RetiredWaitingDate is intentionally blocked until a native advance adapter exists.
"""
import ctypes as C

import a_save_runtime_contract as legacy

U8, U16, U32, U64 = legacy.U8, legacy.U16, legacy.U32, legacy.U64
OPS = {**legacy.OPS, 'RequestNext': 9, 'RepeatSnapshot': 10}
STATES = ('Idle', 'Queued', 'Observing', 'RetiredWaitingDate', 'ReadySecond', 'Failed')
ERRORS = ('None', 'Shape', 'Delivery', 'Boundary', 'Observation', 'Retire',
          'Date', 'Rebind', 'Controller', 'Host', 'Stopped')


class NextData(legacy.Packed):
    _fields_ = [('previousGeneration', U64), ('previousSha256', U8 * 32)]
    _fields_ += [(n, U64) for n in ('generation', 'period', 'epoch')]
    _fields_ += [('inputDigest', U8 * 32), ('year', U16), ('month', U8), ('day', U8)]


class Next(legacy.Packed):
    _fields_ = [('header', legacy.Header), ('nonce', U8 * 32), ('request', NextData)]


class Snapshot(legacy.Packed):
    _fields_ = [('header', legacy.Header), ('nonce', U8 * 32)]
    _fields_ += [(n, U32) for n in ('state', 'error', 'hostThread', 'requested', 'stopped')]
    _fields_ += [(n, U64) for n in ('activeGeneration', 'retiredSerial', 'retiredCount')]
    _fields_ += [('request', NextData)]
    _fields_ += [(n, U32) for n in ('previousArtifactMatched', 'nativeDateMatched',
                                  'bLoadedProven', 'simulationEnabled')]
    _fields_ += [(n, U32) for n in ('lease', 'frame', 'drainPending')]


TYPES = {'NextData': NextData, 'Next': Next, 'RepeatSnapshot': Snapshot}


def envelope(kind, operation, nonce):
    expected = {'RequestNext': Next, 'RepeatSnapshot': Snapshot}
    if expected.get(operation) is not kind:
        raise ValueError('Exact repeat operation/type required')
    obj = kind()
    obj.header = legacy.Header(legacy.MAGIC, legacy.VERSION, C.sizeof(kind), OPS[operation], 0)
    legacy.put_bytes(obj.nonce, nonce)
    if not any(obj.nonce):
        raise ValueError('Nonzero initialized-runtime nonce required')
    return obj


def decode(kind, operation, nonce, raw):
    expected = envelope(kind, operation, nonce)
    if len(raw) != C.sizeof(kind):
        raise ValueError('Response size differs')
    obj = kind.from_buffer_copy(raw)
    h, e = obj.header, expected.header
    if (h.magic, h.version, h.size, h.operation) != (e.magic, e.version, e.size, e.operation):
        raise ValueError('Foreign response header')
    if bytes(obj.nonce) != bytes(expected.nonce):
        raise ValueError('Foreign response nonce')
    return obj


def describe(snapshot):
    """Do not convert queued/retired state or caller-supplied output into readiness."""
    if snapshot.header.result:
        raise ValueError('Runtime did not return a successful snapshot')
    if snapshot.state >= len(STATES) or snapshot.error >= len(ERRORS):
        raise ValueError('Unknown repeat state')
    if snapshot.bLoadedProven or snapshot.simulationEnabled:
        raise ValueError('Unsupported readiness claim from this ABI generation')
    if any(getattr(snapshot, field) not in (0, 1) for field in
           ('requested', 'stopped', 'previousArtifactMatched', 'nativeDateMatched',
            'lease', 'frame', 'drainPending')):
        raise ValueError('Invalid flag encoding')
    if snapshot.state == 4 and not (
            snapshot.requested and snapshot.activeGeneration == 2 and snapshot.retiredCount == 1
            and snapshot.retiredSerial and snapshot.hostThread and snapshot.previousArtifactMatched
            and snapshot.nativeDateMatched and snapshot.request.previousGeneration == 1
            and snapshot.request.generation == 2):
        raise ValueError('Second binding lacks matching native evidence')
    return {
        'state': STATES[snapshot.state], 'error': ERRORS[snapshot.error],
        'second_save_binding_ready': snapshot.state == 4 and not snapshot.error and not snapshot.stopped
                                    and not snapshot.lease and not snapshot.frame and not snapshot.drainPending,
        'two_player_ready': False, 'can_advance_game': False,
        'waiting_for_native_date': snapshot.state == 3,
        'native_date_matched': bool(snapshot.nativeDateMatched),
        'previous_artifact_matched': bool(snapshot.previousArtifactMatched),
        'repeat_cleanup_pending': bool(snapshot.lease or snapshot.frame or snapshot.drainPending),
    }
