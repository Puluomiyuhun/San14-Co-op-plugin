"""Version-bound pass-through preparation. No game orders or code publication.

Default is read-only preflight. --prepare claims this process once, loads the
approved DLL and prepares pinned trampolines. --inspect reads its descriptor
and counters; it never reinitializes, unloads or frees retained control data.
"""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys

P = Path(__file__).resolve().parent
sys.path[:0] = [str(P), str(P/'python_deps'), str(P.parents[1]/'outputs/san14-link')]
GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
DLL = P/'human_rules_stage_live_builds/20261007-222216-250737/live_stage.dll'
DLL_SHA = 'ca4c3b7bc7483c752e06e5fc6e5c6b72edb20f2ecd70c8d7341cb70fc70d88b3'
MAGIC = 0x31544753524c5548
AI_HEADER_SHA = '0452bb683152c13ad7e553f550dc113c7c2c8c46676c18e62c3bcf77eb7e77e8'
ARCHIVE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
EXPORTS = ('HumanRulesStagePrepare','HumanRulesStageDescriptor','HumanRulesStageReadReport',
           'HumanRulesStageDescribeLive')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())


def profiles():
    header = P/'human_ai_runtime_profile.h'
    require(sha(header) == AI_HEADER_SHA, 'AI profile changed')
    text = header.read_text()
    result = []
    for name, rva, prefix in [('Force',0xc6660,16),('District',0xc65f0,15),
                              ('Army',0xc6580,15),('Group',0xc66a0,15)]:
        match = re.search(r'Bytes'+name+r'Entry\[\]=\{([0-9,]+)\}',text)
        require(match is not None, 'Missing native entry profile')
        result.append((rva, prefix, bytes(map(int,match[1].split(',')))))
    result += [(0x28de71,5,bytes([232,58,50,248,255])),
               (0x28daa5,5,bytes([232,6,54,248,255]))]
    return result


def read_descriptor(reader, address):
    # The target publishes Prepared last. Never treat a nonce as readiness.
    before = reader.memory.read(address+1200,4)
    raw = reader.memory.read(address,1208)
    after = reader.memory.read(address+1200,4)
    require(before == after == raw[1200:1204] == struct.pack('<I',2), 'Stage is not terminal Prepared')
    require(raw == reader.memory.read(address,1208), 'Descriptor changed while reading')
    magic, version, size, pid, fixture, birth, base, module, allocation = struct.unpack_from('<Q4I4Q',raw)
    require((magic,version,size,fixture)==(MAGIC,1,1208,0),'Not the production descriptor')
    require(struct.unpack_from('<4I',raw,1192)==(6,0,2,0),'Unsupported stage flags')
    sites = []
    for n,(rva,prefix,expected) in enumerate(profiles()):
        off=88+n*184
        source,destination,original,patch_size,profile_size,protection,reserved=struct.unpack_from('<3Q4I',raw,off)
        require((source,patch_size,profile_size,reserved)==(base+rva,prefix,len(expected),0),'Descriptor site profile differs')
        require(raw[off+40:off+40+len(expected)] == expected,'Descriptor original bytes differ')
        sites.append(dict(address=source,destination=destination,original_target=original,
                          patch_size=patch_size,profile_size=profile_size,protection=protection,
                          expected=expected.hex(),replacement=raw[off+168:off+168+prefix].hex()))
    return dict(address=address,pid=pid,birth=birth,base=base,module=module,allocation=allocation,
                nonce=raw[56:88].hex(),sites=sites,raw_sha256=hashlib.sha256(raw).hexdigest(),
                preparation_state=2,fixture=False,policy_enabled=False)


def report(api, address):
    from checkpoint_live_prefetch_start import invoke
    code,raw=invoke(api,address,output_size=128)
    require(code==0,'Stage report failed')
    state,error,*values=struct.unpack('<2I15Q',raw)
    return dict(state=state,error=error,entered=values[:6],exited=values[6:12],
                active=values[12],abnormal=values[13],unexpected_income_caller=values[14])


def same_known_data(before, after):
    # Tile capture carries its wall-clock observation time, not game state.
    # Ignore exactly this documented metadata field, leaving all other fields
    # (including every serialized tile value) in the equality check.
    import copy
    left,right=copy.deepcopy(before),copy.deepcopy(after)
    for value in (left,right):
        value['tiles'].pop('created',None)
    return left==right


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    actions=parser.add_mutually_exclusive_group()
    actions.add_argument('--prepare',action='store_true')
    actions.add_argument('--inspect',action='store_true')
    args=parser.parse_args()
    from battle_observer import BattleObserver
    from checkpoint_push_start import process_birth
    from run_autonomous_pilot import ProcessAPI, pefile
    from checkpoint_live_prefetch_start import invoke, RemoteCallError
    reader=BattleObserver();api=None
    try:
        birth=process_birth(reader);base=reader.memory.base
        require(reader.sha256==GAME_SHA,'Unsupported game version')
        claim_path=P/f'human_rules_stage_live_{reader.pid}_{birth}_once.json'
        api=ProcessAPI(reader)
        if args.inspect:
            claim=json.loads(claim_path.read_text(encoding='utf8'))
            folder=Path(claim['run']);prepared=json.loads((folder/'result.json').read_text(encoding='utf8'))
            require(prepared.get('prepare_exit')==0 and 'descriptor' in prepared,
                    'No completed preparation to inspect; this action cannot retry it')
            module=prepared['descriptor']['module']
            require((module,Path(claim['dll'])) in api.modules(),'Prepared module no longer bound')
            require(sha(Path(claim['dll']))==DLL_SHA,'Prepared module file changed')
            desc=read_descriptor(reader,prepared['descriptor']['address'])
            require(desc==prepared['descriptor'],'Prepared descriptor changed')
            counters=report(api,prepared['exports']['HumanRulesStageReadReport'])
            result=dict(descriptor=desc,counters=counters,snapshot=reader.snapshot(),source_bytes=[],
                        original_prepare_result=prepared['result'],inspection_is_publication_authority=False)
            for site in desc['sites']:
                result['source_bytes'].append(reader.memory.read(site['address'],site['profile_size']).hex())
            path=folder/('inspection-'+datetime.now().strftime('%H%M%S-%f')+'.json');save(path,result)
            print(json.dumps(dict(result='INSPECTED',path=str(path),counters=counters),ensure_ascii=True))
            return
        snapshot=reader.snapshot()
        require(snapshot['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],
                'Not idle formal planning')
        sources=[]
        for rva,prefix,expected in profiles():
            require(reader.memory.read(base+rva,len(expected))==expected,'Six-entry original code differs')
            sources.append(dict(rva=rva,prefix=prefix,original=expected.hex()))
        require(sha(DLL)==DLL_SHA,'Unapproved production DLL')
        require(not any(path.name=='live_stage.dll' or path.name.startswith('san14-human-rules-') for _,path in api.modules()),
                'A stage already resides in this process; inspect rather than prepare again')
        preflight=dict(pid=reader.pid,birth=birth,base=base,exe_sha256=reader.sha256,snapshot=snapshot,sources=sources)
        if not args.prepare:
            print(json.dumps(dict(result='PASS_READ_ONLY_PREFLIGHT',**preflight),ensure_ascii=True));return
        require(not claim_path.exists(),'This process already has a stage claim; never retry initialization')
        folder=P/'human_rules_stage_live_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
        # The broad witness accepts and records the existing User vtable hook;
        # this new module neither owns nor changes those older loading hooks.
        from checkpoint_complete_live_capture import known_snapshot
        from checkpoint_live_capture import comparison
        prior_slot=reader.pointer(base+0x12cc4d0)
        before=known_snapshot(reader,expected_user_hook=prior_slot)
        save(folder/'known-before.json',before)
        save(folder/'preflight.json',preflight)
        copied=folder/f'san14-human-rules-{folder.name}.dll';shutil.copy2(DLL,copied)
        require(sha(copied)==DLL_SHA,'Copied DLL changed')
        pe=pefile.PE(str(copied))
        try:
            export_rvas={s.name.decode('ascii'):s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
            require(all(name in export_rvas for name in EXPORTS),'Missing control exports')
            image_size=pe.OPTIONAL_HEADER.SizeOfImage
        finally:pe.close()
        claim=dict(run=str(folder),pid=reader.pid,birth=birth,base=base,dll=str(copied),dll_sha256=DLL_SHA,
                   automatic_retry_allowed=False,source_publication=False)
        save(claim_path,claim)
        result=dict(result='INCOMPLETE',**claim,game_orders=0,source_patches=0,module_retained=True)
        try:
            # No native game business function is called on these helper threads.
            invoke(api,api.load_library_address(),str(copied).encode('utf-16le')+b'\0\0')
            found=[b for b,path in api.modules() if path==copied]
            require(len(found)==1,'Loaded module path mismatch');module=found[0]
            exports={name:module+export_rvas[name] for name in EXPORTS}
            result['exports']=exports
            from checkpoint_complete_live_capture import module_approval,readable
            result['module_identity']=module_approval(reader,module,copied,DLL_SHA)
            pe=pefile.PE(str(copied),fast_load=True)
            try:
                for name in EXPORTS:
                    if name=='HumanRulesStageDescriptor':continue
                    address=exports[name]
                    require(module<=address<module+image_size-32,'Control export outside module')
                    readable(reader,address,32,allocation=module,execute=True)
                    require(reader.memory.read(address,32)==pe.get_data(address-module,32),'Loaded control code differs')
            finally:pe.close()
            code,raw=invoke(api,exports['HumanRulesStageDescribeLive'],output_size=48)
            require(code==0,'Live description rejected')
            info=struct.unpack('<Q6I2Q',raw)
            require(info==(MAGIC,1,48,24,1208,128,1200,exports['HumanRulesStageDescriptor'],exports['HumanRulesStagePrepare']),
                    'Live control ABI mismatch')
            code,_=invoke(api,exports['HumanRulesStagePrepare'],struct.pack('<QIIQ',MAGIC,1,24,base))
            result['prepare_exit']=code
            require(code==0,'Preparation rejected; module retained without source patches')
            desc=read_descriptor(reader,exports['HumanRulesStageDescriptor'])
            require((desc['pid'],desc['birth'],desc['base'],desc['module'])==(reader.pid,birth,base,module),'Prepared identity differs')
            result['descriptor']=desc
            result['counters']=report(api,exports['HumanRulesStageReadReport'])
            require(result['counters']==dict(state=2,error=0,entered=[0]*6,exited=[0]*6,active=0,abnormal=0,unexpected_income_caller=0),
                    'Preparation unexpectedly executed a hook')
            for row in sources:
                require(reader.memory.read(base+row['rva'],len(bytes.fromhex(row['original']))).hex()==row['original'],
                        'Preparation changed source code')
            after=known_snapshot(reader,expected_user_hook=prior_slot);save(folder/'known-after.json',after)
            diff=comparison(before,after);result['comparison']=diff
            require(same_known_data(before,after),'Known planning data changed during preparation')
            require(process_birth(reader)==birth,'Process identity changed')
            result['result']='PASS_PREPARED_NOT_PUBLISHED'
        except BaseException as exc:
            result['error']=repr(exc)
            if isinstance(exc,RemoteCallError):
                result['control_completed']=exc.completed;result['control_may_have_started']=exc.may_have_started
            raise
        finally:
            save(folder/'result.json',result)
        print(json.dumps(dict(result=result['result'],path=str(folder/'result.json'),
                             descriptor=result['descriptor'],game_orders=0,source_patches=0),ensure_ascii=True))
    finally:
        if api:api.close()
        reader.close()


if __name__=='__main__':main()
