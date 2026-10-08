"""Trusted local PeriodCoordinator -> fixed-width native planning identity.

No network endpoint, game access, load acknowledgement, or simulation authority.
The serialized scope is identity data, never proof that a native transition ran.
"""
from copy import deepcopy
import hashlib
import struct

import authoritative_sync as sync


def validate(value):
    sync.require(type(value) is dict and set(value) == {
        'schema', 'room_id', 'binding_epoch', 'timeline_epoch', 'scope_sha256',
        'period', 'base_sequence', 'date', 'viewer_force'}, 'Bad local period scope')
    sync.require(value['schema'] == 'san14.local-period-scope.v1', 'Wrong local scope schema')
    sync.require(all(sync.hexid(value[k], 32) and int(value[k], 16) for k in
                     ('room_id', 'binding_epoch', 'timeline_epoch')), 'Bad scope identity')
    sync.require(sync.hexid(value['scope_sha256']) and int(value['scope_sha256'], 16), 'Missing scope digest')
    sync.require(sync.integer(value['period'], 1) and sync.integer(value['base_sequence']), 'Bad period/cut')
    sync.validate_node(value['date'])
    sync.require(type(value['viewer_force']) is int and 0 <= value['viewer_force'] < 51, 'Bad local viewer')


def from_coordinator(coordinator, player):
    """Call once at the trusted start of a settled planning period.

    Caller authenticates room and independently observes the actual native view.
    Later commands do not regenerate this immutable initial scope. In particular,
    native sequence numbers remain global; next period does not restart at one.
    """
    sync.require(type(coordinator) is sync.PeriodCoordinator and player in ('A', 'B'), 'Trusted coordinator required')
    with coordinator.lock:
        sync.validate_scope(coordinator.scope)
        sync.require(coordinator.phase == 'PLANNING' and coordinator.connected == {'A', 'B'} and
                     not coordinator.ready and not any(coordinator.inflight.values()), 'Not an idle planning start')
        sync.require(coordinator.reports['A'] == coordinator.reports['B'], 'Replicas do not share an input cut')
        report = deepcopy(coordinator.reports['A'])
        sync.validate_cut({k: report[k] for k in ('sequence', 'prefix_sha256')})
        sync.require(sync.hexid(report['world_sha256']), 'Missing initial state hash')
        digest = sync.digest({'schema': 'san14.native-period-context.v1',
            'scope': coordinator.scope, 'period': coordinator.period,
            'epoch': coordinator.epoch, 'node': coordinator.node,
            'state_contract': coordinator.state_contract, 'initial_cut': report})
        result = {'schema': 'san14.local-period-scope.v1',
            'room_id': coordinator.scope['room_id'], 'binding_epoch': coordinator.scope['binding_epoch'],
            'timeline_epoch': coordinator.epoch, 'scope_sha256': digest,
            'period': coordinator.period, 'base_sequence': report['sequence'],
            'date': deepcopy(coordinator.node), 'viewer_force': coordinator.scope['bindings'][player]['force_id']}
        validate(result)
        return result


def native_digest(value):
    """Matches C++ MakeBinding exactly, without integer truncation or padding."""
    validate(value)
    date = value['date']
    data = b'san14.local-period-scope.v1'
    data += b''.join(bytes.fromhex(value[k]) for k in ('room_id', 'binding_epoch', 'timeline_epoch', 'scope_sha256'))
    data += struct.pack('<QQHBBB', value['period'], value['base_sequence'], date['year'],
                        date['month'], date['day'], value['viewer_force'])
    return hashlib.sha256(data).hexdigest()
