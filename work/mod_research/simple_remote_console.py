"""Local operator input for the narrow two-PC pilot; never a network listener.

Only adapters retaining the actual room/native owners may supply callbacks.
This module neither attaches to a game nor grants native/menu permissions.
Callbacks must serialize access to their shared room connection. An uncertain
callback is terminal; restarting this console is not permission to replay it.
"""
from copy import deepcopy
import json
import re
import threading

MAX_LINE = 4096


def parse(line):
    if type(line) is not str or len(line) > MAX_LINE:
        raise ValueError('Command must be at most 4096 characters')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON field')
            result[key] = value
        return result
    value = json.loads(line, object_pairs_hook=pairs)
    if type(value) is not dict:
        raise ValueError('Expected a JSON object')
    kind = value.get('action')
    fields = {'action', 'request_id'}
    if kind == 'reward':
        fields |= {'district_id', 'officer_ids'}
    elif kind != 'ready':
        raise ValueError('Only reward and ready are supported')
    if set(value) != fields or type(value.get('request_id')) is not str or not re.fullmatch('[0-9a-f]{32}', value['request_id']):
        raise ValueError('Exact fields and a lowercase 32-digit request_id required')
    if kind == 'reward':
        district, ids = value['district_id'], value['officer_ids']
        if type(district) is not int or not 1 <= district <= 51:
            raise ValueError('district_id must be an integer from 1 to 51')
        if type(ids) is not list or not 1 <= len(ids) <= 16 or any(type(i) is not int or not 1 <= i < 6000 for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('officer_ids must contain 1 to 16 distinct valid integers')
    return value


class Console:
    """One planning window. Start only after the actual planning-open event.

    The cache is local, not a durable game journal. The supplied adapters must
    retain original request IDs and their authoritative execution journal.
    EOF never means Ready. No automatic resend, reconnect, or process shutdown.
    """
    def __init__(self, *, on_reward, on_ready, on_failure, emit):
        if not all(callable(f) for f in (on_reward, on_ready, on_failure, emit)):
            raise TypeError('Four explicit callbacks required')
        self.on_reward, self.on_ready = on_reward, on_ready
        self.on_failure, self.emit = on_failure, emit
        self.lock = threading.RLock()
        self.rows = {}
        self.failed = None
        self.ready = False
        self.closed = False
        self.thread = None
        self.stopping = threading.Event()

    def _failure(self, exc):
        self.failed = self.failed or type(exc).__name__ + ': ' + str(exc)
        self.stopping.set()
        try:
            self.on_failure(exc)
        except BaseException as secondary:
            self.failure_callback_error = repr(secondary)

    def submit_line(self, line):
        # Malformed input has no effects and does not poison a valid session.
        packet = parse(line)
        with self.lock:
            if self.failed or self.closed:
                raise RuntimeError('Operator session ended; no replay')
            identity = packet['request_id']
            old = self.rows.get(identity)
            if old is not None:
                if old['packet'] != packet or old['state'] != 'ACKNOWLEDGED':
                    exc = RuntimeError('Request ID reused or outcome unknown; no replay')
                    self._failure(exc)
                    raise exc
                return dict(event='operator-ack', request_id=identity, duplicate=True,
                            result=deepcopy(old['reply']), game_execution_claimed=False)
            if self.ready:
                raise ValueError('Ready already sent; this planning window is closed')
            if len(self.rows) >= 256:
                raise ValueError('Operator command capacity exhausted')
            row = dict(packet=deepcopy(packet), state='INTENT', reply=None)
            self.rows[identity] = row
            try:
                if packet['action'] == 'reward':
                    reply = self.on_reward(identity, packet['district_id'], list(packet['officer_ids']))
                else:
                    reply = self.on_ready(identity)
                # Reject unsupported receipt types before exposing a cached ACK.
                json.dumps(reply, allow_nan=False)
                row.update(state='ACKNOWLEDGED', reply=deepcopy(reply))
                if packet['action'] == 'ready':
                    self.ready = True
                return dict(event='operator-ack', request_id=identity, duplicate=False,
                            result=deepcopy(reply), game_execution_claimed=False)
            except BaseException as exc:
                row['state'] = 'UNKNOWN'
                self._failure(exc)
                raise

    def start(self, stream):
        with self.lock:
            if self.thread is not None or self.closed or self.failed:
                raise RuntimeError('Console can be started only once')
            self.thread = threading.Thread(target=self._read, args=(stream,), name='san14-local-operator', daemon=True)
            self.thread.start()

    def _read(self, stream):
        try:
            while not self.stopping.is_set():
                line = stream.readline(MAX_LINE + 1)
                if not line:
                    self.emit(dict(event='operator-eof', ready_sent=self.ready, automatic_ready=False))
                    return
                if self.stopping.is_set():
                    return
                if len(line) > MAX_LINE:
                    # Do not interpret the rest of an oversized line as a new command.
                    while line and not line.endswith('\n'):
                        line = stream.readline(MAX_LINE + 1)
                    self.emit(dict(event='operator-rejected', error='Command exceeds size limit'))
                    continue
                try:
                    self.emit(self.submit_line(line))
                except ValueError as exc:
                    if self.failed:
                        raise
                    self.emit(dict(event='operator-rejected', error=str(exc)))
        except BaseException as exc:
            with self.lock:
                if self.failed is None:
                    self._failure(exc)

    def close(self):
        # Do not close process-wide stdin or wait on a blocked readline. A late
        # line cannot invoke an adapter once this lifetime is marked closed.
        with self.lock:
            self.closed = True
            self.stopping.set()
