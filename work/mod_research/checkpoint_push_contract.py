"""Pure v2 report predicates. No game/file access. All captures remain partial.

complete_ok(report, after_precheck, file_evidence, before_capture, after_capture)
requires checkpoint_live_capture.sample() dictionaries, never bare booleans.
"""
import copy
import hashlib
import math
import re
import struct
from collections import Counter

REPORT=struct.Struct('<27I4x9Q16I5Q8I8Q')
NAMES=('magic version status error active_callbacks accepted installer_thread executor_thread original_calls binder_calls queue_calls '
       'intent_created intent_flushed binder_returned queue_returned slot_restored protection_restored exception_code dry_storage_query '
       'source_strings_consumed request_globals_matched queue_item_verified reserved storage_context_calls file_exists_calls remote_slot_absent storage_reserved '
       'base caller state slot original hook queued_state queue_before queue_after '
       'save_callbacks save_original_calls save_active_callbacks save_phase_mask save_association_ok save_worker_started save_worker_joined save_native_success '
       'save_finalizer_called save_finalizer_returned save_globals_cleared save_observation_done save_slot_restored save_protection_restored save_observation_error save_reserved '
       'save_slot save_original save_hook queued_at finalized_at '
       'return_seen return_matched return_thread stop_requested before_rng after_rng cache_mode_before cache_mode_after '
       'pinned_user pinned_game pinned_world returned_at first_user_call_id last_user_call_id user_raw_rax save_raw_rax').split()
assert len(NAMES)==73 and REPORT.size==384
FIELD_BITS=[32]*27+[64]*9+[32]*16+[64]*5+[32]*8+[64]*8
MAGIC=0x1414E201
TARGET='mppush01.s14'
SIDECARS=frozenset(('configS_SC.s14','prdataN.s14'))
STACK=['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
RECORD_TYPES={'person':(571,392),'city':(52,192),'district':(52,24),'force':(52,48),'army':(56,496)}

def read_std_string(read,address):
    raw=read(address,32);size,capacity=struct.unpack_from('<QQ',raw,16)
    if size>15 or size>capacity or (capacity<16 and capacity!=15) or capacity>32768:raise ValueError('Unsupported string length/capacity')
    pointer=struct.unpack_from('<Q',raw)[0] if capacity>=16 else address
    if not 0x10000<=pointer<=0x00007FFFFFFFFFFF-size:raise ValueError('Invalid string data pointer')
    data=read(pointer,size+1)
    if len(data)!=size+1 or data[-1]!=0 or b'\0' in data[:-1]:raise ValueError('Invalid string terminator/content')
    if read(address,32)!=raw:raise ValueError('String changed during sampling')
    return {'size':size,'capacity':capacity,'data_pointer':hex(pointer),'text':data[:-1].decode('ascii')}

def pending_vector_valid(count,capacity,pointer):
    return all(type(x) is int for x in (count,capacity,pointer)) and count==0 and 0<=capacity<=4096 and ((capacity==0)==(pointer==0)) and (pointer==0 or 0x10000<=pointer<=0x00007FFFFFFFFFFF-capacity*16)

def decode(raw):
    if len(raw)!=REPORT.size:raise ValueError('Wrong report size; v2 requires384')
    value=dict(zip(NAMES,REPORT.unpack(raw)))
    if value['magic']!=MAGIC or value['version']!=2:raise ValueError('Wrong report ABI; need0x1414E201/version2')
    return value

def report_valid(r):
    return (isinstance(r,dict) and all(type(r.get(k)) is int and 0<=r[k]<1<<bits for k,bits in zip(NAMES,FIELD_BITS))
            and r['magic']==MAGIC and r['version']==2 and all(r[k]==0 for k in ('reserved','storage_reserved','save_reserved')))

def hook_clean(r):
    return report_valid(r) and r['active_callbacks']==0 and r['slot_restored']==r['protection_restored']==1

def dry_ok(r):
    zero=('error','exception_code','stop_requested','binder_calls','queue_calls','intent_created','intent_flushed',
          'binder_returned','queue_returned','source_strings_consumed','request_globals_matched','queue_item_verified',
          'queued_state','queue_before','queue_after','queued_at','finalized_at','returned_at',
          'return_seen','return_matched','return_thread','last_user_call_id','after_rng','cache_mode_after',
          'save_callbacks','save_original_calls','save_active_callbacks','save_phase_mask','save_association_ok',
          'save_worker_started','save_worker_joined','save_native_success','save_finalizer_called','save_finalizer_returned',
          'save_globals_cleared','save_observation_done','save_slot_restored','save_protection_restored','save_observation_error',
          'save_slot','save_original','save_hook','save_raw_rax')
    return (hook_clean(r) and r['status']==3 and r['accepted']==1 and all(r[k]==0 for k in zero)
            and all(r[k]==1 for k in ('dry_storage_query','storage_context_calls','file_exists_calls','remote_slot_absent'))
            and r['original_calls']>=1 and r['first_user_call_id']>0 and r['installer_thread']>0 and r['executor_thread']>0
            and r['pinned_user']==r['state']>=0x10000 and r['pinned_game']>=0x10000 and r['pinned_world']>=0x10000
            and r['cache_mode_before'] in (0,1))

def native_lifecycle_ok(r):
    ones=('accepted','intent_created','intent_flushed','binder_calls','queue_calls','binder_returned','queue_returned',
          'source_strings_consumed','request_globals_matched','queue_item_verified','storage_context_calls','file_exists_calls','remote_slot_absent',
          'save_association_ok','save_worker_started','save_worker_joined','save_native_success','save_finalizer_called','save_finalizer_returned',
          'save_globals_cleared','save_observation_done','save_slot_restored','save_protection_restored','return_seen','return_matched')
    return (hook_clean(r) and r['status']==8 and all(r[k]==1 for k in ones)
            and all(r[k]==0 for k in ('error','exception_code','dry_storage_query','save_active_callbacks','save_observation_error','stop_requested','queue_before'))
            and r['queue_after']==1 and r['save_phase_mask']==31 and r['queued_state']>=0x10000
            and r['queued_state']!=r['pinned_user'] and r['pinned_user']==r['state']>=0x10000
            and r['pinned_game']>=0x10000 and r['pinned_world']>=0x10000
            and r['save_callbacks']==r['save_original_calls']>=5 and r['original_calls']>=2
            and r['returned_at']>=r['finalized_at']>=r['queued_at']>0
            and r['last_user_call_id']>r['first_user_call_id']>0
            and r['installer_thread']>0 and r['executor_thread']>0 and r['return_thread']>0
            and r['before_rng']==r['after_rng']<1<<32
            and r['cache_mode_before']==r['cache_mode_after'] and r['cache_mode_before'] in (0,1))

def _need(ok,reason):
    if not ok:raise ValueError(reason)

def _sha(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None

def _raw(value,size):
    _need(isinstance(value,str) and len(value)==size*2,'wrong_raw_hex_length')
    raw=bytes.fromhex(value);_need(len(raw)==size,'wrong_raw_length');return raw

def _capture_valid(sample):
    _need(isinstance(sample,dict),'capture_not_object')
    _need(sample['original_update_slot_restored'] is True and sample['game_writes']==0 and sample['full_world_coverage'] is False,'capture_scope_or_hook')
    ctx=sample['context'];snap=ctx['snapshot']
    _need(snap['state_stack']==STACK and ctx['state_sample']['phase_raw']==2,'capture_not_planning')
    _need(snap['date']=={'year':203,'month':8,'day':11,'period':'中旬'},'capture_wrong_date')
    _need(snap['player']['force_id']==12 and snap['player']['ruler_id']==666 and ctx['world_mode']==1,'capture_wrong_identity')
    obj=sample['objects'];records=obj['records'];counts=Counter()
    _need(isinstance(records,dict) and len(records)==783,'capture_record_count')
    for key,value in records.items():
        kind,number=key.split(':');_need(kind in RECORD_TYPES and number.isdigit(),'capture_record_key')
        _raw(value,RECORD_TYPES[kind][1]);counts[kind]+=1
    _need(counts=={k:v[0] for k,v in RECORD_TYPES.items()},'capture_record_categories')
    _need(type(obj['global_rng']) is int and 0<=obj['global_rng']<1<<32 and ctx['global_rng']==obj['global_rng'],'capture_rng')
    _raw(obj['world_rng_fields_hex'],16)
    _need(isinstance(obj['focused'],dict) and isinstance(obj['eligibility'],dict) and isinstance(obj['pools'],dict),'capture_additional_object_fields_missing')
    _need(all(isinstance(k,str) and type(v) is int and v>=0 for k,v in obj['pools'].items()),'capture_allocator_pool_counts')
    tiles=sample['tiles']
    _need(tiles['schema']=='san14.checkpoint-hex-payload-sample.v1' and tiles['slot_count']==48400 and tiles['all_slot_payload_bytes']==242000
          and tiles['table_root_offset']==0xDFE0,'capture_hex_coverage')
    _need(tiles['field_ranges']==[{'offset':20,'length':1},{'offset':22,'length':2},{'offset':24,'length':1},{'offset':25,'length':1}],'capture_hex_fields')
    raw=_raw(tiles['ordered_payload_hex'],242000)
    # Match the existing scanner's tagged digest, not SHA(raw) alone.
    tagged=b'san14.hex.stream-fields.v1\0'+struct.pack('<II',0xDFE0,48400)+raw
    _need(hashlib.sha256(tagged).hexdigest()==tiles['ordered_payload_sha256'],'capture_hex_digest')
    _need(tiles['identity_or_pointer_fields_normalized'] is False and tiles['full_world_verified'] is False,'capture_hex_scope')
    files=sample['save_files'];_need(isinstance(files,dict) and len(files)>0,'capture_file_inventory_missing')
    for name,value in files.items():
        _need(isinstance(name,str) and name.endswith('.s14') and re.fullmatch('[A-Za-z0-9_.-]+',name) is not None,'inventory_filename')
        _need(type(value['size']) is int and value['size']>=0 and _sha(value['sha256']),'inventory_entry')

def compare_known_coverage(before,after):
    """Exact business bytes; allocator/UI pool counts are separately disclosed."""
    result={'valid_inputs':False,'matched':False,'full_world_verified':False}
    try:
        _capture_valid(before);_capture_valid(after)
        a,b=before['objects']['records'],after['objects']['records']
        tile_a={k:v for k,v in before['tiles'].items() if k!='created'}
        tile_b={k:v for k,v in after['tiles'].items() if k!='created'}
        business_a={k:v for k,v in before['objects'].items() if k!='pools'}
        business_b={k:v for k,v in after['objects'].items() if k!='pools'}
        result.update(valid_inputs=True,record_count_before=len(a),record_count_after=len(b),missing_records=sorted(a.keys()-b.keys()),
                      extra_records=sorted(b.keys()-a.keys()),changed_records=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k]),
                      all_objects_equal=before['objects']==after['objects'],context_equal=before['context']==after['context'],
                      all_objects_except_allocator_pools_equal=business_a==business_b,
                      allocator_pools={'before':copy.deepcopy(before['objects']['pools']),'after':copy.deepcopy(after['objects']['pools']),
                                       'changed':before['objects']['pools']!=after['objects']['pools'],
                                       'affects_business_match':False,'scope':'Known allocator/UI counts; no object bytes excluded.'},
                      all_tiles_except_created_equal=tile_a==tile_b,
                      all_48400_hex_serialized_fields_equal=before['tiles']['ordered_payload_hex']==after['tiles']['ordered_payload_hex'],
                      hex_payload_bytes=242000,global_rng_equal=before['objects']['global_rng']==after['objects']['global_rng'],
                      world_rng_fields_equal=before['objects']['world_rng_fields_hex']==after['objects']['world_rng_fields_hex'])
        result['matched']=all(result[k] for k in ('all_objects_except_allocator_pools_equal','context_equal','all_tiles_except_created_equal'))
    except (KeyError,ValueError,TypeError,AttributeError) as error:result['reason']=str(error)
    return result

def _inventory_diff(before,after):
    keys=sorted(before.keys()|after.keys())
    return {'added':sorted(after.keys()-before.keys()),'removed':sorted(before.keys()-after.keys()),
            'changed':sorted(k for k in before.keys()&after.keys() if before[k]!=after[k]),
            'entries':{k:{'before':before.get(k),'after':after.get(k)} for k in keys if before.get(k)!=after.get(k)}}

def completion_evidence(report,after_precheck,file_evidence,before_capture,after_capture):
    """Detailed result; two sidecars disclosed independently, never hidden."""
    result={'complete':False,'native_lifecycle_ok':native_lifecycle_ok(report),'coverage':compare_known_coverage(before_capture,after_capture),
            'full_world_verified':False,'native_full_file_identity_verified':False,'B_load_authorized':False,'sidecars':None,'ordinary_saves':None}
    try:
        _need(result['coverage']['valid_inputs'],'invalid_capture_inputs')
        a,b=before_capture['save_files'],after_capture['save_files']
        ordinary_a={k:v for k,v in a.items() if k not in SIDECARS and k!=TARGET}
        ordinary_b={k:v for k,v in b.items() if k not in SIDECARS and k!=TARGET}
        _need(bool(ordinary_a),'ordinary_inventory_empty')
        result['ordinary_saves']=_inventory_diff(ordinary_a,ordinary_b)
        result['ordinary_saves_unchanged']=ordinary_a==ordinary_b
        result['sidecars']=_inventory_diff({k:v for k,v in a.items() if k in SIDECARS},{k:v for k,v in b.items() if k in SIDECARS})
        result['sidecar_change_affects_file_invariance']=False
        _need(isinstance(after_precheck,dict) and after_precheck.get('result')=='PASS','after_precheck_not_passed')
        _need(result['native_lifecycle_ok'],'native_lifecycle_not_complete')
        f=file_evidence;_need(isinstance(f,dict) and f.get('stable') is True,'file_not_stable')
        _need(type(f.get('samples')) is int and f['samples']>=3,'file_sample_count')
        span=f.get('span_seconds');_need(type(span) in (int,float) and math.isfinite(span) and span>=1,'file_stability_span')
        _need(type(f.get('size')) is int and 294<=f['size']<=0x7d000 and _sha(f.get('sha256')),'file_size_or_hash')
        _need(TARGET not in a and b.get(TARGET)=={'size':f['size'],'sha256':f['sha256']},'new_file_inventory_mismatch')
        _need(report['before_rng']==before_capture['objects']['global_rng'] and report['after_rng']==after_capture['objects']['global_rng'],'report_capture_rng_mismatch')
        _need(result['coverage']['matched'],'known_coverage_changed')
        _need(result['ordinary_saves_unchanged'],'ordinary_or_forensic_saves_changed')
        result['complete']=True
        result['scope']='Bounded native push export returned to same User; all known captures unchanged. Not full-world proof or native B file identity.'
    except (KeyError,ValueError,TypeError,AttributeError) as error:result['reason']=str(error)
    return result

def complete_ok(report,after_precheck,file_evidence,before_capture,after_capture):
    return completion_evidence(report,after_precheck,file_evidence,before_capture,after_capture)['complete']

def selftest():
    """Pure bytes/dictionaries only; count feeds root's isolated fixture report."""
    r=dict.fromkeys(NAMES,0)
    r.update(magic=MAGIC,version=2,status=8,slot_restored=1,protection_restored=1,queued_state=0x20000,queued_at=10,finalized_at=20,returned_at=20,
             save_phase_mask=31,save_callbacks=5,save_original_calls=5,state=0x10000,pinned_user=0x10000,pinned_game=0x30000,pinned_world=0x40000,
             original_calls=2,first_user_call_id=1,last_user_call_id=7,installer_thread=1,executor_thread=2,return_thread=3,
             before_rng=0x1234,after_rng=0x1234,cache_mode_before=1,cache_mode_after=1,queue_after=1)
    for key in ('accepted','intent_created','intent_flushed','binder_calls','queue_calls','binder_returned','queue_returned','source_strings_consumed',
                'request_globals_matched','queue_item_verified','storage_context_calls','file_exists_calls','remote_slot_absent','save_association_ok',
                'save_worker_started','save_worker_joined','save_native_success','save_finalizer_called','save_finalizer_returned','save_globals_cleared',
                'save_observation_done','save_slot_restored','save_protection_restored','return_seen','return_matched'):r[key]=1
    assert native_lifecycle_ok(r);count=1
    packed=REPORT.pack(*(r[k] for k in NAMES));assert decode(packed)==r;count+=1
    for raw in (packed[:288],packed[:-1],packed+b'\0',struct.pack('<II',MAGIC,1)+packed[8:],struct.pack('<I',0x1414E101)+packed[4:]):
        try:decode(raw)
        except ValueError:pass
        else:raise AssertionError('Wrong ABI accepted')
        count+=1
    for key,value in [('status',4),('return_seen',0),('return_matched',0),('stop_requested',1),('pinned_user',0x50000),('after_rng',9),
                      ('cache_mode_after',0),('cache_mode_before',2),('save_phase_mask',30),('save_worker_started',0),('save_worker_joined',0),
                      ('save_native_success',0),('save_finalizer_called',0),('save_finalizer_returned',0),('save_globals_cleared',0),('save_observation_done',0),
                      ('save_association_ok',0),('queue_item_verified',0),('queue_before',1),('queue_after',2),('intent_flushed',0),('binder_calls',2),
                      ('queue_calls',2),('storage_context_calls',2),('file_exists_calls',2),('remote_slot_absent',0),('active_callbacks',1),
                      ('save_active_callbacks',1),('slot_restored',0),('protection_restored',0),('save_slot_restored',0),('save_protection_restored',0),
                      ('exception_code',5),('save_observation_error',60),('returned_at',19),('finalized_at',9),('queued_at',0),
                      ('last_user_call_id',1),('return_thread',0),('save_original_calls',4),('version',1),('original_calls',1<<32)]:
        bad=copy.deepcopy(r);bad[key]=value;assert not native_lifecycle_ok(bad),key;count+=1
    dry=dict.fromkeys(NAMES,0);dry.update(magic=MAGIC,version=2,status=3,accepted=1,slot_restored=1,protection_restored=1,
                                        dry_storage_query=1,storage_context_calls=1,file_exists_calls=1,remote_slot_absent=1,
                                        state=0x10000,pinned_user=0x10000,pinned_game=0x20000,pinned_world=0x30000,
                                        first_user_call_id=1,original_calls=1,installer_thread=1,executor_thread=2)
    assert dry_ok(dry);count+=1
    for key in ('intent_created','intent_flushed','binder_calls','queue_calls','save_callbacks','save_hook','return_seen','stop_requested'):
        bad=copy.deepcopy(dry);bad[key]=1;assert not dry_ok(bad),key;count+=1
    context={'snapshot':{'state_stack':STACK,'date':{'year':203,'month':8,'day':11,'period':'中旬'},'player':{'force_id':12,'ruler_id':666}},
             'state_sample':{'phase_raw':2},'world_mode':1,'global_rng':0x1234}
    raw_tiles=bytes(242000)
    before={'created':'earlier','context':context,'objects':{'records':{f'{kind}:{i}':bytes(size).hex() for kind,(n,size) in RECORD_TYPES.items() for i in range(n)},
             'global_rng':0x1234,'world_rng_fields_hex':bytes(16).hex(),'focused':{},'eligibility':{},'pools':{}},
             'tiles':{'schema':'san14.checkpoint-hex-payload-sample.v1','created':'earlier','slot_count':48400,'all_slot_payload_bytes':242000,'table_root_offset':0xDFE0,
                      'field_ranges':[{'offset':20,'length':1},{'offset':22,'length':2},{'offset':24,'length':1},{'offset':25,'length':1}],
                      'ordered_payload_hex':raw_tiles.hex(),'ordered_payload_sha256':hashlib.sha256(b'san14.hex.stream-fields.v1\0'+struct.pack('<II',0xDFE0,48400)+raw_tiles).hexdigest(),
                      'identity_or_pointer_fields_normalized':False,'full_world_verified':False},
             'save_files':{'svdexSC34.s14':{'size':123,'sha256':'b'*64},'mpckpt01.s14':{'size':456,'sha256':'c'*64},
                           'configS_SC.s14':{'size':12,'sha256':'d'*64}},'original_update_slot_restored':True,'game_writes':0,'full_world_coverage':False}
    after=copy.deepcopy(before);after['created']='later';after['tiles']['created']='later';after['save_files'][TARGET]={'size':300,'sha256':'a'*64}
    after['save_files']['configS_SC.s14']['sha256']='e'*64
    f={'stable':True,'samples':3,'span_seconds':1,'size':300,'sha256':'a'*64};precheck={'result':'PASS'}
    out=completion_evidence(r,precheck,f,before,after)
    assert out['complete'] and out['sidecars']['changed']==['configS_SC.s14'] and not out['full_world_verified'];count+=1
    pool_after=copy.deepcopy(after);pool_after['objects']['pools']={'0x19e1c20':5815,'0x201d3d0':15809}
    pool_out=completion_evidence(r,precheck,f,before,pool_after)
    assert pool_out['complete'] and pool_out['coverage']['allocator_pools']['changed'] and not pool_out['coverage']['all_objects_equal'];count+=1
    assert pool_out['coverage']['allocator_pools']['before']==before['objects']['pools'] and pool_out['coverage']['allocator_pools']['after']==pool_after['objects']['pools'];count+=1
    pool_after['objects']['records']['army:0']='11'+pool_after['objects']['records']['army:0'][2:]
    assert not complete_ok(r,precheck,f,before,pool_after);count+=1
    assert not complete_ok(r,precheck,f,True,True);count+=1
    for path,value in [(('objects','records','army:0'),('00'*312)+'11'+('00'*183)),(('objects','global_rng'),0x1235),
                       (('objects','world_rng_fields_hex'),'01'+('00'*15)),(('tiles','slot_count'),48399),
                       (('tiles','ordered_payload_hex'),'01'+raw_tiles.hex()[2:]),(('context','state_sample','phase_raw'),3),
                       (('save_files','mpckpt01.s14','sha256'),'f'*64),(('save_files',TARGET,'size'),301),
                       (('objects','records'),{}),(('objects','focused'),{'changed':1})]:
        bad=copy.deepcopy(after);where=bad
        for key in path[:-1]:where=where[key]
        where[path[-1]]=value
        assert not complete_ok(r,precheck,f,before,bad),path;count+=1
    for key,value in [('stable',False),('samples',2),('span_seconds',float('nan')),('span_seconds',.9),('sha256','z'*64),('size',0)]:
        bad=copy.deepcopy(f);bad[key]=value;assert not complete_ok(r,precheck,bad,before,after),key;count+=1
    address=0x10000;heap=0x11000
    for capacity,text in [(15,''),(15,TARGET),(31,''),(31,TARGET),(63,'')]:
        memory=bytearray(0x2000);data=text.encode();memory[:16]=struct.pack('<Q',heap)+bytes(8) if capacity>=16 else data.ljust(16,b'\0')
        struct.pack_into('<QQ',memory,16,len(data),capacity)
        if capacity>=16:memory[heap-address:heap-address+len(data)+1]=data+b'\0'
        assert read_std_string(lambda p,n:bytes(memory[p-address:p-address+n]),address)['text']==text;count+=1
    for capacity,size,pointer,terminator in [(7,0,heap,0),(31,0,0,0),(31,0,heap,65),(32769,0,heap,0),(15,16,heap,0)]:
        memory=bytearray(0x2000);struct.pack_into('<Q',memory,0,pointer);struct.pack_into('<QQ',memory,16,size,capacity);memory[heap-address]=terminator
        try:read_std_string(lambda p,n:bytes(memory[p-address:p-address+n]),address)
        except ValueError:pass
        else:raise AssertionError((capacity,size,pointer,terminator))
        count+=1
    for n,cap,pointer,valid in [(0,0,0,True),(0,64,0x11000,True),(1,64,0x11000,False),(0,0,0x11000,False),(0,64,0,False),(0,4097,0x11000,False)]:
        assert pending_vector_valid(n,cap,pointer)==valid;count+=1
    return count

if __name__=='__main__':
    print({'result':'PASS','pure_selftest_cases':selftest(),'report_size':REPORT.size,'fields':len(NAMES),'game_access':False})
