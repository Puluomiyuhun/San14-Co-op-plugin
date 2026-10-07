// Private parse/allocation/cleanup only. Never calls Registration or writes a
// native cache link/table/pending field. Does not claim an exclusive game fence.
static bool leafCallAllowed(void*){
    return inOwnerAfter&&callbackDepth==1&&GetCurrentThreadId()==ownerThread&&
        loadState()==FP_READING&&!InterlockedCompareExchange(&stopped,0,0)&&
        !InterlockedCompareExchange(&extraCallbacks,0,0)&&currentGuard();
}
static bool leafPrivateNode(void*,const checkpoint_target_metadata::OwnedNode& node){
    __try {
        if(!leafCallAllowed(nullptr)||!node.pointer||!node.allocation)return false;
        auto p=uintptr_t(node.pointer);
        if(p<0x10000||p>0x00007FFFFFFFFE9Full)return false;
        auto overlaps=[p](uintptr_t x,size_t n){return p<x+n&&x<p+0x160;};
        if(overlaps(pinned.cache,0x440))return false;
        for(unsigned group=0;group<5;++group){
            auto list=pinned.cache+(group?0x400+(group-1)*16:0x10);
            auto head=probeAt<uintptr_t>(list),count=probeAt<uint64_t>(list+8);
            if(!head||count>120||overlaps(head,16))return false;
            auto at=probeAt<uintptr_t>(head),previous=head;
            for(uint64_t i=0;i<count;++i){
                if(at==head||!at||overlaps(at,0x160)||probeAt<uintptr_t>(at+8)!=previous)return false;
                previous=at;at=probeAt<uintptr_t>(at);
            }
            if(at!=head||probeAt<uintptr_t>(head+8)!=previous)return false;
        }
        for(unsigned i=0;i<120;++i){auto payload=probeAt<uintptr_t>(pinned.cache+0x20+i*8);
            if(payload&&overlaps(payload,0x150))return false;}
        return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
static bool doNativePrepare(native_storage_read::Lease& lease,TargetPrepareLeaf& result){
    try {
#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
        return cfg.testNativePrepare&&cfg.testNativePrepare(lease.bytes.data(),lease.bytes.size(),&result);
#else
        using namespace checkpoint_target_metadata;
        checkpoint_target_metadata_native::Adapter native;
        checkpoint_target_metadata_native::Access access{nullptr,leafCallAllowed,leafPrivateNode};
        Header parsed{};ParseReceipt receipt{};OwnedNode node{};
        bool bound=native.BindProduction(base,GetCurrentThreadId(),access);
        result.bound=bound;
        bool parsedOk=bound&&native.ParseVerifiedBytes(lease.bytes.data(),lease.bytes.size(),parsed,receipt);
        result.parsed=parsedOk;
        bool headerOk=parsedOk&&receipt.source==lease.bytes.data()&&receipt.length==lease.bytes.size()&&
            receipt.consumed==294&&!receipt.streamError&&!receipt.nativeFileOpens&&
            !memcmp(&parsed,&ExpectedParsedHeader,sizeof parsed);
        if(parsedOk){result.consumed=receipt.consumed;
            if(!native_storage_read::Sha256(&parsed,sizeof parsed,result.headerSha256))headerOk=false;}
        bool copied=false,released=false;
        if(headerOk&&leafCallAllowed(nullptr)){
            memcpy(parsed.bytes+0x128,TargetName,13);
            *reinterpret_cast<uint64_t*>(parsed.bytes+0x138)=12;
            *reinterpret_cast<uint64_t*>(parsed.bytes+0x140)=15;
            auto head=probeAt<uintptr_t>(pinned.cache+0x10);
            copied=native.CopyNode(reinterpret_cast<void*>(head),reinterpret_cast<void*>(head),parsed,node);
            result.copied=copied;
            if(copied&&native.OwnsNode(node))released=native.ReleaseNode(node);
        }
        const auto& r=native.GetReport();
        result.released=released;result.sourceUnchanged=r.sourceUnchanged;
        result.headerCtorCalls=r.headerCtorCalls;result.headerParserCalls=r.headerParserCalls;
        result.stringDtorCalls=r.stringDtorCalls;result.allocateCalls=r.allocateCalls;
        result.headerCopyCalls=r.headerCopyCalls;result.freeCalls=r.freeCalls;
        result.poisoned=r.poisoned;result.exceptionCode=r.exceptionCode;result.nodeState=unsigned(r.nodeState);
        result.node=r.node;result.allocationTicket=r.allocationTicket;strncpy_s(result.stage,r.stage,_TRUNCATE);
        result.success=headerOk&&copied&&released&&!node.pointer&&!r.poisoned&&r.sourceUnchanged&&
            r.borrowedStreamIntact&&r.fullBufferMatched&&leafCallAllowed(nullptr);
        return result.success!=0;
#endif
    }catch(...){result.poisoned=1;strncpy_s(result.stage,"prepare_unexpected_exception_no_retry",_TRUNCATE);return false;}
}
