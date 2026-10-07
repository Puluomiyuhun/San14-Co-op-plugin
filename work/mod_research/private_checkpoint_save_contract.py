"""Pure report/trace predicates. No live game imports or effects."""
import copy,struct
REPORT=struct.Struct('<27I4x9Q16I5Q')
NAMES=('magic version status error active_callbacks accepted installer_thread executor_thread original_calls binder_calls queue_calls '
       'intent_created intent_flushed binder_returned queue_returned slot_restored protection_restored exception_code dry_storage_query '
       'source_strings_consumed request_globals_matched queue_item_verified reserved storage_context_calls file_exists_calls remote_slot_absent storage_reserved '
       'base caller state slot original hook queued_state queue_before queue_after '
       'save_callbacks save_original_calls save_active_callbacks save_phase_mask save_association_ok save_worker_started save_worker_joined save_native_success '
       'save_finalizer_called save_finalizer_returned save_globals_cleared save_observation_done save_slot_restored save_protection_restored save_observation_error save_reserved '
       'save_slot save_original save_hook queued_at finalized_at').split()
assert len(NAMES)==57 and REPORT.size==288
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
    return count==0 and 0<=capacity<=4096 and ((capacity==0)==(pointer==0)) and (pointer==0 or 0x10000<=pointer<=0x00007FFFFFFFFFFF-capacity*16)
def decode(raw):
    value=dict(zip(NAMES,REPORT.unpack(raw)))
    assert value['magic']==0x1414E101 and value['version']==1,'Wrong report ABI'
    return value
def hook_clean(r):
    return not r['active_callbacks'] and r['slot_restored']==r['protection_restored']==1
def dry_ok(r):
    return r['status']==3 and r['error']==0 and hook_clean(r) and r['binder_calls']==r['queue_calls']==r['intent_created']==r['save_callbacks']==0 and r['dry_storage_query']==1 and r['file_exists_calls']==r['remote_slot_absent']==1
def native_lifecycle_ok(r):
    ones=('intent_created','intent_flushed','binder_calls','queue_calls','binder_returned','queue_returned','source_strings_consumed','request_globals_matched','queue_item_verified','file_exists_calls','remote_slot_absent',
          'save_association_ok','save_worker_started','save_worker_joined','save_native_success','save_finalizer_called','save_finalizer_returned','save_globals_cleared','save_observation_done','save_slot_restored','save_protection_restored')
    return r['status']==4 and r['error']==0 and hook_clean(r) and all(r[k]==1 for k in ones) and not r['save_active_callbacks'] and not r['save_observation_error'] and r['save_phase_mask']==31 and r['queued_state']!=0 and r['save_callbacks']==r['save_original_calls'] and r['save_callbacks']>=5 and r['finalized_at']>=r['queued_at']>0
def complete_ok(report,after,file_evidence,business_unchanged,existing_unchanged):
    return native_lifecycle_ok(report) and after.get('result')=='PASS' and file_evidence.get('stable') is True and file_evidence.get('samples',0)>=3 and file_evidence.get('span_seconds',0)>=1 and file_evidence.get('size',0)>0 and len(file_evidence.get('sha256',''))==64 and business_unchanged and existing_unchanged
def selftest():
    r=dict.fromkeys(NAMES,0);r.update(magic=0x1414E101,version=1,status=4,slot_restored=1,protection_restored=1,queued_state=123,queued_at=10,finalized_at=20,save_phase_mask=31,save_callbacks=5,save_original_calls=5)
    for key in ('intent_created','intent_flushed','binder_calls','queue_calls','binder_returned','queue_returned','source_strings_consumed','request_globals_matched','queue_item_verified','file_exists_calls','remote_slot_absent','save_association_ok','save_worker_started','save_worker_joined','save_native_success','save_finalizer_called','save_finalizer_returned','save_globals_cleared','save_observation_done','save_slot_restored','save_protection_restored'):r[key]=1
    after={'result':'PASS'};file={'stable':True,'samples':3,'span_seconds':1.1,'size':123,'sha256':'a'*64}
    assert complete_ok(r,after,file,True,True);count=1
    for key,value in [('save_worker_started',0),('save_worker_joined',0),('save_native_success',0),('save_association_ok',0),('save_phase_mask',30),('save_globals_cleared',0),('save_observation_done',0),('save_active_callbacks',1),('save_observation_error',60),('save_slot_restored',0),('queued_state',0),('queue_calls',2),('finalized_at',0)]:
        bad=copy.deepcopy(r);bad[key]=value;assert not complete_ok(bad,after,file,True,True),key;count+=1
    for key,value in [('stable',False),('samples',2),('span_seconds',.9),('size',0),('sha256','')]:
        bad=copy.deepcopy(file);bad[key]=value;assert not complete_ok(r,after,bad,True,True),key;count+=1
    assert not complete_ok(r,{'result':'BLOCKED'},file,True,True);count+=1
    assert not complete_ok(r,after,file,False,True);count+=1
    assert not complete_ok(r,after,file,True,False);count+=1
    address=0x10000;heap=0x11000
    for capacity,text in [(15,''),(15,'mpckpt01.s14'),(31,''),(31,'mpckpt01.s14'),(63,'')]:
        memory=bytearray(0x2000);data=text.encode()
        memory[:16]=struct.pack('<Q',heap)+bytes(8) if capacity>=16 else data.ljust(16,b'\0')
        struct.pack_into('<QQ',memory,16,len(data),capacity)
        if capacity>=16:memory[heap-address:heap-address+len(data)+1]=data+b'\0'
        read=lambda p,n:bytes(memory[p-address:p-address+n])
        assert read_std_string(read,address)['text']==text;count+=1
    for capacity,size,pointer,terminator in [(7,0,heap,0),(31,0,0,0),(31,0,heap,65),(32769,0,heap,0),(15,16,heap,0)]:
        memory=bytearray(0x2000);struct.pack_into('<Q',memory,0,pointer);struct.pack_into('<QQ',memory,16,size,capacity);memory[heap-address]=terminator
        try:read_std_string(lambda p,n:bytes(memory[p-address:p-address+n]),address)
        except ValueError:pass
        else:raise AssertionError((capacity,size,pointer,terminator))
        count+=1
    for n,c,p,valid in [(0,0,0,True),(0,64,0x11000,True),(0,4096,0x11000,True),
                        (1,64,0x11000,False),(0,0,0x11000,False),(0,64,0,False),
                        (0,4097,0x11000,False),(0,64,1,False),(0,64,0x7FFFFFFFFFF0,False)]:
        assert pending_vector_valid(n,c,p)==valid;count+=1
    return count
