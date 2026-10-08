"""Owned fixture peer for the observed-fence successor; never opens SAN14."""
from copy import deepcopy
import json
from pathlib import Path
import secrets
import sys

from reward_room_flow_fixture import ModelPort
from reward_room_flow import Replica, envelope, report_proof
from reward_ready_flow import FenceReplica, proof, FENCE_SCHEMA, COVERAGE
from room_transport import Client
from reward_menu_capture import CaptureSession


def capture_inputs(replica):
    """Explicit menu-lifetime model derived from this local fixture's context."""
    scope = replica.scope
    force = scope['bindings'][replica.player]['force_id']
    context = replica.port.context(force)
    district = context['main_district_id']
    preview = {'kind': 'reward', 'force_id': force, 'district_id': district,
               'funding_city_id': context['funding'][str(district)]['city']['id'],
               'officer_ids': [97] if force == 12 else [101]}
    trusted = {'room_id': scope['room_id'], 'binding_epoch': scope['binding_epoch'],
               'epoch': scope['timeline_epoch'], 'player_id': replica.player, 'bound_force_id': force,
               'main_district_id': district, 'viewer_force_id': context['viewer_force_id'],
               'attachment_id': replica.attachment, 'menu_instance_id': secrets.token_hex(16),
               'world_revision': replica.journal.status()['sequence'], 'draft_revision': 1,
               'phase': 'PLANNING', 'observed_tick': 100, 'expires_tick': 200}
    return preview, trusted


class ReadyModelPort(ModelPort):
    def __init__(self, viewer):
        super().__init__(viewer)
        self.fence_requested = False
        self.fence_revision = 0
        self.fence_setters = 0
        self.fence_observations = 0
        self.fail_after_setter = False
        self.fake_observation = False

    def request_fence(self, revision):
        if type(revision) is not int or revision <= self.fence_revision:
            raise ValueError('Old model fence revision')
        self.fence_revision, self.fence_requested = revision, True
        self.fence_setters += 1
        if self.fail_after_setter:
            raise RuntimeError('Injected loss after model setter')
        return {'requested': True, 'revision': revision, 'observed': False}

    def observe_fence(self, revision):
        if revision != self.fence_revision:
            raise ValueError('Wrong model observation revision')
        self.fence_observations += 1
        return {'schema': FENCE_SCHEMA, 'coverage': COVERAGE, 'revision': revision,
                'requested': self.fence_requested, 'observed': self.fence_requested and not self.fake_observation,
                'active': 0, 'queued': False, 'uncertain': False, 'owner_stopped': False, 'owner_error': 0,
                'user_native_started_delta': 0 if self.fence_requested else 1,
                'user_native_returned_delta': 0 if self.fence_requested else 1,
                'user_finally_delta': 1, 'all_input_held': False}

    def execute(self, command):
        if self.fence_requested:
            raise ValueError('Owned model fence forbids reward execution')
        return super().execute(command)


def worker():
    port = client = replica = fence = None
    key = secrets.token_bytes(32)
    capture = CaptureSession()
    menu = None
    for line in sys.stdin:
        try:
            request = json.loads(line)
            op = request['op']
            if op == 'open':
                if request.get('native_exe'):
                    from reward_ready_flow_native_port import ReadyNativePort
                    port = ReadyNativePort(request['native_exe'], 2, Path(request['run_dir']))
                else:
                    port = ReadyModelPort(2)
                result = {'attachment': port.attachment_id, 'initial': port.observe(), 'trusted_report_key': key.hex()}
            elif op == 'connect':
                client = Client(**request['config'])
                result = {'player_id': client.player_id}
            elif op == 'request':
                result = client.request(request['packet'])
            elif op == 'attach':
                reply = client.request({'action': 'reward_scope'})
                if not reply.get('ok') or reply['attachment'] != port.attachment_id:
                    raise ValueError('Wrong replica binding')
                replica = Replica(request['journal'], reply['scope'], 'B', port)
                fence = FenceReplica(replica, request['fence_journal'], request['attachments'])
                report = replica.report()
                result = client.request(envelope(replica.scope, 'reward_report', report=report,
                                                proof=report_proof(key, report)))
            elif op == 'consume_reward':
                response = client.request(envelope(replica.scope, 'reward_next'))
                if not response.get('ok') or response['intent'] is None:
                    raise ValueError('No reward intent')
                receipt = replica.apply(response['intent'])
                report = replica.report()
                ack = client.request(envelope(replica.scope, 'reward_report', report=report,
                                               proof=report_proof(key, report)))
                result = {'receipt': receipt, 'ack': ack}
            elif op == 'capture_reward':
                # Test semantic signal only; no UI state is intercepted.
                preview, context = capture_inputs(replica)
                identity = secrets.token_hex(16)
                capture.capture(preview, context, capture_id=identity, now_tick=100)
                menu = (identity, preview, context)
                pending = capture.confirm(identity, preview, context, now_tick=100)
                result = client.request(pending.packet())
            elif op == 'repeat_capture':
                identity, preview, context = menu
                pending = capture.confirm(identity, preview, context, now_tick=100)
                result = client.request(pending.packet())
            elif op == 'consume_fence':
                response = client.request(envelope(replica.scope, 'reward_fence_next'))
                if not response.get('ok') or response['challenge'] is None:
                    raise ValueError('No fence challenge')
                body = fence.apply(response['challenge'])
                ack = None if request.get('drop_ack') else client.request(envelope(
                        replica.scope, 'reward_fence_report', body=body, proof=proof(key, body)))
                result = {'body': body, 'ack': ack, 'setters': port.fence_setters,
                          'observations': port.fence_observations}
            elif op == 'sample':
                result = {'sample': port.sample(), 'calls': port.calls, 'setters': port.fence_setters,
                          'observations': port.fence_observations, 'fence': fence.status() if fence else None}
            elif op == 'disconnect':
                client.close()
                client = None
                result = {'closed': True}
            elif op == 'quit':
                if client:
                    client.close()
                if port:
                    port.close()
                print(json.dumps({'ok': True, 'result': {'closed': True}}), flush=True)
                return
            else:
                raise ValueError('Unsupported owned worker operation')
            output = {'ok': True, 'result': result}
        except Exception as error:
            output = {'ok': False, 'error': str(error)}
        print(json.dumps(output, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] != ['--owned-ready-peer']:
        raise SystemExit('Only --owned-ready-peer is supported; not a game adapter')
    worker()
