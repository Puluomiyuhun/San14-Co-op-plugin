"""Read-only bounded native binding snapshot. Never authorizes Session::Arm."""
import hashlib,json,secrets,struct,sys
from datetime import datetime,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P.parents[1]/'outputs/san14-link')]
from battle_observer import BattleObserver
from checkpoint_manual_reload_observe_start import precheck
from checkpoint_push_start import process_birth

def main():
    before=precheck()
    if before['result']!='PASS':raise RuntimeError(before)
    reader=BattleObserver()
    try:
        memory=reader.memory;base=memory.base;reads=[]
        assert reader.pid==before['pid'] and process_birth(reader)==before['process_birth']
        def grab(label,address,size):
            assert type(address)is int and address>=0x10000 and 0<size<=65536
            data=memory.read(address,size);assert len(data)==size
            reads.append(dict(label=label,address=address,data_hex=data.hex()))
            return data
        def q(data,offset=0):return struct.unpack_from('<Q',data,offset)[0]
        root=q(grab('root_pointer',base+0x1FCA1E0,8))
        grab('root_vtable',root,8)
        world=q(grab('world_pointer',root+0x85130,8));grab('world',world,0x44)
        manager=grab('manager',base+0x19E7310,0x50)
        stack_count,stack_capacity=q(manager,0x10),q(manager,0x18)
        queue_count,queue_capacity=q(manager,0x30),q(manager,0x38)
        assert stack_count==5 and stack_count<=stack_capacity<=4096
        assert queue_count==0 and 0<=queue_capacity<=4096
        stack=grab('stack',q(manager,0x20),stack_capacity*8)
        if queue_capacity:
            grab('queue',q(manager,0x40),queue_capacity*16)
        else:
            assert q(manager,0x40)==0
            reads.append(dict(label='queue',address=0,data_hex=''))
        states=[q(stack,i*8) for i in range(5)]
        assert states==[address for _,address in reader.state_objects()]
        names=['state_root','state_motor','state_game','state_strategy','state_user']
        raw=[grab(name,address,size) for name,address,size in zip(names,states,[0x90,0x90,0x488,0x90,0x668])]
        grab('toolbar',q(raw[4],0x478),0x8c)
        grab('panel',q(raw[2],0x480),0x1f8)
        cache=q(grab('cache_pointer',base+0x2025318,8));grab('cache',cache,0x3f4)
        normal=grab('normal_input',base+0x1FCA0A0,0x78)
        grab('keyboard',q(normal),0x258)
        grab('global_rng',base+0x18EB8B0,4)
        grab('prefetch_original_bytes',base+0x3F9DAF,33)
        for name,rva in [('user',0x12CC4A8+0x28),('menu',0x12DB4C0+0x28),('game',0x12CC9B8+0x28),
                         ('load',0x12DBD90),('callable',0x138E8D0)]:
            grab('slot_'+name,base+rva,8)
        # Read the already-initialized context only. No Steam API is called.
        # Supported ContextInit's cached path returns token+16 after comparing
        # token+8 against its process-global generation counter.
        token=grab('storage_context_token',base+0x18D08B8,24)
        assert q(token)==base+0x2FCB90
        context_init=q(grab('storage_context_init_pointer',base+0x123CB28,8))
        code=grab('storage_context_init_code',context_init,0x70)
        assert code[:16]==bytes.fromhex('40 53 48 83 ec 20 48 8b 51 08 48 8b d9 48 8b 05')
        assert code[20:25]==bytes.fromhex('48 3b d0 74 42')
        assert code[0x5b:0x65]==bytes.fromhex('48 8d 41 10 48 83 c4 20 5b c3')
        counter_address=context_init+20+struct.unpack_from('<i',code,16)[0]
        assert q(grab('storage_context_generation',counter_address,8))==q(token,8)
        storage=q(token,16);vtable=q(grab('storage_object',storage,8))
        methods=grab('storage_vtable',vtable,0x80)
        grab('storage_version',base+0x12AA6B8,len(b'STEAMREMOTESTORAGE_INTERFACE_VERSION014\0'))
        storage_binding=dict(holder=base+0x18D08B8+16,storage=storage,vtable=vtable,
            exists=q(methods,0x68),size=q(methods,0x78),read=q(methods,8))
        assert memory.read(base+0x18D08B8,24)==token
        assert q(memory.read(base+0x1FCA1E0,8))==root
        assert q(memory.read(root+0x85130,8))==world
        assert [address for _,address in reader.state_objects()]==states
        assert memory.read(base+0x19E7310+0x10,0x38)==manager[0x10:0x48]
        assert q(memory.read(base+0x2025318,8))==cache
        snapshot=dict(schema='san14.session-config-snapshot.v1',game_build_sha256=reader.sha256,
            attachment=dict(id=secrets.token_hex(32),pid=reader.pid,birth=before['process_birth'],base=base,epoch=1),
            capture=dict(source='root-read-only',sequence=1,captured_utc=datetime.now(timezone.utc).isoformat()),
            reads=reads,storage_binding=storage_binding,atomic_snapshot=False,
            callback_boundary_observed=False,game_writes=0,authorize_arm=False)
    finally:reader.close()
    path=P/('checkpoint_session_binding_snapshot_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    raw=json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n'
    with path.open('x',encoding='utf-8') as f:f.write(raw)
    print(json.dumps(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        reads=len(reads),attachment=snapshot['attachment'],game_writes=0,authorize_arm=False)))

if __name__=='__main__':main()
