"""Persistent room/download endpoints with one active checkpoint generation.

Only trusted local code can publish an already offered checkpoint. This module
does not produce world receipts, call loaded(), start native work or recover a
disconnected game. A completed prior coordinator receipt is required to rotate.
"""
from copy import deepcopy

from checkpoint_room_artifacts import (ArtifactEnabledRoom, CheckpointArtifactService,
    RoomError, SyncError, PeriodCoordinator, CheckpointPackage, scope_from_room, require)
from authoritative_sync import next_node, hexid


class CheckpointRoom(ArtifactEnabledRoom):
    def __init__(self, manifest):
        super().__init__(manifest)
        self._coordinator = None
        self._scope = None
        self._connections = None
        self._attachments = None
        self._initial = None
        self._generation = 0
        self._held = None
        self._closed = False
        self.download_endpoint = DownloadEndpoint(self)

    def _bound(self, coordinator):
        require(not self._closed and self._held is None, 'Checkpoint room is closed or held')
        require(self._coordinator is coordinator, 'Bind the planning coordinator before simulation; replacement is not recovery')
        if self._coordinator is not None:
            require(scope_from_room(self) == self._scope and
                {p:r['connection'] for p,r in self.players.items()} == self._connections,
                'Original room scope/control connection changed')

    def bind_coordinator(self, coordinator):
        """Bind at initial planning, so even a pre-first-save disconnect is seen."""
        require(type(coordinator) is PeriodCoordinator,'Trusted coordinator required')
        with self.lock, coordinator.lock:
            require(self._coordinator is None and not self._closed and self._held is None,
                    'Coordinator already bound or room unavailable')
            require(coordinator.phase=='PLANNING' and coordinator.period==1 and
                coordinator.connected=={'A','B'} and coordinator.scope==scope_from_room(self),
                'Initial planning room boundary required')
            self._coordinator=coordinator
            self._scope=deepcopy(coordinator.scope)
            self._connections={p:r['connection'] for p,r in self.players.items()}
            self._attachments=deepcopy(coordinator.attachments)
            self._initial=dict(epoch=coordinator.epoch,period=coordinator.period,
                node=deepcopy(coordinator.node),attachments=deepcopy(coordinator.attachments))

    def _next_checkpoint(self, coordinator, package):
        old = self.artifacts
        previous = old.manifest
        receipt = coordinator.applied_receipts.get(old.checkpoint_id)
        require(type(receipt) is dict and set(receipt) == {'player','epoch','checkpoint_id','intent',
            'world_sha256','viewer_force','attachment','host_observation'}, 'Prior checkpoint has no completed receipt')
        require(receipt['player']=='B' and receipt['epoch']==previous['epoch'] and
            receipt['checkpoint_id']==old.checkpoint_id and hexid(receipt['intent'],32) and
            receipt['world_sha256']==previous['world_sha256'] and
            receipt['viewer_force']==self._scope['bindings']['B']['force_id'] and
            receipt['host_observation']==dict(attachment=self._attachments['A'],
                world_sha256=previous['world_sha256'],node=previous['node']), 'Prior receipt lineage differs')
        require(coordinator.attachments['A']==self._attachments['A'] and
            coordinator.attachments['B']==receipt['attachment'] and
            receipt['attachment'] not in self._attachments.values(), 'Native attachment lineage differs')
        current = package.manifest
        require(current['period']==previous['period']+1 and current['epoch']!=previous['epoch'] and
            current['node']==next_node(previous['node']), 'Skipped or stale checkpoint generation')
        require(current['cut']['sequence']>=previous['cut']['sequence'] and
            (current['cut']['sequence']!=previous['cut']['sequence'] or
             current['cut']['prefix_sha256']==previous['cut']['prefix_sha256']), 'Command prefix went backwards or changed')

    def install_offered_checkpoint(self, coordinator, package):
        """Trusted host publication, never a network action or a load receipt."""
        require(type(coordinator) is PeriodCoordinator and type(package) is CheckpointPackage,
                'Trusted coordinator/package required')
        with self.lock, coordinator.lock:
            self._bound(coordinator)
            if self.artifacts is None:
                m=package.manifest
                require(m['epoch']==self._initial['epoch'] and m['period']==self._initial['period'] and
                    m['node']==next_node(self._initial['node']) and
                    coordinator.attachments==self._initial['attachments'],
                    'Initial checkpoint skipped or initial native attachment changed')
            else:
                if package.checkpoint_id == self.artifacts.checkpoint_id:
                    # Idempotent publication must not renew tickets or reset quota.
                    with self.artifacts.lock:self.artifacts._current()
                    return self.artifacts
                self._next_checkpoint(coordinator,package)
            candidate = CheckpointArtifactService(self,coordinator,package)
            # Candidate fully hashes its pinned copy before any old owner retires.
            previous = self.artifacts
            if previous is not None:previous.close()
            self.artifacts = candidate
            self._coordinator = coordinator
            self._scope = deepcopy(candidate.scope)
            self._connections = dict(candidate.connections)
            self._attachments = deepcopy(coordinator.attachments)
            self._generation += 1
            self.download_endpoint._retire_old()
            return candidate

    def disconnect(self, player, connection_id):
        with self.lock:
            row = self.players.get(player)
            was_current = row is not None and row['connection']==connection_id
            super().disconnect(player,connection_id)
            if was_current and self._coordinator is not None:
                with self._coordinator.lock:
                    self._coordinator.connection(player,False)
                    self._held = 'CONTROL_CONNECTION_CHANGED'
                    if self.artifacts:self.artifacts.close()
                    self.download_endpoint._retire_old()
            # Resuming a room seat does not certify recovery of a native world.

    def handle(self, player, connection_id, request):
        with self.lock:
            if type(request) is dict and request.get('action')=='period_ready':
                try:
                    require(set(request)=={'action','epoch','ready'} and player in self.players and
                        self.players[player]['connection']==connection_id,'Invalid ready caller/request')
                    require(self._coordinator is not None,'No bound period coordinator')
                    with self._coordinator.lock:
                        self._bound(self._coordinator)
                        self._coordinator.set_ready(player,request['epoch'],request['ready'])
                        return {'ok':True,'epoch':self._coordinator.epoch,'period':self._coordinator.period,
                            'ready':sorted(self._coordinator.ready),'native_gameplay_enabled':False,
                            'native_simulation_started':False}
                except (RoomError,SyncError) as exc:
                    return {'ok':False,'error':str(exc),'applied_to_game':False}
            if type(request) is dict and request.get('action')=='checkpoint_status':
                try:
                    require(set(request)=={'action'} and player in self.players and
                        self.players[player]['connection']==connection_id,'Invalid checkpoint status caller/request')
                    return {'ok':True,'checkpoint':self.checkpoint_status()}
                except (RoomError,SyncError) as exc:
                    return {'ok':False,'error':str(exc),'applied_to_game':False}
            if type(request) is dict and request.get('action')=='checkpoint_download_offer' and (self._closed or self._held):
                return {'ok':False,'error':'Checkpoint room is closed or held','applied_to_game':False}
            return super().handle(player,connection_id,request)

    def checkpoint_status(self):
        with self.lock:
            m = self.artifacts.manifest if self.artifacts else None
            phase=None;available=False
            if self._coordinator:
                with self._coordinator.lock:
                    phase=self._coordinator.phase
                    if self.artifacts:
                        try:
                            with self.artifacts.lock:self.artifacts._current()
                            available=not self._closed and self._held is None
                        except (RoomError,SyncError):pass
            return dict(generation=self._generation, checkpoint_id=self.artifacts.checkpoint_id if m else None,
                epoch=m['epoch'] if m else None,period=m['period'] if m else None,
                download_available=available,coordinator_phase=phase,
                held_reason=self._held,closed=self._closed,native_gameplay_enabled=False,
                native_full_world_verified=False,automatic_reconnect_recovery=False)

    def close_checkpoints(self):
        with self.lock:
            self._closed=True
            if self._coordinator:
                with self._coordinator.lock:
                    # Revoke queued readiness and unconsumed simulation permits.
                    # This cannot undo a native step already dispatched elsewhere.
                    self._coordinator.connection('A',False)
                    self._coordinator.connection('B',False)
            if self.artifacts:self.artifacts.close()
            self.download_endpoint._retire_old()


class DownloadEndpoint:
    """One stable TLS listener; each connection remains pinned to its generation."""
    def __init__(self, room):
        self.room = room
        self._owners = {}

    def _retire_old(self):
        # Always called under room.lock. No reverse lock acquisition.
        self._owners = {c:s for c,s in self._owners.items()
                        if s is self.room.artifacts and not s.closed}

    def authenticate(self, request, connection):
        with self.room.lock:
            require(type(connection) is str and 0<len(connection)<=128 and connection.isascii(), 'Invalid connection identity')
            require(connection not in self._owners, 'Artifact connection identity already in use')
            require(not self.room._closed and not self.room._held and self.room.artifacts is not None,
                    'No available checkpoint')
            self._retire_old()
            # Prune expired authorization records as well as completed generations.
            current = self.room.artifacts
            with current.lock:
                now=current.clock()
                self._owners={c:s for c,s in self._owners.items()
                              if c in s.channels and s.channels[c]['expires']>now}
            require(len(self._owners)<8,'Too many artifact connection owners')
            result = current.authenticate(request,connection)
            self._owners[connection]=current
            return result

    def handle(self, player, connection, request):
        with self.room.lock:
            owner = self._owners.get(connection)
            if owner is None:
                return {'ok':False,'error':'Retired or unknown artifact connection','applied_to_game':False}
            # Never redirect an old authenticated stream to the latest package.
            return owner.handle(player,connection,request)

    def disconnect(self, player, connection):
        with self.room.lock:
            owner = self._owners.pop(connection,None)
            if owner:owner.disconnect(player,connection)

    def status(self):
        with self.room.lock:
            return dict(active_connection_owners=len(self._owners),native_gameplay_enabled=False)
