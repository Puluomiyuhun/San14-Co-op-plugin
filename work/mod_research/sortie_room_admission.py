"""Fixed recorded sortie -> authenticated room admission and planning barrier.

Reuses PeriodCoordinator pending sets. No native executor, menu interception,
remote success receipt, Ready grant or command-prefix update exists here. The
only releasable outcome is a trusted local rejection BEFORE any native call.
The frozen pilot contract remains exactly Zhang Lu/1300/Wan -> Chang'an; even
an admitted candidate is NOT current-world legality or execution permission.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import json
import sqlite3
import threading

from authoritative_sync import canonical,digest,hexid,next_node
from a_observed_three_room import ObservedRoom
from a_room_three_protocol import BootstrapCoordinator
from pilot_request import validate_payload,GAME_SHA,BASELINE_SHA

FLAGS=dict(native_execution_connected=False,native_execution_authorized=False,
    current_world_legality_verified=False,menu_capture_connected=False,
    generalized_sortie_supported=False,native_gameplay_enabled=False)

def need(value,message):
    if not value:raise ValueError(message)

def envelope(scope,action,**fields):
    return dict(action=action,scope=deepcopy(scope),**fields)

class Admission:
    """Fresh durable admission owner; the existing coordinator owns the barrier."""
    def __init__(self,path,room,coordinator):
        need(type(room) is ObservedRoom and type(coordinator) is BootstrapCoordinator,
             'Exact retained three-checkpoint room/coordinator required')
        self.room,self.coordinator=room,coordinator;self.lock=threading.RLock()
        self.path=Path(path).resolve();self.held=None;self.closed=False;self.scope=None;self.history=[]
        with room.lock,coordinator.lock:
            room._bound(coordinator)
            self.connections={p:room.players[p]['connection'] for p in ('A','B')}
            need(all(self.connections.values()),'Both authenticated connections required')
            need(coordinator.scope['profile']['game_sha256']==GAME_SHA and
                 coordinator.scope['profile']['checkpoint_sha256']==BASELINE_SHA,
                 'Only the fixed sortie reference build and starting checkpoint are admitted')
            self._room_scope=deepcopy(coordinator.scope)
            initial=self._fresh_scope()
            with self.path.open('xb'):pass
            with self.db() as db:
                db.execute('CREATE TABLE metadata(id INTEGER PRIMARY KEY,room_scope TEXT,held TEXT)')
                db.execute('INSERT INTO metadata VALUES(1,?,NULL)',(canonical(self._room_scope).decode(),))
                db.execute('CREATE TABLE proposals(ordinal INTEGER PRIMARY KEY AUTOINCREMENT,player TEXT,request_id TEXT,'
                    'fingerprint TEXT,scope TEXT,payload TEXT,status TEXT,reason TEXT,UNIQUE(player,request_id))')
            self.scope=initial;self.history.append(deepcopy(initial))

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,isolation_level=None,timeout=5)
        db.row_factory=sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE');yield db;db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()

    def _fresh_scope(self):
        c=self.coordinator;self.room._bound(c)
        need(not self.closed and self.held is None and c.scope==self._room_scope and
             all(self.room.players[p]['connection']==self.connections[p] for p in ('A','B')),
             'Room or authenticated connection changed; no reconstruction')
        need(c.bootstrap_completed and c.period in (2,3) and c.phase=='PLANNING' and
             c.connected=={'A','B'} and c.event is None,'Only post-bootstrap planning periods are admitted')
        return dict(schema='san14.fixed-sortie-admission-scope.v1',room_id=self.room.room_id,
            binding_epoch=self.room.binding_epoch,epoch=c.epoch,period=c.period,
            attachments=deepcopy(c.attachments),node=deepcopy(c.node))

    def _rows(self):
        with self.db() as db:return [dict(r) for r in db.execute('SELECT * FROM proposals ORDER BY ordinal')]

    def _current(self):
        need(self.held is None and not self.closed,'Sortie admission is terminal; no replay')
        need(self._fresh_scope()==self.scope,'Sortie binding expired; explicitly bind the next planning period')
        pending={p:{r['request_id'] for r in self._rows() if r['player']==p and r['status']=='QUEUED'} for p in ('A','B')}
        if any(not pending[p]<=self.coordinator.inflight[p] for p in ('A','B')):
            self._hold('Shared pending set lost an admitted sortie')
            raise ValueError(self.held)

    def _hold(self,reason):
        if self.held is not None:return
        self.held=reason
        # Fail closed in memory before attempting failure evidence on disk.
        self.coordinator.ready.clear();self.coordinator.phase='HELD';self.room._held='SORTIE_ADMISSION_UNCERTAIN'
        with self.db() as db:
            db.execute('UPDATE metadata SET held=COALESCE(held,?) WHERE id=1',(reason,))
            db.execute("UPDATE proposals SET status='UNKNOWN',reason=? WHERE status='QUEUED'",(reason,))

    def hold_local(self,reason):
        """Trusted local owner uncertainty; never clear or replay pending effects."""
        need(type(reason) is str and 1<=len(reason)<=200,'Bounded local hold reason required')
        with self.lock,self.room.lock,self.coordinator.lock:self._hold(reason)

    def bind_current(self):
        """After verified checkpoint replacement, bind fresh epoch and attachment.

        This is not a network action. Prior candidates must all be rejected;
        applied sorties cannot yet pass this admission-only component.
        """
        with self.lock,self.room.lock,self.coordinator.lock:
            need(not any(r['status']!='REJECTED' for r in self._rows()),'Unresolved sortie prevents rebinding')
            fresh=self._fresh_scope();old=self.scope;c=self.coordinator
            need(not c.ready and not any(c.inflight.values()) and fresh['period']==old['period']+1 and
                 fresh['epoch']!=old['epoch'] and fresh['node']==next_node(old['node']) and
                 fresh['attachments']['A']==old['attachments']['A'] and
                 fresh['attachments']['B']!=old['attachments']['B'],'Next verified planning lineage required')
            self.scope=fresh;self.history.append(deepcopy(fresh));return deepcopy(fresh)

    def handle(self,player,connection,request):
        with self.lock,self.room.lock,self.coordinator.lock:
            need(player in ('A','B') and self.connections[player]==connection and
                 self.room.players[player]['connection']==connection,'Current authenticated seat required')
            self._current();need(type(request) is dict,'Object request required')
            if request=={'action':'sortie_scope'}:return dict(ok=True,scope=deepcopy(self.scope),**FLAGS)
            need(set(request)=={'action','scope','payload'} and request['action']=='sortie_propose',
                 'Only fixed sortie proposal admission is connected')
            need(canonical(request['scope'])==canonical(self.scope),'Old room, epoch, date or attachment')
            payload=deepcopy(request['payload']);validate_payload(payload)
            need(self.coordinator.scope['bindings'][player]['force_id']==payload['force_id'],
                 'Authenticated seat does not own the fixed sortie force')
            fingerprint=digest(request);request_id=payload['request_id']
            with self.db() as db:
                old=db.execute('SELECT * FROM proposals WHERE player=? AND request_id=?',(player,request_id)).fetchone()
                if old:
                    need(old['fingerprint']==fingerprint,'Request id reused with changed command or planning period')
                    return dict(ok=True,ordinal=old['ordinal'],status=old['status'],duplicate=True,**FLAGS)
                need(player not in self.coordinator.ready,'Ready player cannot admit another sortie')
                need(request_id not in self.coordinator.inflight[player],'Request id belongs to another pending owner')
                need(db.execute('SELECT count(*) FROM proposals').fetchone()[0]<256,'Admission lifetime limit')
                db.execute('INSERT INTO proposals(player,request_id,fingerprint,scope,payload,status) VALUES(?,?,?,?,?,?)',
                    (player,request_id,fingerprint,canonical(self.scope).decode(),canonical(payload).decode(),'QUEUED'))
                ordinal=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            try:
                self.coordinator.set_pending(player,self.scope['epoch'],self.coordinator.inflight[player]|{request_id})
            except BaseException:
                self._hold('Admitted sortie could not acquire the shared pending barrier');raise
            return dict(ok=True,ordinal=ordinal,status='QUEUED',duplicate=False,**FLAGS)

    def reject_local(self,player,request_id,reason):
        """Only local pre-execution rejection releases this proposal's marker."""
        need(type(reason) is str and 1<=len(reason)<=200,'Bounded rejection reason required')
        with self.lock,self.room.lock,self.coordinator.lock:
            self._current()
            with self.db() as db:
                row=db.execute('SELECT * FROM proposals WHERE player=? AND request_id=?',(player,request_id)).fetchone()
                need(row is not None and row['scope']==canonical(self.scope).decode() and row['status']=='QUEUED',
                     'Current queued proposal required; rejection is once only')
                db.execute("UPDATE proposals SET status='REJECTED',reason=? WHERE ordinal=?",(reason,row['ordinal']))
            try:self.coordinator.set_pending(player,self.scope['epoch'],self.coordinator.inflight[player]-{request_id})
            except BaseException:
                self._hold('Local rejection could not release its pending marker');raise
            return dict(status='REJECTED',native_calls=0,**FLAGS)

    def execute(self,*args,**kwargs):
        raise ValueError('Native sortie execution is not connected; admission grants no permission')

    def status(self):
        with self.lock:return dict(scope=deepcopy(self.scope),held=self.held,rows=self._rows(),**FLAGS)

class Endpoint:
    """Wrap the existing endpoint; preserve service cleanup and TLS ownership."""
    def __init__(self,endpoint,admission):
        need(type(admission) is Admission and endpoint.owner.room is admission.room,'Same service endpoint required')
        self.endpoint,self.admission=endpoint,admission
    def authenticate(self,*args):return self.endpoint.authenticate(*args)
    def disconnect(self,player,connection):
        current=player in ('A','B') and self.admission.connections[player]==connection
        try:return self.endpoint.disconnect(player,connection)
        finally:
            if current:self.admission.hold_local('Authenticated sortie peer disconnected')
    def handle(self,player,connection,request):
        try:
            if type(request) is dict and str(request.get('action','')).startswith('sortie_'):
                return self.admission.handle(player,connection,request)
            if type(request) is dict and request.get('action')=='period_ready':
                with self.admission.lock,self.admission.room.lock,self.admission.coordinator.lock:
                    self.admission._current()
                    return self.endpoint.handle(player,connection,request)
            return self.endpoint.handle(player,connection,request)
        except (ValueError,TypeError,KeyError) as exc:return dict(ok=False,error=str(exc),**FLAGS)
