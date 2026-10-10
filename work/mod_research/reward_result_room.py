"""Authenticated Room transport for bounded projected reward results only.

No command execution, native sink, input permission, Room Ready or UI refresh.
Shared submission HMAC is tied to the actual authenticated connection/seat;
local-journal acknowledgements additionally use separately provisioned seat keys.
Their truth still depends on trusted local adapters, not on a game's native proof.
"""
from copy import deepcopy
from contextlib import contextmanager
import hashlib,hmac,json,sqlite3,threading
from pathlib import Path
import reward_result_channel as channel
from room_session import Room

SCHEMA='san14.reward-result-room.v1'
SUBMIT_DOMAIN=b'san14.reward-result-room.submit.v1\0'
ACK_DOMAIN=b'san14.reward-result-room.ack.v1\0'
need=channel.need


def envelope(scope,action,**fields):
    return dict(action=action,room_id=scope['room_id'],binding_epoch=scope['binding_epoch'],
                epoch=scope['timeline_epoch'],**fields)


def submission(scope,player,event_id,delta,*,key):
    channel._key(key)
    body=channel._body(scope,player,event_id,1,delta);body.pop('sequence');body['schema']=SCHEMA
    channel.delta_api._envelope(delta)
    return dict(body=body,proof=hmac.new(key,SUBMIT_DOMAIN+channel.canonical(body),hashlib.sha256).hexdigest())


def ack_proof(key,receipt):
    channel._key(key)
    return hmac.new(key,ACK_DOMAIN+channel.canonical(receipt),hashlib.sha256).hexdigest()


class ResultAuthority:
    """One fresh A-hosted ordering lifetime; an existing journal is never reset.

    current_scope is a trusted local observation of timeline/date/attachments.
    No callback receives peer pointers, runs a reward or changes game memory.
    Lock order is authority -> Room; mount/handlers must not invert it.
    """
    def __init__(self,path,room,scope,*,key,report_keys,current_scope):
        need(isinstance(room,Room) and callable(current_scope),'Actual Room and local scope observer required')
        channel._key(key)
        need(type(report_keys) is dict and set(report_keys)=={'A','B'},'Two local adapter report keys required')
        for k in report_keys.values():channel._key(k)
        need(report_keys['A']!=report_keys['B'] and key not in report_keys.values(),'Submission and seat report keys must differ')
        self.room=room;self.scope=channel.validate_scope(scope);self.key=key;self.report_keys=dict(report_keys)
        self.current_scope=current_scope;self.lock=threading.RLock();self.failed=None;self.closed=False
        with room.lock:
            need(set(room.players)=={'A','B'} and all(r['connection'] for r in room.players.values()),'Both authenticated seats must be connected')
            self.connections={p:r['connection'] for p,r in room.players.items()}
            self._scope()
        self.path=Path(path)
        with self.path.open('xb'):pass
        self.db=sqlite3.connect(self.path,isolation_level=None,check_same_thread=False,timeout=5)
        try:
            self.db.execute('PRAGMA synchronous=FULL');self.db.execute('PRAGMA journal_mode=DELETE')
            with self.transaction():
                self.db.execute('CREATE TABLE metadata (id INTEGER PRIMARY KEY,scope TEXT NOT NULL,connections TEXT NOT NULL,sequence INTEGER NOT NULL,held TEXT)')
                self.db.execute('INSERT INTO metadata VALUES(1,?,?,0,NULL)',(channel.canonical(self.scope).decode(),channel.canonical(self.connections).decode()))
                self.db.execute('CREATE TABLE events (sequence INTEGER PRIMARY KEY,event_id TEXT UNIQUE NOT NULL,player TEXT NOT NULL,proposal_sha TEXT NOT NULL,proposal TEXT NOT NULL,packet TEXT NOT NULL,state TEXT NOT NULL)')
                self.db.execute('CREATE TABLE receipts (sequence INTEGER NOT NULL,player TEXT NOT NULL,sha TEXT NOT NULL,receipt TEXT NOT NULL,PRIMARY KEY(sequence,player))')
        except BaseException:self.db.close();raise

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:yield;self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise

    def _scope(self):
        need(self.room.room_id==self.scope['room_id'] and self.room.binding_epoch==self.scope['binding_epoch'] and
             self.room.bindings==self.scope['actors'],'Authenticated Room binding differs')
        need(channel.validate_scope(self.current_scope())==self.scope,'Local timeline/date/attachment changed')

    def _active(self,player,connection):
        need(not self.closed and self.failed is None,'Result authority terminal')
        need(self.db.execute('SELECT held FROM metadata WHERE id=1').fetchone()==(None,),'Persisted result authority held')
        need(player in ('A','B') and connection==self.connections[player] and
             self.room.players[player]['connection']==connection,'Connection is not the bound authenticated seat')
        need({p:r['connection'] for p,r in self.room.players.items()}==self.connections,'Authenticated peer disconnected or changed')
        self._scope()

    def hold(self,reason):
        self.failed=self.failed or reason
        try:
            with self.transaction():self.db.execute('UPDATE metadata SET held=COALESCE(held,?) WHERE id=1',(self.failed,))
        except BaseException as exc:self.hold_record_error=type(exc).__name__

    def _fields(self,r,extra):
        need(type(r) is dict and set(r)=={'action','room_id','binding_epoch','epoch'}|set(extra),'Exact result action fields required')
        need(all(r[k]==self.scope[v] for k,v in (('room_id','room_id'),('binding_epoch','binding_epoch'),('epoch','timeline_epoch'))),'Stale result scope')

    def _submit(self,player,r):
        self._fields(r,{'proposal'});value=r['proposal']
        need(type(value) is dict and set(value)=={'body','proof'},'Signed candidate required')
        b=value['body'];need(type(b) is dict and b.get('player')==player,'Candidate impersonates another authenticated seat')
        expected=submission(self.scope,player,b.get('event_id'),b.get('delta'),key=self.key)
        need(type(value['proof']) is str and hmac.compare_digest(value['proof'],expected['proof']) and
             channel.canonical(value['body'])==channel.canonical(expected['body']),'Candidate signature or binding differs')
        fingerprint=channel.digest(value)
        old=self.db.execute('SELECT proposal_sha,packet,state FROM events WHERE event_id=?',(b['event_id'],)).fetchone()
        if old:
            need(old[0]==fingerprint,'Event identity reused with different candidate')
            return dict(packet=json.loads(old[1]),status=old[2],duplicate=True)
        with self.transaction():
            need(self.db.execute("SELECT 1 FROM events WHERE state!='PAIRED'").fetchone() is None,'Previous result lacks both local journal receipts')
            sequence=self.db.execute('SELECT sequence FROM metadata WHERE id=1').fetchone()[0]+1
            p=channel.packet(self.scope,player,b['event_id'],sequence,b['delta'],key=self.key)
            self.db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,'WAITING_RECEIPTS')",(sequence,b['event_id'],player,fingerprint,channel.canonical(value).decode(),channel.canonical(p).decode()))
            self.db.execute('UPDATE metadata SET sequence=? WHERE id=1',(sequence,))
        return dict(packet=p,status='WAITING_RECEIPTS',duplicate=False)

    def _poll(self,r):
        self._fields(r,set())
        row=self.db.execute("SELECT packet FROM events WHERE state!='PAIRED'").fetchone()
        return dict(packet=json.loads(row[0]) if row else None,status='WAITING_RECEIPTS' if row else 'IDLE')

    def _ack(self,player,r):
        self._fields(r,{'receipt','proof'});receipt=r['receipt']
        need(type(r['proof']) is str and hmac.compare_digest(r['proof'],ack_proof(self.report_keys[player],receipt)),'Local adapter receipt signature differs')
        need(type(receipt) is dict and channel.integer(receipt.get('sequence'),1,2**63-1),'Local journal receipt required')
        row=self.db.execute('SELECT packet,state FROM events WHERE sequence=?',(receipt['sequence'],)).fetchone()
        need(row is not None,'Receipt has no authority event');p=json.loads(row[0]);b=p['body']
        expected=dict(schema=channel.SCHEMA,event_id=b['event_id'],sequence=b['sequence'],player=b['player'],
            local_player=player,scope_sha256=channel.digest(self.scope),body_sha256=channel.digest(b),
            after_sha256=b['delta']['after_sha256'],origin='LOCAL_ALREADY_COMPLETED' if player==b['player'] else 'REMOTE_RESULT_APPLICATION',**channel.CAPABILITIES)
        need(channel.canonical(receipt)==channel.canonical(expected),'Receipt does not match exact local journal result/direction')
        hashed=channel.digest(receipt)
        with self.transaction():
            old=self.db.execute('SELECT sha FROM receipts WHERE sequence=? AND player=?',(b['sequence'],player)).fetchone()
            if old:need(old==(hashed,),'Receipt replay changed')
            else:self.db.execute('INSERT INTO receipts VALUES(?,?,?,?)',(b['sequence'],player,hashed,channel.canonical(receipt).decode()))
            paired=self.db.execute('SELECT COUNT(*) FROM receipts WHERE sequence=?',(b['sequence'],)).fetchone()[0]==2
            if paired:self.db.execute("UPDATE events SET state='PAIRED' WHERE sequence=?",(b['sequence'],))
        return dict(sequence=b['sequence'],status='PAIRED' if paired else 'WAITING_RECEIPTS',duplicate=bool(old))

    def handle(self,player,connection,r):
        with self.lock,self.room.lock:
            try:
                self._active(player,connection)
                action=r.get('action') if type(r) is dict else None
                if action=='result_submit':response=self._submit(player,r)
                elif action=='result_poll':response=self._poll(r)
                elif action=='result_ack':response=self._ack(player,r)
                else:raise channel.ResultError('Unsupported result action')
                return dict(ok=True,**response,**channel.CAPABILITIES)
            except Exception as exc:
                self.hold(type(exc).__name__+': '+str(exc))
                return dict(ok=False,error=str(exc),held=True,**channel.CAPABILITIES)

    def disconnect(self,player,connection):
        with self.lock,self.room.lock:
            if player in self.room.players and self.room.players[player]['connection']==connection:
                self.hold('Authenticated peer disconnected; pending results require manual reconciliation')
            self.room.disconnect(player,connection)

    def status(self):
        with self.lock:
            sequence,held=self.db.execute('SELECT sequence,held FROM metadata WHERE id=1').fetchone()
            return dict(sequence=sequence,held=bool(held or self.failed),pending=self.db.execute("SELECT COUNT(*) FROM events WHERE state!='PAIRED'").fetchone()[0],**channel.CAPABILITIES)

    def close(self):
        with self.lock:
            if not self.closed:self.db.close();self.closed=True


class ResultEndpoint:
    """Server.room wrapper: existing Room greeting/selection, then one mount."""
    def __init__(self,room):
        need(isinstance(room,Room),'Actual Room required');self.room=room;self.authority=None;self.lock=threading.RLock()
    def mount(self,authority):
        with self.lock:
            need(type(authority) is ResultAuthority and authority.room is self.room and self.authority is None,'Single exact authority mount required')
            self.authority=authority
    def authenticate(self,*args):return self.room.authenticate(*args)
    def handle(self,player,connection,r):
        with self.lock:a=self.authority
        if type(r) is dict and str(r.get('action','')).startswith('result_'):
            if a is None:return dict(ok=False,error='Result adapter not mounted',**channel.CAPABILITIES)
            return a.handle(player,connection,r)
        return self.room.handle(player,connection,r)
    def disconnect(self,player,connection):
        with self.lock:a=self.authority
        if a is not None:a.disconnect(player,connection)
        else:self.room.disconnect(player,connection)
