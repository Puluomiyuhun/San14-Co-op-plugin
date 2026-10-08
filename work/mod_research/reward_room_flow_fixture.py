"""Explicitly owned offline worlds and a separate TLS guest process; never SAN14."""
from copy import deepcopy
import json
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs' / 'san14-link'))
import authority_reward as reward
import execution_journal as journal
from reward_room_flow import Replica, envelope, report_proof
from room_transport import Client

CONTRACT = 'owned-reward-fixture.v1:date;two-forces(gold,ap,loyalty);not-full-SAN14-world'


def initial_state():
    return {'date': {'year': 203, 'month': 8, 'day': 11, 'period': '中旬'},
            'forces': {'12': {'district': 11, 'city': 19, 'ruler': 666, 'gold': 83308, 'ap': 18,
                              'officers': {'97': 80, '759': 80}},
                       '2': {'district': 2, 'city': 13, 'ruler': 500, 'gold': 20804, 'ap': 10,
                             'officers': {'101': 70, '264': 70, '411': 70}}}}


def context_from_state(state, viewer, force):
    districts, funding, persons = [], {}, []
    for identity, row in state['forces'].items():
        identity = int(identity)
        district = row['district']
        districts.append({'id': district, 'force_id': identity, 'kind_raw': 1,
                          'leader_id': row['ruler'], 'action_points': row['ap'], 'valid': True})
        funding[str(district)] = {'supported': True, 'leader_id': row['ruler'],
                'leader_force_id': identity, 'leader_location_id': row['city'],
                'city': {'id': row['city'], 'name': 'owned fixture city', 'district_id': district,
                         'force_id': identity, 'foothold_id': row['city'], 'gold': row['gold']}}
        for officer, loyalty in row['officers'].items():
            persons.append({'id': int(officer), 'name': 'owned fixture officer', 'district_id': district,
                            'force_id': identity, 'rank_raw': 4, 'native_valid': True,
                            'loyalty': loyalty, 'predicate_eligible': loyalty < 100,
                            'rejection_reason': '' if loyalty < 100 else 'fixture loyalty cap'})
    actor = state['forces'][str(force)]
    context = {'schema': 'san14.authority-reward-context.v1', 'game_sha256': reward.SUPPORTED_SHA256,
               'date': deepcopy(state['date']), 'viewer_force_id': viewer, 'command_force_id': force,
               'ruler_id': actor['ruler'], 'state_stack': list(reward.PLANNING_STACK), 'strategy_mode': 2,
               'main_district_id': actor['district'], 'districts': districts, 'funding': funding,
               'persons': persons, 'native_action_cost': 1}
    context['context_sha256'] = reward.context_hash(context)
    return context


class ModelPort:
    """Small stateful business substitute. +4 is ONLY this fixture's rule."""
    def __init__(self, viewer):
        self.viewer = viewer
        self.attachment_id = secrets.token_hex(16)
        self.state = initial_state()
        self.calls = 0
        self.fail_after_effect = False

    def observe(self):
        return journal.digest(self.state)

    def sample(self):
        return deepcopy(self.state)

    def context(self, force):
        return context_from_state(self.state, self.viewer, force)

    def execute(self, command):
        reward.validate_reward(command, self.context(command['force_id']), command['force_id'])
        row = self.state['forces'][str(command['force_id'])]
        row['gold'] -= 100 * len(command['officer_ids'])
        row['ap'] -= 1
        for identity in command['officer_ids']:
            row['officers'][str(identity)] = min(100, row['officers'][str(identity)] + 4)
        self.calls += 1
        if self.fail_after_effect:
            raise RuntimeError('Injected exception after owned model writes')
        return {'source': 'python-business-substitute', 'native_returned': True,
                'args_released': True, 'owned_slot_cleared': True}

    def close(self):
        pass


def worker():
    port = client = replica = None
    adapter_key = secrets.token_bytes(32)
    def report_packet():
        report = replica.report()
        return envelope(replica.scope, 'reward_report', report=report, proof=report_proof(adapter_key, report))
    for line in sys.stdin:
        try:
            message = json.loads(line)
            op = message['op']
            if op == 'open':
                if message.get('native_exe'):
                    from reward_room_flow_native_port import NativePort
                    port = NativePort(message['native_exe'], 2, Path(message['run_dir']))
                else:
                    port = ModelPort(2)
                # This stdio supervisor channel is separate from the room TLS
                # client. The key is never returned by a room endpoint or log.
                result = {'attachment': port.attachment_id, 'initial': port.observe(),
                          'trusted_report_key': adapter_key.hex()}
            elif op == 'connect':
                client = Client(**message['config'])
                result = {'player_id': client.player_id, 'state': client.state}
            elif op == 'request':
                result = client.request(message['packet'])
            elif op == 'attach':
                response = client.request({'action': 'reward_scope'})
                if not response.get('ok') or response['attachment'] != port.attachment_id:
                    raise ValueError('Guest scope/attachment mismatch')
                replica = Replica(message['journal'], response['scope'], 'B', port)
                result = client.request(report_packet())
            elif op == 'consume':
                incoming = client.request(envelope(replica.scope, 'reward_next'))
                if not incoming.get('ok'):
                    raise ValueError(str(incoming))
                if incoming['intent'] is None:
                    raise ValueError('No incoming intent')
                receipt = replica.apply(incoming['intent'])
                report = replica.report()
                ack = None if message.get('drop_ack') else client.request(report_packet())
                result = {'receipt': receipt, 'report': report, 'ack': ack, 'calls': port.calls}
            elif op == 'report':
                result = client.request(report_packet())
            elif op == 'sample':
                result = {'sample': port.sample(), 'calls': port.calls, 'journal': replica.journal.status() if replica else None}
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
                raise ValueError('Unknown owned worker operation')
            output = {'ok': True, 'result': result}
        except Exception as error:
            output = {'ok': False, 'error': str(error)}
        print(json.dumps(output, ensure_ascii=True, allow_nan=False), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] != ['--owned-guest-worker']:
        raise SystemExit('Only --owned-guest-worker is supported; this is not a game adapter')
    worker()
