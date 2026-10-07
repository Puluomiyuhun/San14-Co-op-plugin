"""Reuse the tested debug lifecycle, with per-thread native call/return pairing."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
old=(ROOT/'observe_camera_rng_watch.cpp').read_text()
prefix=old[:old.index('static void tacticRecord')]
prefix=prefix.replace('// Observation-only camera/tactics trace plus AFTER-write RNG watch. No game code/data writes/calls. Debugger changes scheduling.',
'''// Observation only: native RNG entry, per-thread return, and global state writes.
// No game code/data writes, no DLL injection. Debugger changes scheduling.''')
prefix=prefix.replace('struct TracedThread { HANDLE handle; Registers original; };',
'''struct PendingCall { uint64_t id=0,rsp=0,caller=0; uint32_t before=0; int32_t argument=0; bool range=false; };
struct TracedThread { HANDLE handle; Registers original; PendingCall pending; };''')
prefix=prefix.replace('static uint64_t sequence=0, stageSamples=0, casualtySamples=0, moveSamples=0, fixtureSamples=0;',
                      'static uint64_t sequence=0, stageSamples=0, fixtureSamples=0, callCount=0, returnCount=0, abandonedCalls=0;')
prefix=prefix.replace('static uint64_t rngAddress=0;','static uint64_t rngAddress=0, rangeAddress=0, percentageAddress=0;')
core=r'''
static void stackRecord(FILE* log,HANDLE p,const CONTEXT& c) {
    std::fprintf(log,",\"registers\":{\"rip\":%llu,\"rsp\":%llu,\"rax\":%llu,\"rcx\":%llu,\"rdx\":%llu,\"rbp\":%llu,\"rbx\":%llu,\"rsi\":%llu,\"rdi\":%llu,\"r8\":%llu,\"r9\":%llu,\"r10\":%llu,\"r11\":%llu,\"r12\":%llu,\"r13\":%llu,\"r14\":%llu,\"r15\":%llu}",
        c.Rip,c.Rsp,c.Rax,c.Rcx,c.Rdx,c.Rbp,c.Rbx,c.Rsi,c.Rdi,c.R8,c.R9,c.R10,c.R11,c.R12,c.R13,c.R14,c.R15);
    unsigned char stack[2048];SIZE_T n=0;size_t len=sizeof(stack);
    while(len>=64&&!(ReadProcessMemory(p,reinterpret_cast<void*>(c.Rsp),stack,len,&n)&&n==len))len/=2;
    std::fprintf(log,",\"stack_hex\":\"");if(len>=64)hexBytes(log,stack,len);std::fprintf(log,"\"");
}
static bool observe(FILE* log,HANDLE p,uint64_t base,CONTEXT& c,DWORD tid,TracedThread& t) {
    const unsigned bits=unsigned(c.Dr6&15);
    if(!bits||(bits&(bits-1)))throw std::runtime_error("Ambiguous hardware marker bits");
    bool entry=bits==1||bits==2,returned=bits==8,write=bits==4;
    auto state=rd<uint32_t>(p,rngAddress);
    if(entry){
        if(t.pending.id)throw std::runtime_error("Nested entry in audited leaf RNG");
        auto caller=rd<uint64_t>(p,c.Rsp);
        MEMORY_BASIC_INFORMATION region{};
        if(!VirtualQueryEx(p,reinterpret_cast<void*>(caller),&region,sizeof(region))||
           region.State!=MEM_COMMIT||!(region.Protect&(PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)))
            throw std::runtime_error("Native return address is not executable");
        t.pending={++callCount,c.Rsp,caller,state,int32_t(c.Rcx),bits==1};
        c.Dr3=caller;c.Dr7|=0x40;
    }
    if(returned&&(!t.pending.id||c.Rip!=t.pending.caller||c.Rsp!=t.pending.rsp+8))
        throw std::runtime_error("Native call/return stack mismatch");
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"tick_ms\":%llu,\"call_id\":%llu,\"rip\":%llu,\"rng_snapshot\":%u",
        entry?"rng_entry":returned?"rng_return":"rng_write",++sequence,tid,GetTickCount64(),t.pending.id,c.Rip,state);
    if(!fixtureMode){
        auto root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
        if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
        std::fprintf(log,",");routeContext(log,p,base,world);
    }
    if(entry||returned){
        auto& q=t.pending;
        std::fprintf(log,",\"kind\":\"%s\",\"argument\":%d,\"entry_rng_snapshot\":%u,\"caller\":%llu,\"entry_rsp\":%llu",
            q.range?"range":"percentage",q.argument,q.before,q.caller,q.rsp);
        if(returned){std::fprintf(log,",\"result\":%d,\"return_rsp\":%llu",int32_t(c.Rax),c.Rsp);returnCount++;}
    }
    if(write){
        std::fprintf(log,",\"previous_observed\":%u,\"observed_after\":%u",previousObservedRng,state);
        previousObservedRng=state;
    }
    if(entry||write)stackRecord(log,p,c);
    std::fprintf(log,"}\n");std::fflush(log);
    if(returned){t.pending={};c.Dr3=0;c.Dr7&=~DWORD64(0x40);}
    stageSamples++;started=true;
    return sequence>=12000;
}
static uint64_t unfinished(const std::map<DWORD,TracedThread>& threads){
    uint64_t n=0;for(const auto& row:threads)if(row.second.pending.id)n++;return n;
}
'''
tail=old[old.index('int wmain'):]
tail=tail.replace('        6;','        8;')
tail=tail.replace('Usage: probe pid base rva timeout_seconds log.jsonl [expected.bin recorded.bin]',
                  'Usage: probe pid base range_address percentage_address rng_address timeout_seconds log.jsonl')
tail=tail.replace('uint64_t base=_wcstoui64(argv[2],nullptr,0), rva=_wcstoui64(argv[3],nullptr,0), target=base+rva;',
'''uint64_t base=_wcstoui64(argv[2],nullptr,0);
    rangeAddress=_wcstoui64(argv[3],nullptr,0);percentageAddress=_wcstoui64(argv[4],nullptr,0);rngAddress=_wcstoui64(argv[5],nullptr,0);''')
tail=tail.replace('wcstoul(argv[4],nullptr,0)','wcstoul(argv[6],nullptr,0)').replace('argv[5])+L".stop"','argv[7])+L".stop"')
tail=tail.replace('!base || rva>0x3000000','!base || !rangeAddress || !percentageAddress || !rngAddress')
tail=tail.replace('_wfsopen(argv[5],','_wfsopen(argv[7],')
tail=tail.replace('pending_watch_fixture.exe','rng_pair_target_fixture.exe')
tail=tail.replace('        rngAddress=fixtureMode?target:base+0x18EB8B0;\n','')
tail=tail.replace('if(!fixtureMode && rva!=0x15B070) throw std::runtime_error("Unexpected native observer entry");',
'''if(!fixtureMode && (rangeAddress!=base+0x3AA7C0||percentageAddress!=base+0x3AA3F0||rngAddress!=base+0x18EB8B0))
            throw std::runtime_error("Unexpected native observer addresses");''')
tail=tail.replace('uint8_t code[16]; readExact(process,target,code,sizeof(code));','uint8_t code[16]; readExact(process,rangeAddress,code,sizeof(code));')
tail=tail.replace('std::fprintf(log,"{\\"event\\":\\"attached\\",\\"pid\\":%lu,\\"target_rva\\":%llu}\\n",pid,rva);',
                   'std::fprintf(log,"{\\"event\\":\\"attached\\",\\"pid\\":%lu,\\"base\\":%llu,\\"range_address\\":%llu,\\"percentage_address\\":%llu,\\"rng_address\\":%llu}\\n",pid,base,rangeAddress,percentageAddress,rngAddress);')
tail=tail.replace(' || (!fixtureMode&&started&&pastTurn(process,base))','')
tail=tail.replace('TracedThread{th,saved}','TracedThread{th,saved,{}}')
begin=tail.index('                        c.Dr0=fixtureMode?0:target;')
end=tail.index('                        check(SetThreadContext(th,&c)',begin)
tail=tail[:begin]+'''                        c.Dr0=rangeAddress;c.Dr1=percentageAddress;c.Dr2=rngAddress;c.Dr3=0;c.Dr6=0;
                        // Entry L0/L1; RNG write L2/RW2=01/LEN2=11; L3 armed per pending return.
                        c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x0d000015;
'''+tail[end:]
begin=tail.index('                        bool ours=')
end=tail.index('                        if(ours)',begin)
tail=tail[:begin]+'''                        bool ours=(c.Dr6&4)||((c.Dr6&1)&&c.Rip==rangeAddress)||((c.Dr6&2)&&c.Rip==percentageAddress)||
                            ((c.Dr6&8)&&it->second.pending.id&&c.Rip==it->second.pending.caller);
'''+tail[end:]
tail=tail.replace('observe(log,process,base,c,event.dwThreadId)','observe(log,process,base,c,event.dwThreadId,it->second)')
tail=tail.replace('if(it!=threads.end()) { CloseHandle(it->second.handle); threads.erase(it); }',
'''if(it!=threads.end()) {
                    if(it->second.pending.id){
                        abandonedCalls++;
                        std::fprintf(log,"{\\"event\\":\\"thread_exit_with_pending\\",\\"thread\\":%lu,\\"call_id\\":%llu}\\n",event.dwThreadId,it->second.pending.id);
                    }
                    CloseHandle(it->second.handle);threads.erase(it);
                }''')
tail=tail.replace('std::fprintf(log,"{\\"event\\":\\"detached\\",\\"captured\\":%s,\\"registers_restored\\":true}\\n",hit?"true":"false");',
'''std::fprintf(log,"{\\"event\\":\\"detached\\",\\"captured\\":%s,\\"registers_restored\\":true,\\"entries\\":%llu,\\"returns\\":%llu,\\"unfinished_calls\\":%llu,\\"abandoned_calls\\":%llu}\\n",hit?"true":"false",callCount,returnCount,unfinished(threads),abandonedCalls);''')
tail=tail.replace('if(SuspendThread(thread.handle)==DWORD(-1)) continue;',
                  'if(SuspendThread(thread.handle)==DWORD(-1)){restored=false;continue;}')
assert 'pastTurn' not in tail and 'target' not in tail.replace('rng_pair_target_fixture','fixture') and 'rva' not in tail
(ROOT/'observe_rng_pairs.cpp').write_text(prefix+core+tail)
native=(ROOT/'rng_route_native_fixture.h').read_text().replace('    uint32_t get()',
    '    uintptr_t fixtureAddress(unsigned offset){return reinterpret_cast<uintptr_t>(code+offset);}\n    uint32_t get()')
(ROOT/'rng_pair_native_fixture.h').write_text(native)
