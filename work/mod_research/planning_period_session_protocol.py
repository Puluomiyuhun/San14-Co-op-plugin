"""Explicit protocol/business model inputs for the owned native session test."""
from copy import deepcopy
import json
from pathlib import Path
import secrets
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'outputs/san14-link'))
import authoritative_sync as sync
import planning_period_scope as mapper


def coordinator():
    scope={'schema':'san14.authoritative-sync-scope.v1','room_id':secrets.token_hex(16),
        'binding_epoch':secrets.token_hex(16),'authority':'A','policy':sync.POLICY,
        'profile':{'protocol':'san14.room.v1','game_sha256':'a'*64,
            'adapter_contract':'research-no-native-room-adapter.v1','checkpoint_sha256':'b'*64,'rules_sha256':'c'*64},
        'bindings':{'A':{'force_id':12,'main_district_id':11},'B':{'force_id':2,'main_district_id':2}}}
    return sync.PeriodCoordinator(scope,'owned-scope-model-not-game','d'*64,
        {'A':secrets.token_hex(16),'B':secrets.token_hex(16)},
        {'year':203,'month':8,'day':11,'phase':'PLANNING_BOUNDARY'})


def advance_model(c):
    # Execute the actual frozen protocol transitions. All observations/files here
    # are explicit test model data; this never attests an actual guest load.
    for player in ('A','B'):
        c.applied_prefix(player,c.epoch,1,'e'*64,'f'*64,c.attachments[player])
        c.set_ready(player,c.epoch,True)
    seal=c.seal_inputs();c.begin_simulation(seal)
    package=sync.CheckpointPackage(c.scope,c.epoch,c.period,{'sequence':1,'prefix_sha256':'e'*64},
        sync.next_node(c.node),c.state_contract,'1'*64,
        {'world.s14':b'owned diagnostic model, not a game save','adapter.json':b'{}'},source_player='A')
    identity=c.offer_checkpoint('A',package.manifest)
    receiver=sync.CheckpointReceiver(package.manifest,identity,c.scope,c.epoch,c.period,package.manifest['cut'])
    for chunk in package.chunks():receiver.accept(chunk)
    c.received('B',c.epoch,receiver);intent=c.begin_guest_load('B',c.epoch)
    c.loaded('B',c.epoch,identity,intent,'1'*64,2,secrets.token_hex(16),
             {'attachment':c.attachments['A'],'world_sha256':'1'*64,'node':package.manifest['node']})


def prepare(run):
    c=coordinator();a=mapper.from_coordinator(c,'A');b=mapper.from_coordinator(c,'B')
    assert a['timeline_epoch']==b['timeline_epoch'] and mapper.native_digest(a)!=mapper.native_digest(b)
    advance_model(c);n=mapper.from_coordinator(c,'A')
    assert n['base_sequence']==1 and n['period']==2 and n['timeline_epoch']!=a['timeline_epoch']
    checks=[]
    def test(name,fn):fn();checks.append({'case':name,'result':'PASS','kind':'protocol_business_model','exit':0})
    def rejects(fn):
        try:fn()
        except (ValueError,TypeError,KeyError):return
        raise AssertionError('expected rejection')
    def identity_bytes():
        for k in ('room_id','binding_epoch','timeline_epoch','scope_sha256'):
            x=deepcopy(a);raw=bytearray.fromhex(x[k]);raw[-1]^=1;x[k]=raw.hex()
            assert mapper.native_digest(x)!=mapper.native_digest(a)
    test('scope-full-width-identity',identity_bytes)
    def malformed():
        for k,value in [('period',True),('base_sequence',2**53),('timeline_epoch','0'*32),('viewer_force',True)]:
            x=deepcopy(a);x[k]=value;rejects(lambda:mapper.native_digest(x))
    test('scope-invalid-fields',malformed)
    def blocked():
        x=coordinator();x.phase='RUNNING';rejects(lambda:mapper.from_coordinator(x,'A'))
        x=coordinator();x.ready.add('B');rejects(lambda:mapper.from_coordinator(x,'A'))
        x=coordinator();x.reports['B']['world_sha256']='2'*64;rejects(lambda:mapper.from_coordinator(x,'A'))
    test('scope-unsettled-refusal',blocked)
    test('scope-protocol-next-global-cut',lambda:None)
    scopes=[a,n]
    (run/'protocol-scopes.json').write_text(json.dumps({'scopes':scopes,'native_load_observations':'explicit models only'},indent=2)+'\n')
    def arr(h):return '{'+','.join(str(v) for v in bytes.fromhex(h))+'}'
    lines=['#pragma once','static planning_period_session::Scope SessionScopes[]={']
    for s in scopes:
        d=s['date'];fields=[arr(s[k]) for k in ('room_id','binding_epoch','timeline_epoch','scope_sha256')]
        fields += [str(s['period']),str(s['base_sequence']),'{'+','.join(str(v) for v in (d['year'],d['month'],d['day'],s['viewer_force']))+'}']
        lines.append('{'+','.join(fields)+'},')
    lines+=['};','static std::array<unsigned char,32> SessionDigests[]={'+','.join(arr(mapper.native_digest(s)) for s in scopes)+'};']
    (run/'planning_period_session_scopes.h').write_text('\n'.join(lines)+'\n')
    return checks
