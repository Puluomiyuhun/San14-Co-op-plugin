"""Generate bounded native reload pilot from existing debugger lifecycle; offline only."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
image=(ROOT/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
hooks=(0x3F8177,0x3F818D,0x4BF5C3,0x2EE64C,0x508BC2,0x2FC850,0x3F69F0,0x3F72C0,0x3F9B00)
ranges=[(at,at+next(md.disasm(image[at:at+16],at)).size) for at in hooks]
ranges += [(0x3F8177,0x3F8194),(0x4AA582,0x4AA58F),(0x4A370C,0x4A3726),(0x4CEAE0,0x4CEB12),(0x4DA3B2,0x4DA3BE),(0x836710,0x836721)]
header='// Generated exact-build guards; no injected gameplay code.\n'
for i,(a,z) in enumerate(ranges):header+='static const unsigned char ar_bytes_%d[]={%s};\n'%(i,','.join(map(str,image[a:z])))
header+='struct ARGuard {uint64_t rva;const unsigned char* bytes;size_t size;};\nstatic const ARGuard ar_guards[]={'
header+=','.join('{0x%X,ar_bytes_%d,sizeof ar_bytes_%d}'%(a,i,i) for i,(a,z) in enumerate(ranges))+'};\n'
(ROOT/'auto_reload_profile.h').write_text(header,encoding='utf-8')
(ROOT/'auto_reload_profile.json').write_text(json.dumps({'game_sha256':'42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025','ranges':[{'start':a,'end':z,'sha256':hashlib.sha256(image[a:z]).hexdigest()} for a,z in ranges]},indent=2)+'\n',encoding='utf-8')
s=(ROOT/'observe_startup_identity.cpp').read_text(encoding='utf-8')
s=s.replace('#include "startup_identity_observe.inc"','#include "auto_reload_cleanup.inc"\n#include "auto_reload_payload.inc"')
s=s.replace('if(argc!=expectedArgc)', 'if(argc!=9)')
s=s.replace('DWORD pid=wcstoul', '''executeReload=std::wcscmp(argv[6],L"execute")==0;
    if(!executeReload&&std::wcscmp(argv[6],L"dry"))return 2;
    reservationPath=argv[7];checkpointPath=argv[8];
    DWORD pid=wcstoul''')
s=s.replace('DWORD access=PROCESS_QUERY_INFORMATION|PROCESS_VM_READ;', 'DWORD access=PROCESS_QUERY_INFORMATION|PROCESS_VM_READ; if(executeReload)access|=PROCESS_VM_WRITE|PROCESS_VM_OPERATION;')
s=s.replace('submit_probe_fixture.exe','auto_reload_fixture.exe')
s=s.replace('fixtureMode=(!_wcsicmp(leaf,L"auto_reload_fixture.exe"));','syntheticFixture=(!_wcsicmp(leaf,L"auto_reload_fixture.exe")); fixtureMode=false;')
s=s.replace('if(!fixtureMode && rva!=0x2EE64C)', 'if(rva!=0x3F8177)')
s=s.replace('check(DebugActiveProcess(pid),"DebugActiveProcess");', 'verifyReloadProfile(process,base); pinCheckpoint(path);\n        check(DebugActiveProcess(pid),"DebugActiveProcess");')
s=s.replace('hit=stageSamples>0 || fixtureSamples>0;', 'hit=reloadComplete||dryComplete;')
s=s.replace('std::fclose(log); return result;', 'if(checkpointHandle!=INVALID_HANDLE_VALUE)CloseHandle(checkpointHandle);\n    std::fclose(log); return result;')
s=s.replace('// Observation-only combat gate logger. No game code/data writes or game calls. RNG writers are observed before the native store.', '// Controlled same-player load34 pilot: one guarded pending-slot DWORD write; native lifecycle continues. Dry by default through launcher.')
s=s.replace('Usage: probe pid base rva timeout_seconds log.jsonl [expected.bin recorded.bin]', 'Usage: auto_reload pid base 0x3f8177 timeout_seconds log.jsonl dry|execute once.json checkpoint34.s14')
old_cleanup='''            bool suspended=false;
            try {
                if(!eventPending) { if(SuspendThread(thread.handle)==DWORD(-1)) continue; suspended=true; }
                restore(thread.handle,thread.original);
            } catch(...) { restored=false; }
            if(suspended) ResumeThread(thread.handle);'''
new_cleanup='''            auto outcome=cleanupThread(thread.handle,eventPending,[&]{restore(thread.handle,thread.original);});
            if((!outcome.registersRestored&&!outcome.threadExited)||outcome.resumeFailed)restored=false;
            if(!outcome.registersRestored||outcome.resumeFailed)
                std::fprintf(log,"{\\"event\\":\\"thread_cleanup_status\\",\\"thread\\":%lu,\\"registers_restored\\":%s,\\"thread_exited\\":%s,\\"suspend_failed\\":%s,\\"resume_failed\\":%s}\\n",tid,outcome.registersRestored?"true":"false",outcome.threadExited?"true":"false",outcome.suspendFailed?"true":"false",outcome.resumeFailed?"true":"false");'''
assert old_cleanup in s
s=s.replace(old_cleanup,new_cleanup)
old_read='''    check(ReadProcessMemory(process,reinterpret_cast<void*>(address),output,bytes,&count),"ReadProcessMemory");
    if(count!=bytes) throw std::runtime_error("Partial process read");'''
new_read='''    BOOL ok=ReadProcessMemory(process,reinterpret_cast<void*>(address),output,bytes,&count);
    if(!ok||count!=bytes){
        DWORD error=GetLastError();char message[192];
        sprintf_s(message,"ReadProcessMemory error=%lu address=0x%llx requested=%zu read=%zu",error,address,bytes,count);
        throw std::runtime_error(message);
    }'''
assert old_read in s
s=s.replace(old_read,new_read)
old_error=r'''std::fprintf(log,"{\"event\":\"error\",\"message\":\"%s\"}\n",error.what());'''
new_error=r'''std::fprintf(log,"{\"event\":\"error\",\"message\":\"%s\",\"point_epoch\":%u,\"last_observation_rva\":%llu}\n",error.what(),pointEpoch,lastObservationRva);'''
assert old_error in s
s=s.replace(old_error,new_error)
(ROOT/'observe_auto_reload.cpp').write_text(s,encoding='utf-8')
print(json.dumps({'generated':True,'guards':len(ranges),'game_access':False}))
