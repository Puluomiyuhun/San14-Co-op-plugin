"""Serialized room requests plus idle heartbeat, no automatic request replay.

Owns a control Client only; checkpoint transfers use a separate connection.
A failed I/O latches uncertainty and stops. Resume/native recovery is explicit.
"""
from copy import deepcopy
import threading
import time

from checkpoint_room_artifacts import require
from room_transport import Client


class RoomConnection:
    def __init__(self, host, port, fingerprint, greeting, *, heartbeat_seconds=5):
        require(type(heartbeat_seconds) in (int,float) and 1<=heartbeat_seconds<=10,
                'Heartbeat interval must be 1..10 seconds')
        require(type(greeting) is dict and greeting.get('method') in ('host','join','resume'),
                'Room control greeting required; artifact clients are separate')
        self._lock=threading.RLock()
        self._stop=threading.Event()
        self._closed=False
        self._closing=False
        self._close_error=None
        self._fault=None
        self._heartbeats=0
        self._request_count=0
        self._interval=heartbeat_seconds
        self._client=Client(host,port,fingerprint,greeting)
        self._last_success=time.monotonic()
        self._thread=threading.Thread(target=self._heartbeat,name='san14-room-heartbeat',daemon=True)
        try:self._thread.start()
        except BaseException:
            self._client.close();self._closed=True
            raise

    @property
    def player_id(self):return self._client.player_id

    @property
    def resume_token(self):
        # Caller-owned credential, intentionally absent from status and logs.
        return self._client.resume_token

    def _request(self, packet, *, heartbeat=False):
        require(not self._closed and not self._stop.is_set() and self._fault is None,
                'Room connection is closed or uncertain; no automatic retry')
        try:
            # One lock covers the whole write/read exchange; heartbeat cannot
            # consume the reply to a player's command or interleave its bytes.
            reply=self._client.request(packet)
            if heartbeat:
                require(reply.get('ok') is True and type(reply.get('state')) is dict and
                        reply['state'].get('you')==self.player_id,'Invalid heartbeat response')
                self._heartbeats+=1
            self._last_success=time.monotonic()
            self._request_count+=1
            return reply
        except BaseException as exc:
            self._fault={'kind':type(exc).__name__,'request_may_have_been_sent':True,
                         'was_heartbeat':heartbeat,'automatically_retried':False}
            self._stop.set()
            try:self._client.close()
            except Exception:pass
            raise

    def request(self, packet):
        with self._lock:return self._request(packet)

    def _heartbeat(self):
        while not self._stop.wait(self._interval):
            try:
                with self._lock:
                    if self._stop.is_set():return
                    if time.monotonic()-self._last_success>=self._interval:
                        self._request({'action':'status'},heartbeat=True)
            except BaseException:
                # Fault is latched by _request; never resume/replay automatically.
                return

    def status(self):
        with self._lock:
            return dict(player_id=self.player_id,transport_open=not self._stop.is_set() and not self._closed and self._fault is None,
                closed=self._closed,heartbeat_count=self._heartbeats,successful_requests=self._request_count,
                last_success_age_seconds=round(time.monotonic()-self._last_success,3),
                fault=deepcopy(self._fault),closing=self._closing,close_error=self._close_error,
                automatic_reconnect=False,native_gameplay_enabled=False)

    def close(self):
        self._stop.set()
        error=None
        with self._lock:
            self._closing=True
            if not self._closed:
                try:
                    self._client.close()
                    self._closed=True
                    self._close_error=None
                except BaseException as exc:
                    self._close_error=type(exc).__name__
                    error=exc
            # An explicit later close may retry resource release only. Requests
            # remain disabled; this never retries a command or reconnects.
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout=6)
            require(not self._thread.is_alive(),'Room heartbeat did not stop')
        if error is not None:raise error
        return self.status()
