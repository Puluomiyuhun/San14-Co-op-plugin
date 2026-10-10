"""Trusted local result consumer for the authenticated candidate-only room.

No polling thread, native writer, menu hook or Ready operation is created.
Caller supplies one retained authenticated connection and local ResultChannel.
Submission describes a reward already completed locally. An uncertain reply
holds this consumer and closes its connection; it never repeats game commands.
"""
from copy import deepcopy
import os
from pathlib import Path
import threading

from reward_result_channel import ResultChannel, canonical, digest, hexid, unpack, CAPABILITIES
import reward_result_room as wire


def need(ok, message):
    if not ok: raise ValueError(message)


def write_new(path, value):
    raw = canonical(value)+b'\n'
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


class ResultConsumer:
    """One fresh connection lifetime; local call sites still need writer exclusion."""
    def __init__(self, control, channel, *, result_key, report_key, records):
        need(type(channel) is ResultChannel, 'Exact local result channel required')
        need(getattr(control, 'player_id', None) == channel.local_player, 'Authenticated connection seat differs')
        need(all(type(k) is bytes and len(k) == 32 and any(k) for k in (result_key, report_key)) and
             result_key != report_key, 'Separate result and report keys required')
        need(channel.key == result_key, 'Local channel uses another result key')
        state = channel.status()
        need(not state['held'] and state['events'] == state['sequence'] == state['pending'] == 0,
             'Fresh unresolved-free local channel required')
        self.records = Path(records)
        need(self.records.is_absolute(), 'Absolute fresh consumer records required')
        self.records.mkdir(exist_ok=False)
        self.control, self.channel = control, channel
        self.result_key, self.report_key = result_key, report_key
        self.scope = deepcopy(channel.scope); self.player = channel.local_player
        self.lock = threading.RLock(); self.failed = None; self.closed = False
        self.submissions = {}; self.acknowledgements = []; self.attempts = 0

    def _current(self):
        need(not self.closed and self.failed is None, 'Result consumer is terminal')
        need(getattr(self.control, 'player_id', None) == self.player and self.channel.scope == self.scope and
             self.channel.local_player == self.player and not self.channel.status()['held'],
             'Local result channel or authenticated seat changed')

    def _request(self, value):
        self.attempts += 1
        response = self.control.request(value)
        need(type(response) is dict and response.get('ok') is True, 'Result authority refused request')
        need(all(response.get(k) is v for k,v in CAPABILITIES.items()), 'Authority capabilities differ')
        return response

    def _hold(self, exc):
        self.failed = self.failed or type(exc).__name__
        try: self.control.close()
        except Exception: pass

    def submit_completed(self, event_id, candidate):
        """Submit a captured result. This method does not execute the reward."""
        with self.lock:
            try:
                self._current(); need(hexid(event_id), 'Fresh result event ID required')
                proposal = wire.submission(self.scope, self.player, event_id, candidate, key=self.result_key)
                fingerprint = digest(proposal)
                if event_id in self.submissions:
                    old = self.submissions[event_id]
                    need(old['fingerprint'] == fingerprint and old.get('response') is not None,
                         'Changed or unresolved previous submission')
                    return dict(response=deepcopy(old['response']), duplicate=True, network_resubmitted=False, **CAPABILITIES)
                # The source may already contain its result, so a failure after
                # this intent is not permission to issue the original command.
                write_new(self.records/(event_id+'-submit-intent.json'), proposal)
                self.submissions[event_id] = dict(fingerprint=fingerprint, response=None)
                response = self._request(wire.envelope(self.scope, 'result_submit', proposal=proposal))
                need(response.get('status') in ('WAITING_RECEIPTS', 'PAIRED') and
                     type(response.get('duplicate')) is bool, 'Malformed submission reply')
                body = unpack(response['packet'], key=self.result_key)
                need(body['scope'] == self.scope and body['player'] == self.player and
                     body['event_id'] == event_id and body['delta'] == candidate,
                     'Authority assigned another result')
                write_new(self.records/(event_id+'-submit-reply.json'), response)
                self.submissions[event_id]['response'] = deepcopy(response)
                return dict(response=response, duplicate=False, network_resubmitted=False, **CAPABILITIES)
            except BaseException as exc: self._hold(exc); raise

    def consume_one(self):
        """Dispatch exactly the polled result to its source/receiver journal."""
        with self.lock:
            try:
                self._current()
                response = self._request(wire.envelope(self.scope, 'result_poll'))
                need('packet' in response, 'Missing result offer')
                packet = response['packet']
                need(response.get('status') == ('IDLE' if packet is None else 'WAITING_RECEIPTS'),
                     'Malformed result offer status')
                if packet is None: return dict(status='NO_RESULT_OFFERED', **CAPABILITIES)
                body = unpack(packet, key=self.result_key)
                need(body['scope'] == self.scope, 'Polled result belongs to another lifetime')
                if body['player'] == self.player:
                    prior = self.submissions.get(body['event_id'])
                    need(prior is not None and prior['response'] is not None,
                         'Local source result was not submitted by this consumer')
                    outcome = self.channel.record_local_completed(packet)
                else:
                    outcome = self.channel.receive(packet)
                receipt = outcome['receipt']
                acknowledgement = wire.envelope(self.scope, 'result_ack', receipt=receipt,
                    proof=wire.ack_proof(self.report_key, receipt))
                # Distinct attempts retain duplicate ACK attempts without ever
                # losing the exact durable local journal that produced them.
                serial = len(self.acknowledgements)+1
                path = self.records/('%04d-ack-intent.json'%serial)
                write_new(path, acknowledgement)
                self.acknowledgements.append(dict(event_id=body['event_id'], reply=None))
                reply = self._request(acknowledgement)
                need(type(reply.get('sequence')) is int and reply['sequence'] == body['sequence'] and
                     reply.get('status') in ('WAITING_RECEIPTS', 'PAIRED') and
                     type(reply.get('duplicate')) is bool, 'Acknowledgement reply differs')
                write_new(self.records/('%04d-ack-reply.json'%serial), reply)
                self.acknowledgements[-1]['reply'] = deepcopy(reply)
                return dict(status='LOCAL_RESULT_ACKNOWLEDGED', local=outcome, authority=reply, **CAPABILITIES)
            except BaseException as exc: self._hold(exc); raise

    def status(self):
        with self.lock:
            return dict(player=self.player, held=self.failed is not None, closed=self.closed,
                        network_attempts=self.attempts, submissions=len(self.submissions),
                        ack_attempts=len(self.acknowledgements), **CAPABILITIES)

    def close(self):
        with self.lock:
            if not self.closed:
                self.closed = True; self.control.close()
