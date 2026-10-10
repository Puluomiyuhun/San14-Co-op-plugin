"""Three-checkpoint two-seat TLS owner for the observed no-command pilot.

No process access, native calls, key distribution, automatic reconnect or game
advance. The host's explicit ready request and B's ready request remain separate.
"""
from copy import deepcopy
from pathlib import Path
import json
import secrets
import socket
import socketserver
import threading
import time

from room_transport import Server, Client, make_certificate, MAX_PACKET
from checkpoint_room_client import RoomConnection
from authoritative_sync import canonical, scope_from_room, validate_node
from a_room_three_protocol import BootstrapCoordinator
from a_observed_three_room import ObservedRoom
from b_warm_world import CONTRACT


def need(value, message):
    if not value: raise ValueError(message)


def request_ok(control, packet):
    result = control.request(packet)
    need(result.get('ok') is True, 'Room request rejected: ' + str(result.get('error')))
    return result


def selection(control, action, force=None):
    state = request_ok(control, {'action':'status'})['state']
    value = dict(action=action, request_id=secrets.token_hex(16), expected_revision=state['revision'])
    if force is not None: value['force_id'] = force
    return request_ok(control, value)


class _Endpoint:
    def __init__(self, owner): self.owner = owner
    def authenticate(self, *args): return self.owner.room.authenticate(*args)
    def disconnect(self, player, connection):
        room=self.owner.room
        with room.lock:
            current=player=='B' and room.players.get('B',{}).get('connection')==connection
            try:return room.disconnect(player,connection)
            finally:
                if current:self.owner.guest_disconnected.set()
    def handle(self, player, connection, packet):
        room = self.owner.room
        if type(packet) is not dict or packet.get('action') not in ('pilot_context','pilot_guest_finished','pilot_host_finished'):
            return room.handle(player, connection, packet)
        try:
            with room.lock:
                need(player in room.players and room.players[player]['connection'] == connection,
                     'Current authenticated seat required')
                if packet['action']=='pilot_host_finished':
                    need(player=='B' and packet=={'action':'pilot_host_finished'},'Exact B close-barrier query required')
                    return dict(ok=True,host_finished=self.owner.host_finished,
                        native_cleanup_independently_verified=False)
                if packet['action'] == 'pilot_guest_finished':
                    need(player == 'B' and set(packet) == {'action','formal_completions',
                        'native_cleanup_verified','retained_native_state'}, 'Exact B finish notification required')
                    need(type(packet['formal_completions']) is int and 0 <= packet['formal_completions'] <= 3 and
                         all(type(packet[k]) is bool for k in ('native_cleanup_verified','retained_native_state')),
                         'Exact finish coverage required')
                    c = self.owner.coordinator
                    need(c is not None, 'No bound cleanup context')
                    with c.lock:
                        need(packet['formal_completions'] == len(c.applied_receipts), 'Finish count differs')
                        if packet['native_cleanup_verified']:
                            room._bound(c)
                            need(self.owner.failure is None and c.bootstrap_completed and c.phase=='PLANNING' and
                                 c.connected=={'A','B'} and not c.ready and not any(c.inflight.values()) and c.event is None and
                                 packet['formal_completions'] == 3 and c.period == 4 and
                                 not packet['retained_native_state'], 'Successful cleanup requires three completions')
                        need(self.owner.guest_finished is None, 'Finish notification already attempted')
                        self.owner.guest_finished = deepcopy(packet)
                        if not packet['native_cleanup_verified']:
                            room._held='GUEST_NATIVE_CLEANUP_INCOMPLETE'
                            c.ready.clear();c.phase='HELD'
                            if room.artifacts is not None:room.artifacts.close()
                            room.download_endpoint._retire_old()
                    return dict(ok=True, recorded=True, native_cleanup_independently_verified=False)
                need(packet == {'action':'pilot_context'}, 'Exact context request required')
                need(self.owner.failure is None, 'Room owner failed; retain local state')
                c = self.owner.coordinator
                if c is None: return dict(ok=True, context=None, native_gameplay_enabled=False)
                with c.lock:
                    room._bound(c)
                    context = dict(scope=deepcopy(c.scope), epoch=c.epoch, period=c.period,
                        node=deepcopy(c.node), attachments=deepcopy(c.attachments), phase=c.phase,
                        checkpoint_id=c.checkpoint_id, manifest=deepcopy(c.manifest))
                    return dict(ok=True, context=context, native_gameplay_enabled=False)
        except (ValueError, RuntimeError) as exc:
            return dict(ok=False, error=str(exc), native_gameplay_enabled=False)


class _Handler(socketserver.BaseRequestHandler):
    """Interruptible TLS reads without socket.makefile's retained I/O handle.

    Keep partial frames across short timeouts, but never replay a request or
    wait indefinitely for a newline. The original canonical packet limit and
    room authentication/dispatch are unchanged.
    """
    def handle(self):
        connection=secrets.token_hex(16);player=None;buffer=bytearray()
        def read():
            deadline=time.monotonic()+30
            while True:
                if b'\n' in buffer:
                    frame,_,tail=buffer.partition(b'\n');buffer[:]=tail
                    need(len(frame)+1<=MAX_PACKET,'Packet exceeds TLS limit')
                    value=json.loads(frame);need(type(value) is dict,'Object packet required');return value
                need(len(buffer)<=MAX_PACKET,'Packet exceeds TLS limit')
                if self.server.closing.is_set():raise EOFError()
                need(time.monotonic()<deadline,'Incomplete or idle TLS packet')
                self.request.settimeout(.25)
                try:data=self.request.recv(min(4096,MAX_PACKET+1-len(buffer)))
                except socket.timeout:continue
                if not data:raise EOFError()
                buffer.extend(data)
        def write(value):
            raw=canonical(value)+b'\n';need(len(raw)<=MAX_PACKET,'Response exceeds TLS limit')
            self.request.settimeout(3);self.request.sendall(raw)
        try:
            greeting=self.server.room.authenticate(read(),connection);player=greeting['player_id']
            write(dict(ok=True,**greeting))
            while not self.server.closing.is_set():
                packet=read()
                # Resolve the current endpoint after waiting for a packet: the
                # bootstrap owner can mount reward planning while we wait.
                write(self.server.room.handle(player,connection,packet))
        except (EOFError,OSError):pass
        except (ValueError,TypeError) as exc:
            try:write(dict(ok=False,error=str(exc),applied_to_game=False))
            except OSError:pass
        finally:
            if player is not None:self.server.room.disconnect(player,connection)


class _Server(Server):
    """Track this owner's transport sockets so close never leaves live handlers."""
    def __init__(self, *args):
        self.connections = set(); self.connection_lock = threading.Lock();self.closing=threading.Event()
        super().__init__(*args)
        self.RequestHandlerClass=_Handler
    def process_request(self, request, address):
        with self.connection_lock: self.connections.add(request)
        try: return super().process_request(request, address)
        except BaseException:
            with self.connection_lock: self.connections.discard(request)
            raise
    def shutdown_request(self, request):
        try: super().shutdown_request(request)
        finally:
            with self.connection_lock: self.connections.discard(request)
    def drain(self):
        # Wake the bounded read loop; do not close a makefile-backed SSL handle
        # underneath an uninterruptible Windows read.
        self.closing.set()
        deadline = time.monotonic() + 5
        while True:
            with self.connection_lock:
                if not self.connections: return
            need(time.monotonic() < deadline, 'TLS handlers still pending')
            time.sleep(.02)


class HostService:
    """Owns only network resources; native cleanup belongs to each launcher."""
    def __init__(self, manifest, node, *, directory, listen_host, advertise_host,
                 control_port, download_port, host_force=12, guest_force=2):
        validate_node(node)
        need(host_force != guest_force and all(type(x) is int for x in (host_force,guest_force)),
             'Two distinct configured forces required')
        need(type(listen_host) is str and listen_host and type(advertise_host) is str and advertise_host
             and advertise_host not in ('0.0.0.0','::'), 'Explicit bind and reachable advertised host required')
        need(all(type(p) is int and 0 <= p < 65536 for p in (control_port,download_port)) and
             (not control_port or control_port != download_port), 'Separate valid ports required')
        self.room = ObservedRoom(manifest); self.node = deepcopy(node)
        need(host_force in self.room.catalog and guest_force in self.room.catalog, 'Configured forces absent')
        self.host_force, self.guest_force = host_force, guest_force
        self.directory = Path(directory).resolve(); self.directory.mkdir(exist_ok=False, parents=True)
        self.coordinator = None; self.failure = None; self.servers = []; self.control = None
        self.guest_finished = None;self.host_finished=False;self.guest_disconnected=threading.Event()
        self._closed = False; self._stop = threading.Event(); self._thread = None
        self._seal_started = set(); self._host_ready = set(); self._state_lock = threading.RLock()
        try:
            cert, key, fp = make_certificate(self.directory/'tls')
            for port, endpoint in ((control_port,_Endpoint(self)),(download_port,self.room.download_endpoint)):
                server = _Server((listen_host,port),endpoint,cert,key)
                thread = threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True)
                self.servers.append((server,thread)); thread.start()
            local_host = '127.0.0.1' if listen_host == '0.0.0.0' else listen_host
            self.control = RoomConnection(local_host,self.servers[0][0].server_address[1],fp,
                dict(method='host',credential=self.room.host_token,profile=manifest['profile']))
            selection(self.control,'select_force',host_force)
            self.invitation = dict(schema='san14.observed-three-pilot-invitation.v1',host=advertise_host,
                control_port=self.servers[0][0].server_address[1],download_port=self.servers[1][0].server_address[1],
                fingerprint=fp,profile=deepcopy(manifest['profile']),credential=self.room.invite,force_id=guest_force)
            self._thread = threading.Thread(target=self._monitor,name='san14-observed-room-owner',daemon=True)
            self._thread.start()
        except BaseException:
            self.close(); raise

    def _monitor(self):
        try:
            while not self._stop.wait(.05):
                if self.coordinator is None:
                    # Guest is configured to select and confirm before A confirms.
                    # No simultaneous revision-changing selection requests exist.
                    with self.room.lock:
                        b = self.room.players.get('B')
                        can_bind = b is not None and b['connection'] is not None and b['confirmed']
                        if can_bind: need(b['force'] == self.guest_force, 'Guest selected another force')
                    if can_bind:
                        selection(self.control,'confirm_force')
                        with self.room.lock:
                            scope = scope_from_room(self.room)
                            # Bootstrap identity of the configured starting FILE,
                            # not a claim of live world equality. First native
                            # export replaces this with its actual partial digest.
                            c = BootstrapCoordinator(scope,CONTRACT,self.room.manifest['profile']['checkpoint_sha256'],
                                {p:secrets.token_hex(16) for p in ('A','B')},self.node)
                            self.room.bind_coordinator(c); self.coordinator = c
                else:
                    with self.room.lock,self.coordinator.lock:
                        if self.guest_finished is not None: return
                        c = self.coordinator; self.room._bound(c)
                        token=(c.period,c.epoch)
                        if token in self._host_ready and token not in self._seal_started and c.ready == {'A','B'}:
                            need(c.bootstrap_completed and c.period in (2,3) and c.phase == 'PLANNING'
                                 and len(c.applied_receipts) == c.period-1 and not any(c.inflight.values()),
                                 'Cannot seal outside a completed bounded no-command period')
                            self._seal_started.add(token)
                            c.begin_simulation(c.seal_inputs())
        except BaseException as exc:
            self.failure = type(exc).__name__+': '+str(exc)
            with self.room.lock:
                self.room._held = 'NETWORK_OWNER_FAILED'
                if self.coordinator is not None:
                    with self.coordinator.lock:
                        self.coordinator.ready.clear(); self.coordinator.phase = 'HELD'

    def wait_bound(self, timeout=600):
        need(type(timeout) is int and 1 <= timeout <= 1800, 'Bounded room wait required')
        deadline = time.monotonic() + timeout
        while self.coordinator is None:
            need(self.failure is None and not self._closed, 'Room owner unavailable: '+str(self.failure))
            need(time.monotonic() < deadline, 'Guest selection timed out; do not reconnect')
            time.sleep(.1)
        need(self.failure is None, 'Room binding failed')
        return self.coordinator

    def ready_for_turn(self):
        """Called once per period by the explicit A entry after loaded1/loaded2.

        Nonblocking: A's native pipe heartbeat must continue while B works.
        Old ready/seal tokens remain recorded; neither can authorize a new epoch.
        Only the monitor seals after both actual current period_ready requests.
        """
        c = self.coordinator
        need(c is not None, 'Room not bound')
        with self._state_lock:
            with self.room.lock,c.lock:
                self.room._bound(c)
                token=(c.period,c.epoch)
                need(self.failure is None and self.guest_finished is None and not self.host_finished and
                     token not in self._host_ready and token not in self._seal_started and
                     c.bootstrap_completed and c.period in (2,3) and c.phase == 'PLANNING' and
                     len(c.applied_receipts) == c.period-1,
                     'Host ready once per bounded period after formal completion')
                epoch = c.epoch
            request_ok(self.control,dict(action='period_ready',epoch=epoch,ready=True))
            self._host_ready.add(token)

    def wait_guest_finished(self, timeout=600):
        need(type(timeout) is int and 1 <= timeout <= 1800, 'Bounded guest cleanup wait required')
        deadline = time.monotonic() + timeout
        while self.guest_finished is None:
            need(self.failure is None and not self._closed, 'Room failed before B cleanup notification')
            need(time.monotonic() < deadline, 'B cleanup notification missing; native result remains separate')
            time.sleep(.1)
        return deepcopy(self.guest_finished)

    def mark_host_finished(self):
        """The owning native entry returned; not a native-cleanup success claim."""
        with self.room.lock:
            need(not self.host_finished,'Host finish barrier already published')
            self.host_finished=True

    def wait_guest_disconnected(self, timeout=600):
        need(type(timeout) is int and 1<=timeout<=1800 and self.host_finished,
             'Bounded close wait after host entry completion required')
        deadline=time.monotonic()+timeout
        while not self.guest_disconnected.is_set():
            need(time.monotonic()<deadline,'B did not close after host completion; retain network evidence')
            time.sleep(.1)
        return dict(guest_control_disconnected=True,native_cleanup_independently_verified=False)

    def close(self):
        self._stop.set(); errors = []
        if self._thread is not None:
            self._thread.join(timeout=6)
            if self._thread.is_alive(): errors.append('room owner thread retained')
        self.room.close_checkpoints()
        if self.control is not None:
            try: self.control.close()
            except BaseException as exc: errors.append(type(exc).__name__+': control close')
        for server,thread in reversed(self.servers):
            try:
                if thread.is_alive(): server.shutdown(); thread.join(timeout=5)
                server.drain(); server.server_close()
                need(not thread.is_alive(), 'Listener thread retained')
            except BaseException as exc: errors.append(type(exc).__name__+': listener close: '+str(exc))
        self._closed = not errors
        return dict(network_closed=self._closed,errors=errors,native_cleanup_claimed=False)


def validate_invitation(value):
    need(type(value) is dict and set(value) == {'schema','host','control_port','download_port',
        'fingerprint','profile','credential','force_id'} and value['schema']=='san14.observed-three-pilot-invitation.v1',
        'Exact pilot invitation required')
    need(type(value['host']) is str and value['host'] and value['host'] not in ('0.0.0.0','::') and
         all(type(value[k]) is int and 0 < value[k] < 65536 for k in ('control_port','download_port')) and
         value['control_port'] != value['download_port'], 'Explicit remote host and separate ports required')
    need(type(value['fingerprint']) is str and len(value['fingerprint'])==64 and
         all(c in '0123456789abcdef' for c in value['fingerprint']), 'Pinned certificate required')
    need(type(value['credential']) is str and 1 <= len(value['credential']) <= 256 and
         type(value['force_id']) is int and 1 <= value['force_id'] <= 51,
         'Guest invitation credential and configured force required')
    need(type(value['profile']) is dict, 'Compatibility profile required')
    return deepcopy(value)


class GuestLink:
    def __init__(self, invitation):
        self.invitation = validate_invitation(invitation); n = self.invitation
        self.control = RoomConnection(n['host'],n['control_port'],n['fingerprint'],
            dict(method='join',credential=n['credential'],profile=n['profile']))
        try:
            need(self.control.player_id == 'B', 'Expected B seat')
            selection(self.control,'select_force',n['force_id']); selection(self.control,'confirm_force')
        except BaseException:
            self.control.close(); raise
    def connect_download(self, token):
        n = self.invitation
        return Client(n['host'],n['download_port'],n['fingerprint'],
            dict(method='checkpoint_download',credential=token,profile=n['profile']))
    def wait_context(self, timeout=600):
        need(type(timeout) is int and 1 <= timeout <= 1800, 'Bounded context wait required')
        deadline = time.monotonic() + timeout
        while True:
            reply = request_ok(self.control,{'action':'pilot_context'})
            if reply['context'] is not None: return reply['context']
            need(time.monotonic() < deadline, 'Authority context unavailable')
            time.sleep(.1)
    def close(self): return self.control.close()


def join_guest(invitation): return GuestLink(invitation)
