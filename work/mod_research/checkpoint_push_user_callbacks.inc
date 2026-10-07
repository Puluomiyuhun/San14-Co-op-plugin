static thread_local uint64_t firstClaimCall=0,returnClaimCall=0;
static void userBefore(const CheckpointPushFrame* frame,void*) noexcept {
    InterlockedIncrement(&CheckpointPushReport.activeCallbacks);
    __try {
        if(InterlockedCompareExchange(&claimed,1,0)==0){
            firstClaimCall=frame->call_id;CheckpointPushReport.firstUserCallId=frame->call_id;
            CheckpointPushReport.status=2;CheckpointPushReport.executorThread=frame->thread_id;
            CheckpointPushReport.caller=at<uintptr_t>(frame->caller_entry_rsp);
            CheckpointPushReport.state=frame->args[0];
        } else if(CheckpointPushReport.status==4&&CheckpointPushReport.saveObservationDone){
            // The scheduler, not this observer, has resumed and re-entered User.
            returnClaimCall=frame->call_id;CheckpointPushReport.returnSeen=1;
            CheckpointPushReport.returnThread=frame->thread_id;
            if(!guard(reinterpret_cast<void*>(frame->args[0]),true)){
                CheckpointPushReport.status=5;restoreSlot();
            }
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        CheckpointPushReport.exceptionCode=GetExceptionCode();CheckpointPushReport.status=6;restoreSlot();
    }
}
static void userAfter(const CheckpointPushFrame* frame,void*) noexcept {
    __try {
        ++CheckpointPushReport.originalCalls;CheckpointPushReport.userRawRax=frame->result_rax;
        if(frame->call_id==firstClaimCall&&CheckpointPushReport.status==2){
            if(CheckpointPushReport.stopRequested){CheckpointPushReport.status=7;restoreSaveSlot();restoreSlot();}
#ifndef CHECKPOINT_PUSH_FIXTURE
            if(CheckpointPushReport.caller!=base+0x50B785){reject(21);CheckpointPushReport.status=5;}
#endif
            if(CheckpointPushReport.status==2&&!guard(reinterpret_cast<void*>(frame->args[0])))CheckpointPushReport.status=5;
            if(CheckpointPushReport.status==2){
                if(!cfg.execute){
                    CheckpointPushReport.dryStorageQuery=1;
                    CheckpointPushReport.status=remoteSlotVacant()&&guard(reinterpret_cast<void*>(frame->args[0]))?3:5;
                }else CheckpointPushReport.status=queueOnce(reinterpret_cast<void*>(frame->args[0]))?4:5;
            }
            if(CheckpointPushReport.status!=4){restoreSaveSlot();restoreSlot();}
        }else if(frame->call_id==returnClaimCall&&CheckpointPushReport.status==4){
            const bool stable=guard(reinterpret_cast<void*>(frame->args[0]),true);
            CheckpointPushReport.afterRng=at<DWORD>(base+0x18EB8B0);
            CheckpointPushReport.cacheModeAfter=at<DWORD>(at<uintptr_t>(base+0x2025318)+8);
            CheckpointPushReport.lastUserCallId=frame->call_id;
            CheckpointPushReport.returnedAt=GetTickCount64();
            CheckpointPushReport.returnMatched=stable;
            CheckpointPushReport.status=stable&&restoreSlot()?8:5;
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        CheckpointPushReport.exceptionCode=GetExceptionCode();CheckpointPushReport.status=6;
        restoreSaveSlot();restoreSlot();
    }
    InterlockedDecrement(&CheckpointPushReport.activeCallbacks);
}
