"""Signed completed-reward candidates, never reward-command replay.

This separate contract has no Room Ready/start permission. A trusted local sink
owns compare/apply serialization. No production game-memory sink or UI refresh
exists here. SQLite intent and game memory cannot share a transaction: any
uncertain outcome holds the entire lifetime and is never retried automatically.
The persistent local seat prevents loopback application. A shared HMAC key does
not independently authenticate which peer sent a packet; a future Room adapter
must bind the TLS connection identity before exposing this local API. Sequence
ordering is supplied by that trusted caller, not assigned by this channel.
"""
from abc import ABC,abstractmethod
from contextlib import contextmanager
from copy import deepcopy
import hashlib,hmac,json,re,sqlite3,threading
from pathlib import Path
import reward_result_delta as delta_api

SCHEMA='san14.reward-result-channel.v1'
SCOPE='san14.reward-result-scope.v1'
DOMAIN=b'san14.reward-result-channel.v1\0'
MAX_PACKET=49152
CAPABILITIES=dict(result_candidates_only=True,native_sink_implemented=False,
    native_completion_verified=False,ui_refresh_verified=False,full_world_verified=False,
    reward_command_replayed=False,room_ready_permission=False,full_reward_effects_verified=False)


class ResultError(ValueError):pass
class ResultHeld(ResultError):pass
def need(value,message):
    if not value:raise ResultError(message)
def canonical(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
    need(len(raw)<=MAX_PACKET,'Result packet too large');return raw
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def hexid(value,n=32):return type(value) is str and re.fullmatch('[0-9a-f]{%d}'%n,value) is not None
def integer(value,low,high):return type(value) is int and low<=value<=high
def date(value):
    need(type(value) is dict and set(value)=={'year','month','day','period'},'Exact planning date required')
    need(integer(value['year'],1,9999) and integer(value['month'],1,12) and
         value['day'] in (1,11,21) and type(value['day']) is int and
         value['period']=={1:'上旬',11:'中旬',21:'下旬'}[value['day']],'Invalid planning date')
    return deepcopy(value)


def validate_scope(value):
    need(type(value) is dict and set(value)=={'schema','room_id','binding_epoch','timeline_epoch',
         'attachments','actors','date','projection_contract'} and value['schema']==SCOPE,'Exact result scope required')
    need(all(hexid(value[k]) for k in ('room_id','binding_epoch','timeline_epoch')),'Invalid scope epoch')
    need(type(value['attachments']) is dict and set(value['attachments'])=={'A','B'} and
         all(hexid(x) for x in value['attachments'].values()),'Exact local attachment pair required')
    need(type(value['actors']) is dict and set(value['actors'])=={'A','B'},'Two authorized actors required')
    for actor in value['actors'].values():
        need(type(actor) is dict and set(actor)=={'force_id','main_district_id'} and
             all(integer(x,1,51) for x in actor.values()),'Bound force/main district required')
    need(value['actors']['A']['force_id']!=value['actors']['B']['force_id'],'Actors must differ')
    date(value['date'])
    from reward_observed_context import CONTRACT
    need(value['projection_contract']==CONTRACT,'Only the declared reward projection is supported')
    return deepcopy(value)


def _key(key):need(type(key) is bytes and len(key)==32 and any(key),'Private 32-byte result key required')
def _body(scope,player,event_id,sequence,delta):
    scope=validate_scope(scope)
    need(player in ('A','B') and hexid(event_id) and integer(sequence,1,2**63-1),'Event identity/sequence invalid')
    need(type(delta) is dict and delta.get('date')==scope['date'],'Result date differs')
    actor=scope['actors'][player]
    need(delta.get('actor')==dict(force_id=actor['force_id'],district_id=actor['main_district_id']),
         'Result actor is not authorized by this scope')
    return dict(schema=SCHEMA,scope=scope,player=player,event_id=event_id,sequence=sequence,
                actor=deepcopy(delta['actor']),date=deepcopy(scope['date']),delta=deepcopy(delta))


def packet(scope,player,event_id,sequence,delta,*,key):
    _key(key);body=_body(scope,player,event_id,sequence,delta)
    return dict(body=body,proof=hmac.new(key,DOMAIN+canonical(body),hashlib.sha256).hexdigest())


def unpack(value,*,key):
    _key(key);need(type(value) is dict and set(value)=={'body','proof'} and hexid(value['proof'],64),'Signed result envelope required')
    need(hmac.compare_digest(value['proof'],hmac.new(key,DOMAIN+canonical(value['body']),hashlib.sha256).hexdigest()),'Result signature differs')
    b=value['body'];need(type(b) is dict and set(b)=={'schema','scope','player','event_id','sequence','actor','date','delta'},'Result body fields differ')
    expected=_body(b['scope'],b['player'],b['event_id'],b['sequence'],b['delta'])
    need(b==expected,'Result body binding differs');return deepcopy(b)


class LocalResultSink(ABC):
    """Trusted local capability, never constructed from peer JSON.

    Implementations must serialize every covered writer on lock and compare all
    expected_before values before an atomic replacement. This contract does not
    claim arbitrary native memory writes are atomic. Only owned dict tests exist.
    """
    def __init__(self):self.lock=threading.RLock()
    @abstractmethod
    def current_scope(self):pass
    @abstractmethod
    def snapshot(self):pass
    @abstractmethod
    def apply_atomic(self,expected_before,expected_after):pass


class ResultChannel:
    def __init__(self,path,scope,*,local_player,key,sink,create=False):
        need(isinstance(sink,LocalResultSink) and hasattr(sink,'lock'),'Typed trusted local sink required')
        need(type(local_player) is str and local_player in ('A','B'),'Exact local seat required')
        _key(key);self.scope=validate_scope(scope);self.key=key;self.sink=sink
        self.local_player=local_player
        self.lock=threading.RLock();self.failed=None;self.closed=False;self.path=Path(path)
        if create:
            with self.path.open('xb'):pass
        else:need(self.path.is_file(),'Existing result journal required')
        self.db=sqlite3.connect(self.path,timeout=5,isolation_level=None,check_same_thread=False)
        try:
            self.db.execute('PRAGMA synchronous=FULL');self.db.execute('PRAGMA journal_mode=DELETE')
            if create:
                with self._transaction():
                    self.db.execute('CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1),scope TEXT NOT NULL,key_hash TEXT NOT NULL,local_player TEXT NOT NULL,sequence INTEGER NOT NULL,held TEXT)')
                    self.db.execute('CREATE TABLE events (event_id TEXT PRIMARY KEY,sequence INTEGER UNIQUE NOT NULL,body_sha TEXT NOT NULL,body TEXT NOT NULL,origin TEXT NOT NULL,state TEXT NOT NULL,result TEXT)')
                    self.db.execute('INSERT INTO metadata VALUES(1,?,?,?,0,NULL)',(canonical(self.scope).decode(),hashlib.sha256(DOMAIN+key).hexdigest(),local_player))
            row=self.db.execute('SELECT scope,key_hash,local_player FROM metadata WHERE id=1').fetchone()
            need(row==(canonical(self.scope).decode(),hashlib.sha256(DOMAIN+key).hexdigest(),local_player),'Journal scope/key/local seat differs')
        except BaseException:self.db.close();raise

    @contextmanager
    def _transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:yield;self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise

    def _ready(self):
        need(not self.closed and self.failed is None,'Result channel is terminal or closed')
        sequence,held=self.db.execute('SELECT sequence,held FROM metadata WHERE id=1').fetchone()
        if held or self.db.execute("SELECT 1 FROM events WHERE state='INTENT' LIMIT 1").fetchone():
            raise ResultHeld('Held or unresolved intent; manual reconciliation required')
        return sequence

    def _hold(self,exc):
        self.failed=self.failed or type(exc).__name__
        try:
            with self._transaction():self.db.execute('UPDATE metadata SET held=COALESCE(held,?) WHERE id=1',(self.failed,))
        except BaseException as secondary:self.hold_record_error=type(secondary).__name__

    def _current(self):
        need(validate_scope(self.sink.current_scope())==self.scope,'Local date, scope or attachment changed')

    def _reserve(self,body,origin):
        with self._transaction():
            last=self._ready();need(body['sequence']==last+1,'Result sequence is not next')
            self.db.execute('INSERT INTO events VALUES(?,?,?,?,?,\'INTENT\',NULL)',
                (body['event_id'],body['sequence'],digest(body),canonical(body).decode(),origin))

    def _persist_result(self,body,receipt):
        with self._transaction():
            need(self.db.execute('SELECT held FROM metadata WHERE id=1').fetchone()==(None,), 'Journal was held concurrently')
            cursor=self.db.execute("UPDATE events SET state='COMPLETE',result=? WHERE event_id=? AND body_sha=? AND state='INTENT'",
                (canonical(receipt).decode(),body['event_id'],digest(body)))
            need(cursor.rowcount==1,'Reserved result disappeared')
            self.db.execute('UPDATE metadata SET sequence=? WHERE id=1',(body['sequence'],))

    def _process(self,value,local):
        with self.sink.lock,self.lock:
            try:
                self._ready();body=unpack(value,key=self.key)
                need((body['player']==self.local_player)==local,'Result direction differs from the bound local seat')
                need(body['scope']==self.scope,'Packet belongs to another result scope');self._current()
                old=self.db.execute('SELECT body_sha,state,result,origin FROM events WHERE event_id=?',(body['event_id'],)).fetchone()
                origin='LOCAL_ALREADY_COMPLETED' if local else 'REMOTE_RESULT_APPLICATION'
                if old:
                    need(old[0]==digest(body) and old[1]=='COMPLETE' and old[3]==origin,'Repeated event changed or is unresolved')
                    return dict(receipt=json.loads(old[2]),duplicate=True,sink_invoked=False,**CAPABILITIES)
                before=deepcopy(self.sink.snapshot());self._current()
                if local:
                    # The source already executed once. Register its observed
                    # result only, and NEVER subtract costs or replay a command.
                    need(delta_api.journal.digest(before)==body['delta']['after_sha256'],'Local completed result is not the current projection')
                    # Recover a candidate before projection using only the exact
                    # declared semantic field changes, then require reapply to
                    # validate the entire shape, whitelist and both hashes.
                    prior=deepcopy(before)
                    for change in body['delta']['changes']:
                        need(type(change) is dict and set(change)=={'fieldtable','id','field','before','after'},'Malformed result change')
                        need(change['fieldtable'] in ('persons','cities','districts'),'Unknown semantic table')
                        rows=[r for r in prior[change['fieldtable']] if r['id']==change['id']]
                        need(len(rows)==1 and rows[0].get(change['field'])==change['after'],'Local result fields differ')
                        rows[0][change['field']]=change['before']
                    after=delta_api.reapply(prior,body['delta']);need(after==before,'Local result reconstruction differs')
                else:after=delta_api.reapply(before,body['delta'])
                self._reserve(body,origin)  # Durable before any receiving-side write.
                if not local:
                    self.sink.apply_atomic(deepcopy(before),deepcopy(after))
                    self._current();need(self.sink.snapshot()==after,'Sink result differs from the exact candidate projection')
                else:
                    self._current();need(self.sink.snapshot()==before,'Local result changed while registering')
                receipt=dict(schema=SCHEMA,event_id=body['event_id'],sequence=body['sequence'],
                    player=body['player'],local_player=self.local_player,scope_sha256=digest(self.scope),body_sha256=digest(body),
                    after_sha256=delta_api.journal.digest(after),origin=origin,**CAPABILITIES)
                self._persist_result(body,receipt)
                return dict(receipt=receipt,duplicate=False,sink_invoked=not local,**CAPABILITIES)
            except BaseException as exc:self._hold(exc);raise

    def receive(self,value):return self._process(value,False)
    def record_local_completed(self,value):return self._process(value,True)
    def status(self):
        with self.lock:
            row=self.db.execute('SELECT sequence,held FROM metadata WHERE id=1').fetchone()
            return dict(local_player=self.local_player,sequence=row[0],held=bool(row[1] or self.failed),events=self.db.execute('SELECT COUNT(*) FROM events').fetchone()[0],
                pending=self.db.execute("SELECT COUNT(*) FROM events WHERE state='INTENT'").fetchone()[0],**CAPABILITIES)
    def close(self):
        with self.lock:
            if not self.closed:self.db.close();self.closed=True
