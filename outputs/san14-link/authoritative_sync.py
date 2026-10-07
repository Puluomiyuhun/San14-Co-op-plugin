"""Host-authoritative period/checkpoint protocol, NOT a native game adapter.

The caller is the authenticated room service / trusted adapter, not a raw
client JSON endpoint. Every player argument must come from authentication.
World hashes and application reports are adapter observations, never user
claims. Native completeness is not certified by this module. Room gameplay
remains disabled. State survives reconnection only while this object lives.
"""
from copy import deepcopy
import base64
import hashlib
import json
import re
import secrets
import threading

POLICY='host-authoritative-period-checkpoint.v1'
CHUNK=32768
MAX_PART=64*1024*1024
PARTS={'world.s14','adapter.json'}

class SyncError(ValueError):pass

def require(ok,message):
    if not ok:raise SyncError(message)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def sha(data):return hashlib.sha256(data).hexdigest()
def digest(value):return sha(canonical(value))
def hexid(value,n=64):return type(value) is str and re.fullmatch('[0-9a-f]{%d}'%n,value) is not None
def integer(value,minimum=0):return type(value) is int and minimum<=value<2**53

def scope_from_room(room):
    """Export locked bindings. Does not change WAITING_NATIVE_ADAPTER."""
    with room.lock:
        require(room.bindings is not None,'Select both forces first')
        require(set(room.players)=={'A','B'} and all(p['connection'] is not None for p in room.players.values()),'Peer offline')
        return {'schema':'san14.authoritative-sync-scope.v1','room_id':room.room_id,
                'binding_epoch':room.binding_epoch,'profile':deepcopy(room.manifest['profile']),
                'bindings':deepcopy(room.bindings),'authority':'A','policy':POLICY}

def validate_scope(scope):
    require(type(scope) is dict and set(scope)=={'schema','room_id','binding_epoch','profile','bindings','authority','policy'},'Bad scope')
    require(scope['schema']=='san14.authoritative-sync-scope.v1' and scope['authority']=='A' and scope['policy']==POLICY,'Wrong authority/policy')
    require(hexid(scope['room_id'],32) and hexid(scope['binding_epoch'],32),'Bad room binding')
    require(type(scope['profile']) is dict and scope['profile'].get('adapter_contract')=='research-no-native-room-adapter.v1','No native adapter certified')
    profile=scope['profile']
    require(set(profile)=={'protocol','game_sha256','adapter_contract','checkpoint_sha256','rules_sha256'} and profile['protocol']=='san14.room.v1','Bad compatibility profile')
    require(all(hexid(profile[k]) for k in ('game_sha256','checkpoint_sha256','rules_sha256')),'Bad compatibility hashes')
    require(type(scope['bindings']) is dict and set(scope['bindings'])=={'A','B'},'Bad players')
    ids=[];districts=[]
    for binding in scope['bindings'].values():
        require(type(binding) is dict and set(binding)=={'force_id','main_district_id'},'Bad binding')
        require(all(type(v) is int and 1<=v<=51 for v in binding.values()),'Bad force/district')
        ids.append(binding['force_id'])
        districts.append(binding['main_district_id'])
    require(len(set(ids))==2 and len(set(districts))==2,'Duplicate force/district')

def validate_node(node):
    require(type(node) is dict and set(node)=={'year','month','day','phase'},'Bad logical node')
    require(integer(node['year'],1) and node['year']<=9999 and type(node['month']) is int and 1<=node['month']<=12 and
            type(node['day']) is int and node['day'] in (1,11,21) and node['phase']=='PLANNING_BOUNDARY','Not a settled period boundary')

def next_node(node):
    validate_node(node);n=deepcopy(node)
    if n['day']<21:n['day']+=10
    else:
        n['day']=1;n['month']+=1
        if n['month']==13:n['month']=1;n['year']+=1
    validate_node(n);return n

def validate_cut(cut):
    require(type(cut) is dict and set(cut)=={'sequence','prefix_sha256'},'Bad command prefix')
    require(integer(cut['sequence']) and hexid(cut['prefix_sha256']),'Bad command prefix values')

def validate_manifest(m):
    fields={'schema','scope_sha256','epoch','period','cut','node','state_contract','world_sha256','parts','chunk_size','native_coverage_verified'}
    require(type(m) is dict and set(m)==fields,'Bad checkpoint manifest')
    require(m['schema']=='san14.authority-checkpoint.v1' and hexid(m['scope_sha256']) and hexid(m['epoch'],32),'Bad checkpoint scope')
    require(integer(m['period'],1) and m['chunk_size']==CHUNK and type(m['chunk_size']) is int,'Bad period/chunk size')
    require(m['native_coverage_verified'] is False,'Native coverage not implemented')
    validate_cut(m['cut'])
    validate_node(m['node'])
    require(type(m['state_contract']) is str and 1<=len(m['state_contract'])<=200 and hexid(m['world_sha256']),'Missing state contract/digest')
    require(type(m['parts']) is dict and set(m['parts'])==PARTS,'Save and adapter state are both required')
    for row in m['parts'].values():
        require(type(row) is dict and set(row)=={'size','sha256'} and integer(row['size'],1) and row['size']<=MAX_PART and hexid(row['sha256']),'Bad part descriptor')

class CheckpointPackage:
    def __init__(self,scope,epoch,period,cut,node,state_contract,world_sha256,parts,*,source_player):
        validate_scope(scope);require(source_player=='A','Only A can publish authoritative results')
        require(type(parts) is dict and set(parts)==PARTS and all(type(v) is bytes and 0<len(v)<=MAX_PART for v in parts.values()),'Bad checkpoint parts')
        self._parts=deepcopy(parts)
        m={'schema':'san14.authority-checkpoint.v1','scope_sha256':digest(scope),'epoch':epoch,'period':period,
           'cut':deepcopy(cut),'node':deepcopy(node),'state_contract':state_contract,'world_sha256':world_sha256,
           'parts':{name:{'size':len(data),'sha256':sha(data)} for name,data in parts.items()},'chunk_size':CHUNK,'native_coverage_verified':False}
        validate_manifest(m);self._manifest=canonical(m);self.checkpoint_id=sha(self._manifest)
    @property
    def manifest(self):return json.loads(self._manifest)
    def chunks(self):
        for name,data in sorted(self._parts.items()):
            for offset in range(0,len(data),CHUNK):
                yield {'checkpoint_id':self.checkpoint_id,'part':name,'index':offset//CHUNK,
                       'data':base64.b64encode(data[offset:offset+CHUNK]).decode('ascii')}

class CheckpointReceiver:
    """In-memory resumable staging. Verified bytes are NOT a loaded world."""
    def __init__(self,manifest,expected_id,scope,epoch,period,cut):
        validate_manifest(manifest);validate_scope(scope);validate_cut(cut)
        require(hexid(expected_id) and digest(manifest)==expected_id,'Unpinned/tampered manifest')
        require(manifest['scope_sha256']==digest(scope) and manifest['epoch']==epoch and manifest['period']==period and manifest['cut']==cut,'Stale/foreign checkpoint')
        self.manifest=deepcopy(manifest);self.checkpoint_id=expected_id;self._chunks={};self.lock=threading.RLock()
    def accept(self,packet):
        with self.lock:
            require(digest(self.manifest)==self.checkpoint_id,'Staged manifest was modified')
            require(type(packet) is dict and set(packet)=={'checkpoint_id','part','index','data'},'Bad chunk')
            require(packet['checkpoint_id']==self.checkpoint_id,'Wrong checkpoint')
            name=packet['part'];i=packet['index']
            require(type(name) is str and name in PARTS and integer(i),'Bad chunk coordinates')
            size=self.manifest['parts'][name]['size'];require(i*CHUNK<size,'Chunk index outside part')
            text=packet['data'];require(type(text) is str and 0<len(text)<=((CHUNK+2)//3)*4,'Oversized chunk')
            try:data=base64.b64decode(text,validate=True)
            except (ValueError,UnicodeError) as e:raise SyncError('Bad base64 chunk') from e
            require(len(data)==min(CHUNK,size-i*CHUNK),'Wrong chunk length')
            key=(name,i)
            if key in self._chunks:
                require(self._chunks[key]==data,'Conflicting duplicate chunk');return {'duplicate':True}
            self._chunks[key]=data;return {'duplicate':False}
    def verified_parts(self):
        with self.lock:
            require(digest(self.manifest)==self.checkpoint_id,'Staged manifest was modified')
            parts={}
            for name,row in self.manifest['parts'].items():
                keys=[(name,i) for i in range((row['size']+CHUNK-1)//CHUNK)]
                require(all(k in self._chunks for k in keys),'Incomplete checkpoint; do not load')
                raw=b''.join(self._chunks[k] for k in keys)
                require(len(raw)==row['size'] and sha(raw)==row['sha256'],'Checkpoint content hash mismatch')
                parts[name]=raw
            return parts

class PeriodCoordinator:
    """Protocol barrier model fed by trusted adapters; no game start endpoint.

    A B-side speculative result is intentionally never compared to A's final
    result before replacement. Applied commands must match BEFORE simulation;
    a verified loaded checkpoint must match AFTER replacement.
    """
    def __init__(self,scope,state_contract,initial_sha256,attachments,initial_node):
        validate_scope(scope);require(hexid(initial_sha256),'Bad initial state')
        require(type(state_contract) is str and 1<=len(state_contract)<=200,'Missing state contract')
        require(type(attachments) is dict and set(attachments)=={'A','B'} and all(hexid(a,32) for a in attachments.values()),'Bad adapter attachments')
        require(attachments['A']!=attachments['B'],'Attachments must be distinct')
        validate_node(initial_node)
        self.scope=deepcopy(scope);self.state_contract=state_contract;self.attachments=deepcopy(attachments)
        self.node=deepcopy(initial_node);self.period=1;self.epoch=secrets.token_hex(16);self.phase='PLANNING'
        self.connected={'A','B'};self.ready=set();self.inflight={'A':set(),'B':set()};self.event=None;self.seen_events=set()
        self.reports={p:{'sequence':0,'prefix_sha256':digest(scope),'world_sha256':initial_sha256} for p in ('A','B')}
        self.seal=None;self.manifest=None;self.checkpoint_id=None;self.bytes_received=False;self.load_intent=None
        self.applied_receipts={};self.trace=[];self.lock=threading.RLock()
    def _context(self,player,epoch):
        require(type(player) is str and player in ('A','B'),'Unknown authenticated player')
        require(epoch==self.epoch,'Old period epoch')
        require(self.connected=={'A','B'},'Peer disconnected')
    def set_pending(self,player,epoch,request_ids):
        with self.lock:
            self._context(player,epoch);require(self.phase=='PLANNING','Planning closed')
            require(type(request_ids) is set and len(request_ids)<=4096 and all(hexid(x,32) for x in request_ids),'Bad pending set')
            require(player not in self.ready or not request_ids,'Ready player cannot create new requests')
            self.inflight[player]=set(request_ids)
    def applied_prefix(self,player,epoch,sequence,prefix_sha256,world_sha256,attachment):
        with self.lock:
            self._context(player,epoch);require(self.phase=='PLANNING','Input prefix already sealed')
            require(attachment==self.attachments[player],'Native load instance changed')
            require(integer(sequence) and hexid(prefix_sha256) and hexid(world_sha256),'Bad applied-prefix observation')
            old=self.reports[player];new={'sequence':sequence,'prefix_sha256':prefix_sha256,'world_sha256':world_sha256}
            require(sequence>=old['sequence'],'Stale applied prefix')
            require(sequence!=old['sequence'] or new==old,'Same prefix changed state; recover')
            self.reports[player]=new
    def set_ready(self,player,epoch,value):
        with self.lock:
            self._context(player,epoch);require(self.phase=='PLANNING' and type(value) is bool,'Cannot change ready now')
            require(not value or not self.inflight[player],'Own requests still pending')
            if value:self.ready.add(player)
            else:self.ready.discard(player)
    def seal_inputs(self):
        with self.lock:
            require(self.phase=='PLANNING' and self.connected=={'A','B'} and self.ready=={'A','B'},'Both players must be ready')
            require(not any(self.inflight.values()),'Commands in flight')
            require(self.reports['A']==self.reports['B'],'Applied command prefix/world differs')
            self.seal={'id':secrets.token_hex(16),'epoch':self.epoch,'period':self.period,**self.reports['A']}
            self.phase='SEALED';return deepcopy(self.seal)
    def begin_simulation(self,permit):
        with self.lock:
            require(self.connected=={'A','B'} and self.phase=='SEALED' and permit==self.seal,'Stale/used simulation permit')
            self.phase='RUNNING'
    def host_event(self,source_player,event_id,owner_player,options):
        with self.lock:
            require(source_player=='A' and self.connected=={'A','B'} and self.phase=='RUNNING','Only running authority creates events')
            require(hexid(event_id,32) and type(owner_player) is str and owner_player in ('A','B'),'Bad event identity')
            require((self.epoch,event_id) not in self.seen_events,'Repeated authoritative event')
            require(type(options) is tuple and 1<=len(options)<=32 and all(type(x) is str and 0<len(x)<=100 for x in options) and len(set(options))==len(options),'Bad event choices')
            self.seen_events.add((self.epoch,event_id));self.event={'id':event_id,'owner':owner_player,'options':options,'answer':None};self.phase='WAITING_EVENT'
    def answer_event(self,player,epoch,event_id,choice):
        with self.lock:
            self._context(player,epoch);require(self.phase=='WAITING_EVENT' and self.event['id']==event_id and self.event['owner']==player,'Wrong event owner/id')
            require(choice in self.event['options'],'Invalid event choice')
            require(self.event['answer'] is None or self.event['answer']==choice,'Event already answered differently')
            self.event['answer']=choice
    def event_applied(self,source_player,event_id):
        with self.lock:
            require(source_player=='A' and self.connected=={'A','B'} and self.phase=='WAITING_EVENT' and self.event['id']==event_id and self.event['answer'] is not None,'Authority event result not ready')
            self.trace.append({'kind':'event_applied','event_id':event_id});self.event=None;self.phase='RUNNING'
    def offer_checkpoint(self,source_player,manifest):
        with self.lock:
            require(source_player=='A','B simulation is non-authoritative')
            validate_manifest(manifest)
            require(self.phase=='RUNNING' and self.connected=={'A','B'} and self.event is None,'Still simulating event or held')
            require(manifest['scope_sha256']==digest(self.scope) and manifest['epoch']==self.epoch and manifest['period']==self.period,'Checkpoint scope mismatch')
            require(manifest['cut']=={k:self.seal[k] for k in ('sequence','prefix_sha256')} and manifest['state_contract']==self.state_contract,'Wrong checkpoint input prefix/coverage contract')
            require(manifest['node']==next_node(self.node),'Checkpoint skipped/wrong period')
            self.manifest=deepcopy(manifest);self.checkpoint_id=digest(manifest);self.phase='RECONCILING'
            self.bytes_received=False;self.load_intent=None;return self.checkpoint_id
    def received(self,player,epoch,receiver):
        with self.lock:
            self._context(player,epoch);require(player=='B' and self.phase=='RECONCILING','Not a guest transfer boundary')
            require(type(receiver) is CheckpointReceiver and receiver.checkpoint_id==self.checkpoint_id,'Wrong transfer')
            receiver.verified_parts();self.bytes_received=True
    def begin_guest_load(self,player,epoch):
        with self.lock:
            self._context(player,epoch);require(player=='B' and self.phase=='RECONCILING' and self.bytes_received,'Bytes not verified')
            require(self.load_intent is None,'Load already attempted; uncertain results must not auto-retry')
            self.load_intent=secrets.token_hex(16);return self.load_intent
    def loaded(self,player,epoch,checkpoint_id,intent,world_sha256,viewer_force,new_attachment,host_observation):
        with self.lock:
            receipt={'player':player,'epoch':epoch,'checkpoint_id':checkpoint_id,'intent':intent,'world_sha256':world_sha256,
                     'viewer_force':viewer_force,'attachment':new_attachment,'host_observation':deepcopy(host_observation)}
            if checkpoint_id in self.applied_receipts:
                require(self.applied_receipts[checkpoint_id]==receipt,'Conflicting checkpoint receipt');return {'duplicate':True,'native_gameplay_enabled':False}
            self._context(player,epoch)
            require(player=='B' and self.phase=='RECONCILING' and checkpoint_id==self.checkpoint_id,'Stale load completion')
            require(self.load_intent is not None and intent==self.load_intent,'Missing/mismatched load intent')
            require(world_sha256==self.manifest['world_sha256'],'Loaded world still differs; remain locked')
            require(type(viewer_force) is int and viewer_force==self.scope['bindings']['B']['force_id'],'B identity not restored')
            require(hexid(new_attachment,32) and new_attachment not in self.attachments.values(),'Reload attachment not new')
            require(host_observation=={'attachment':self.attachments['A'],'world_sha256':world_sha256,'node':self.manifest['node']},'A advanced or changed during synchronization')
            self.attachments['B']=new_attachment;self.node=deepcopy(self.manifest['node'])
            self.applied_receipts[checkpoint_id]=receipt;self.period+=1;self.epoch=secrets.token_hex(16)
            self.reports={p:{**deepcopy(self.manifest['cut']),'world_sha256':world_sha256} for p in ('A','B')}
            self.phase='PLANNING';self.ready.clear();self.inflight={'A':set(),'B':set()}
            self.trace.append({'kind':'authoritative_replacement_confirmed','checkpoint_id':checkpoint_id})
            return {'duplicate':False,'period':self.period,'epoch':self.epoch,'native_gameplay_enabled':False}
    def connection(self,player,connected):
        with self.lock:
            require(type(player) is str and player in ('A','B') and type(connected) is bool,'Bad connection notification')
            if connected:self.connected.add(player)
            else:
                self.connected.discard(player);self.ready.clear()
                if self.phase in ('SEALED','RUNNING','WAITING_EVENT'):self.phase='HELD'
            # Reconnection never automatically resumes a native step/load.
    def status(self):
        with self.lock:
            return {'phase':self.phase,'period':self.period,'epoch':self.epoch,'policy':POLICY,
                    'ready':sorted(self.ready),'connected':sorted(self.connected),'checkpoint_id':self.checkpoint_id,
                    'checkpoint_bytes_verified':self.bytes_received,'guest_load_attempted':self.load_intent is not None,
                    'native_gameplay_enabled':False,'native_full_world_coverage_verified':False,
                    'host_restart_recovery_implemented':False}
