"""Adapt own-process guard fixtures; actual dispatcher coverage is separate."""
from pathlib import Path
P=Path(__file__).resolve().parent
p=P/'checkpoint_push_fixture.cpp';s=p.read_text(encoding='utf8')
s=s.replace('static void __fastcall original(', 'static uint64_t __fastcall original(')
s=s.replace('if(test==L"original-drift")put<uint32_t>(user+0x470,5);','if(test==L"original-drift")put<uint32_t>(user+0x470,5);\n    return 0xFEDCBA9876543210ULL;')
s=s.replace('static void __fastcall enqueue(void* manager,const char* name,uintptr_t argument){',
'''static void __fastcall enqueue(void* manager,const char* name,uintptr_t argument,void* carrier){
    if(!carrier)argumentsOk=false;
    else for(unsigned i=0;i<64;++i)if(reinterpret_cast<unsigned char*>(carrier)[i])argumentsOk=false;''')
s=s.replace('put<uint32_t>(q,2);','put<uint32_t>(q,test==L"type2-queue"?2:0);')
s=s.replace('static void __fastcall saveOriginal(', 'static uint64_t __fastcall saveOriginal(')
s=s.replace('put<uint64_t>(manager+0x10,5);put<uint64_t>(manager+0x30,0);\n    }\n}',
'''put<uint64_t>(manager+0x10,5);put<uint64_t>(manager+0x30,0);
        if(test==L"return-phase-drift")put<uint32_t>(user+0x470,5);
        if(test==L"return-object-changed")put<uintptr_t>(image+0x210000+32,user+0x1000);
        if(test==L"return-rng-drift")put<uint32_t>(image+0x18EB8B0,123);
        if(test==L"return-advance")put<uint32_t>(image+0x202000+0x47C,1);
        if(test==L"return-pending-menu")put<int32_t>(image+0x280000+0x88,6);
        if(test==L"return-queue-pending")put<uint64_t>(manager+0x30,1);
    }
    return 0x0123456789ABCDEFULL;
}''')
s=s.replace('f(reinterpret_cast<void*>(user),0x1122,0x3344,0x5566);','if(f(reinterpret_cast<void*>(user),0x1122,0x3344,0x5566)!=0xFEDCBA9876543210ULL)argumentsOk=false;')
s=s.replace('f(reinterpret_cast<void*>(s),0,0,0);','if(f(reinterpret_cast<void*>(s),0,0,0)!=0x0123456789ABCDEFULL)argumentsOk=false;')
s=s.replace('''    }
    return 0;
}
int wmain''','''        if(*reinterpret_cast<uint64_t*>(manager+0x10)==5){
            auto f=*reinterpret_cast<SaveUpdate*>(image+0x12CC4A8+0x28);
            if(f(reinterpret_cast<void*>(user),0x1122,0x3344,0x5566)!=0xFEDCBA9876543210ULL)argumentsOk=false;
        }
    }
    return 0;
}
int wmain''')
s=s.replace('input.version=1','input.version=2')
at='    const bool dryCase='
idx=s.index(at)
s=s[:idx]+'''    // Synthetic backing fields for the stricter planning boundary guard.
    put<int32_t>(image+0x280000+0x88,-1);
    put<uintptr_t>(image+0x202000+0x480,image+0x2B0000);
    put<uint32_t>(image+0x19E7510+0x13C,1);
    if(test==L"cache-mode-one")put<uint32_t>(image+0x290000+8,1);
    if(test==L"selected-object")put<uintptr_t>(user+0x4A8,root+0x8B000);
    if(test==L"advance-pending")put<uint32_t>(image+0x202000+0x47C,1);
    if(test==L"toolbar-pending")put<int32_t>(image+0x280000+0x88,6);
    if(test==L"control-paused")put<uint32_t>(image+0x1A38EC8+0x28,1);
    if(test==L"cursor-disabled")put<uint32_t>(image+0x19E7510+0x13C,0);
    if(test==L"secondary-active")put<uint32_t>(image+0x290000+0x3F0,1);
'''+s[idx:]
s=s.replace('const bool successCase=test==L"queue"', 'const bool successCase=test==L"cache-mode-one"||test==L"queue"')
s=s.replace('const bool queueWanted=successCase||test==L"queue-failure"||lifecycleCase;',
'''const bool returnFailure=test.rfind(L"return-",0)==0;
    const bool queueWanted=successCase||test==L"queue-failure"||test==L"type2-queue"||lifecycleCase||returnFailure;''')
s=s.replace('LONG expected=successCase||lifecycleCase?4:dryCase?3:test==L"cancel"?7:test==L"binder-exception"?6:5;',
'''LONG expected=successCase||test==L"native-failure"?8:
        (test==L"globals-not-cleared"||returnFailure)?5:lifecycleCase?4:dryCase?3:test==L"cancel"?7:test==L"binder-exception"?6:5;
    const unsigned expectedOriginals=(successCase||returnFailure||
        (lifecycleCase&&test!=L"save-stall"&&test!=L"bad-save-phase"))?12:11;''')
s=s.replace('originals==11&&argumentsOk','originals==expectedOriginals&&argumentsOk')
s=s.replace('if(successCase)passed=passed&&lifecycleOk;',
'''if(successCase)passed=passed&&lifecycleOk&&report->returnSeen&&report->returnMatched&&
        report->pinnedUser==user&&report->state==user&&report->beforeRng==report->afterRng&&
        report->userRawRax==0xFEDCBA9876543210ULL&&report->saveRawRax==0x0123456789ABCDEFULL;
    if(returnFailure)passed=passed&&!report->returnMatched;
    if(test==L"type2-queue")passed=passed&&report->queueItemVerified==0;''')
s=s.replace('if(test==L"save-stall")stopObserver(nullptr);','if(test==L"save-stall"||test==L"bad-save-phase")stopObserver(nullptr);')
p.write_text(s,encoding='utf8')
print('Candidate guard fixtures adapted; native scheduler proof remains separate')
