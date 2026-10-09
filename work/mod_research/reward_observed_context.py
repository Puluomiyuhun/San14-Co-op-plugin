"""Build-locked GameReader reward projection; finite reads, never native permission.

Reuses the production person predicate, pooled lists, funding and context
samplers. It binds one local attachment/date and retires on any drift. No game
is opened, discovered, written, or called by this module.
"""
from copy import deepcopy
from pathlib import Path
import struct
import sys
import threading

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'outputs/san14-link'))
import authority_reward as reward
import execution_journal as journal
from game_reader import GameReader,DATA_POINTER_RVA
from checkpoint_complete_live_capture import process_birth

CONTRACT='san14.reward-observed-projection.v1:date;two-forces;districts;funding-cities;persons;not-full-world'
PERSON_FIELDS=('id','district_id','force_id','location_id','location_descriptor_raw','rank_raw',
               'loyalty','flags','native_valid','task','army')
CITY_FIELDS=('id','foothold_id','district_id','force_id','gold','food','garrison','trade_rate_raw','trade_flags_raw')
DISTRICT_FIELDS=('id','force_id','kind_raw','leader_id','action_points','valid')


def need(value,message):
    if not value:raise ValueError(message)


def projection(contexts):
    need(type(contexts) is dict and len(contexts)==2,'Exactly two local force contexts required')
    first=next(iter(contexts.values()));people={};districts={};cities={};forces=[]
    def put(table,row,keys):
        value={k:deepcopy(row[k]) for k in keys};old=table.setdefault(value['id'],value)
        need(old==value,'Projection object disagrees between force captures')
    ids=set(contexts)
    for force,c in sorted(contexts.items()):
        need(c['command_force_id']==force and c['date']==first['date'] and
             c['persons']==first['persons'] and c['districts']==first['districts'] and
             c['context_sha256']==reward.context_hash(c),'Context changed during projection')
        forces.append(dict(id=force,ruler=c['ruler_id'],main_district=c['main_district_id']))
        for d in c['districts']:
            if d['force_id'] in ids:put(districts,d,DISTRICT_FIELDS)
        for p in c['persons']:
            if p['force_id'] in ids:put(people,p,PERSON_FIELDS)
        for f in c['funding'].values():
            need(f['supported'],'Reward projection supports only proven city funding')
            put(cities,f['city'],CITY_FIELDS)
    return dict(schema=CONTRACT,date=deepcopy(first['date']),forces=forces,
                districts=sorted(districts.values(),key=lambda r:r['id']),
                cities=sorted(cities.values(),key=lambda r:r['id']),
                persons=sorted(people.values(),key=lambda r:r['id']))


def validate_effect(before,after,command,precheck):
    """Exact projected costs/flags; observe loyalty, do not invent its formula."""
    expected=deepcopy(before);cost=precheck['expected_costs']
    city=next(r for r in expected['cities'] if r['id']==cost['funding_city_id'])
    district=next(r for r in expected['districts'] if r['id']==cost['charged_district_id'])
    need(city['gold']==cost['gold_before'] and district['action_points']==cost['actions_before'],
         'Projection differs from validated funding')
    city['gold']-=cost['gold'];district['action_points']-=cost['action_points']
    old={r['id']:r for r in expected['persons']};actual={r['id']:r for r in after['persons']};changes=[]
    for identity in command['officer_ids']:
        a,b=old[identity],actual[identity]
        need(type(b['loyalty']) is int and a['loyalty']<b['loyalty']<=100,
             'Selected officer loyalty did not increase within native range')
        a['flags']|=2;a['loyalty']=b['loyalty']
        changes.append(dict(id=identity,loyalty_after=b['loyalty'],flags_after=b['flags']))
    need(after==expected,'Native reward changed unexpected projected fields or costs')
    return dict(costs=deepcopy(cost),officers=changes,projection_sha256=journal.digest(after),
                loyalty_formula_verified=False,ui_refresh_verified=False,full_world_verified=False)


class ContextSampler:
    """Trusted local owner supplies the epoch/attachment accessor, never a packet.

    GameReader methods and existing capture_context execute unchanged. The local
    accessor cannot substitute for native exclusion; coverage remains false.
    """
    def __init__(self,reader,*,pid,birth,epoch,attachment_id,current_binding,node,viewer,players,read_birth=None):
        need(type(reader) is GameReader and reader.pid==pid and reader.sha256==reward.SUPPORTED_SHA256,
             'Actual retained GameReader/build required')
        need(type(pid) is int and 0<pid<2**32 and type(birth) is int and 0<birth<2**64,'Process incarnation required')
        need(journal.hex_id(epoch,32) and journal.hex_id(attachment_id,32) and callable(current_binding),
             'Local epoch/attachment binding required')
        need(type(players) is dict and len(players)==2 and viewer in players,'Two bound forces and local viewer required')
        need(all(type(f) is int and 1<=f<=51 and type(v) is dict and set(v)=={'ruler','district'} and
                 type(v['ruler']) is int and 1<=v['ruler']<6000 and type(v['district']) is int and 1<=v['district']<=51
                 for f,v in players.items()),'Bound force identities required')
        need(type(node) is dict and set(node)=={'year','month','day'} and
             all(type(v) is int for v in node.values()),'Exact planning date required')
        self.reader,self.pid,self.birth=reader,pid,birth;self.epoch,self.attachment_id=epoch,attachment_id
        self.current_binding=current_binding;self.node=deepcopy(node);self.viewer=viewer;self.players=deepcopy(players)
        self.read_birth=read_birth or (lambda:process_birth(reader));self.failed=None;self.records=[]
        self.lock=threading.RLock();self.local_identity=self._identity()

    def retire(self,reason):
        with self.lock:
            if self.failed is None:self.failed=str(reason)

    def _identity(self):
        need(self.failed is None,'Reward attachment retired; no replay')
        r=self.reader
        need(r.pid==self.pid and r.sha256==reward.SUPPORTED_SHA256 and self.read_birth()==self.birth,
             'Process incarnation changed')
        need(self.current_binding()==(self.epoch,self.attachment_id),'Epoch or attachment changed')
        root=r.pointer(r.memory.base+DATA_POINTER_RVA);world=r.pointer(root+0x85130)
        snap=r.snapshot();states=r.state_objects()
        need({k:snap['date'][k] for k in self.node}==self.node and
             snap['player']['force_id']==self.viewer and snap['player']['ruler_id']==self.players[self.viewer]['ruler'] and
             snap['state_stack']==reward.PLANNING_STACK,'Date/viewer/planning boundary changed')
        return (r.memory.base,root,world,tuple(states))

    def capture(self):
        with self.lock:
            try:
                need(self._identity()==self.local_identity,'Native world/state attachment changed')
                first={f:reward.capture_context(self.reader,f) for f in sorted(self.players)}
                second={f:reward.capture_context(self.reader,f) for f in sorted(self.players)}
                need(first==second,'Reward complete samples changed')
                for f,c in first.items():
                    need(c['ruler_id']==self.players[f]['ruler'] and c['main_district_id']==self.players[f]['district'] and
                         c['viewer_force_id']==self.viewer and c['strategy_mode']==2,'Native player or command mode changed')
                value=projection(first)
                need(self._identity()==self.local_identity,'Attachment changed during capture')
                self.records.append(dict(sequence=len(self.records)+1,sha256=journal.digest(value),
                    input_exclusion_proven=False,atomic_snapshot=False))
                return first,value
            except BaseException as exc:self.retire(type(exc).__name__+': '+str(exc));raise


class CheckedPort:
    """Existing Replica port with actual before/after projection validation.

    native is a trusted local owner adapter, NOT a remote result producer. Its
    identity() must return the pinned local tuple and execute(command) must use
    that same native Owner lane. This module supplies no injection/export bridge.
    """
    def __init__(self,sampler,native):
        need(type(sampler) is ContextSampler,'Typed local reward sampler required')
        self.sampler,self.native=sampler,native;self.attachment_id=sampler.attachment_id
        self.binding=(sampler.pid,sampler.birth,sampler.epoch,sampler.attachment_id)
        need(native.identity()==self.binding,'Native owner belongs to another local attachment')
        self.calls=0;self.receipts=[]

    def observe(self):return journal.digest(self.sampler.capture()[1])
    def context(self,force):
        need(force in self.sampler.players,'Force is not a bound player')
        return self.sampler.capture()[0][force]
    def retire(self,reason):self.sampler.retire(reason)

    def execute(self,command):
        with self.sampler.lock:
            try:
                need(self.native.identity()==self.binding,'Native owner identity changed')
                contexts,before=self.sampler.capture();force=command['force_id']
                need(force in self.sampler.players,'Command force unbound')
                preview=reward.validate_reward(command,contexts[force],force)
                # The enclosing ExecutionJournal reserves its INTENT first.
                self.calls+=1;native=self.native.execute(deepcopy(command))
                need(type(native) is dict and all(native.get(k) is True for k in
                     ('native_returned','args_released','owned_slot_cleared')) and
                     native.get('uncertain') is False and type(native.get('error')) is int and native['error']==0,
                     'Native completion/cleanup unavailable; no retry')
                need(self.native.identity()==self.binding,'Native attachment changed during command')
                _,after=self.sampler.capture();effects=validate_effect(before,after,command,preview)
                result=dict(native_returned=True,args_released=True,owned_slot_cleared=True,effects=effects,
                    source='LOCAL_REWARD_CONTEXT_AND_RESULT_OBSERVATION',input_exclusion_proven=False,
                    native_gameplay_enabled=False,ui_refresh_verified=False)
                self.receipts.append(result);return result
            except BaseException as exc:self.retire(type(exc).__name__+': '+str(exc));raise
