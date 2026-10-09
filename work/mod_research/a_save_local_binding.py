"""Capture current A planning/storage bindings, READ ONLY; no args means help.

Explicit --capture --pid is required. No process discovery, writable handle,
debugger, native call, save, or load. Private captures are not runtime permits.
"""
from pathlib import Path
from datetime import datetime
import argparse,ctypes as C,hashlib,json,struct,sys
from ctypes import wintypes as W
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def source_hashes():
    paths={Path(__file__).resolve()}
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if not name:continue
        path=Path(name).resolve()
        if path.suffix=='.py' and path.is_relative_to(P.parents[1]):paths.add(path)
    return {path.relative_to(P.parents[1]).as_posix():sha(path) for path in sorted(paths)}

def modules(handle):
    ps=C.WinDLL('psapi',use_last_error=True)
    ps.EnumProcessModulesEx.argtypes=[W.HANDLE,C.POINTER(C.c_void_p),W.DWORD,C.POINTER(W.DWORD),W.DWORD]
    ps.EnumProcessModulesEx.restype=W.BOOL
    ps.GetModuleFileNameExW.argtypes=[W.HANDLE,W.HMODULE,W.LPWSTR,W.DWORD]
    ps.GetModuleFileNameExW.restype=W.DWORD
    values=(C.c_void_p*2048)();size=W.DWORD()
    if not ps.EnumProcessModulesEx(handle,values,C.sizeof(values),C.byref(size),3):raise C.WinError(C.get_last_error())
    if size.value>C.sizeof(values) or size.value%C.sizeof(C.c_void_p):raise RuntimeError('Incomplete module inventory')
    rows=[]
    for base in values[:size.value//C.sizeof(C.c_void_p)]:
        path=C.create_unicode_buffer(32768)
        count=ps.GetModuleFileNameExW(handle,base,path,len(path))
        if not count or count>=len(path)-1:raise RuntimeError('Incomplete module path')
        rows.append((base,Path(path.value)))
    return rows

def capture(pid):
    if type(pid)is not int or pid<=0:raise ValueError('Explicit positive PID required')
    sys.path[:0]=[str(P),str(PRIVATE/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
    from a_save_observation_status import preflight
    from checkpoint_complete_live_capture import planning_bindings,storage_bindings
    from game_reader import GameReader
    import startup_identity_reader  # Include this deferred dependency in the initial pins.
    sources=source_hashes()
    run=PRIVATE/'a_save_local_binding_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(schema='san14.a-save-local-binding.v1',result='INCOMPLETE',pid=pid,game_data_writes=0,
                native_requests=0,debugger_attached=False,atomic_snapshot=False,production_permit=False)
    try:
        before=preflight(pid)
        if before['result']!='PASS_READ_ONLY':raise RuntimeError(before['reasons'])
        reader=GameReader(pid=pid)
        try:
            planning=planning_bindings(reader);storage=storage_bindings(reader,modules(reader.memory.handle))
            if (planning['pid'],planning['birth'],planning['base'])!=(before['pid'],before['birth'],before['base']):raise RuntimeError('Attachment changed')
            m=reader.memory;b=m.base
            u32=lambda a:struct.unpack('<I',m.read(a,4))[0]
            s32=lambda a:struct.unpack('<i',m.read(a,4))[0]
            u64=lambda a:struct.unpack('<Q',m.read(a,8))[0]
            user=planning['states'][4];game=planning['states'][2];manager=b+0x19e7310
            inputs=dict(queue_count=u64(manager+0x30),queue_capacity=u64(manager+0x38),queue_pointer=u64(manager+0x40),
                        user_phase=u32(user+0x470),menu_command=s32(planning['toolbar']+0x88),
                        game_transition=u32(game+0x474),load_queued=u32(game+0x478),advance=u32(game+0x47c),
                        panel_advance=u32(planning['panel']+0x1b0),user_transition=u32(user+0x660),
                        user_selection=u32(user+0x68),game_selection=u32(game+0x68),
                        cache_selection=s32(planning['cache']+0x3ec),cache_pending=u32(planning['cache']+0x3f0),
                        user_targets=[u64(user+offset) for offset in (0x4a8,0x4b0,0x4b8)])
            again=planning_bindings(reader);storage_after=storage_bindings(reader,modules(reader.memory.handle))
            if again!=planning or storage_after!=storage:raise RuntimeError('Bindings changed during capture')
            result.update(planning=planning,storage=storage,inputs=inputs,
                          native_empty_queue=inputs['queue_count']==inputs['queue_capacity']==inputs['queue_pointer']==0)
        finally:reader.close()
        after=preflight(pid)
        if after!=before:raise RuntimeError('Game context changed after capture')
        result.update(result='PASS_READ_ONLY',preflight=before)
    except Exception as e:result.update(result='BLOCKED',error=repr(e))
    # All captured addresses/code remain private. Public evidence uses only
    # counts, booleans and hashes, never this file as an admission token.
    result['sources']=sources
    result['sources_unchanged']=all(sha(P.parents[1]/name)==digest for name,digest in sources.items())
    if not result['sources_unchanged']:result.update(result='BLOCKED',error='Source changed during capture')
    file=run/'result.json'
    with file.open('x',encoding='utf-8',newline='\n')as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps(dict(result=result['result'],path=str(file),native_empty_queue=result.get('native_empty_queue'),error=result.get('error')),ensure_ascii=False))
    return 0 if result['result']=='PASS_READ_ONLY' else 1

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capture',action='store_true');parser.add_argument('--pid',type=int)
    args=parser.parse_args()
    if not args.capture:parser.print_help();return 0
    if args.pid is None or args.pid<=0:parser.error('--capture requires a positive --pid')
    return capture(args.pid)
if __name__=='__main__':raise SystemExit(main())
