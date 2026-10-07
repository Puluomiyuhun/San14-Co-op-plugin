// Included after helpers; these observers never call original Update themselves.
struct PushSaveObservation {uint64_t call=0;DWORD phase=0;bool observed=false,terminal=false;};
static thread_local PushSaveObservation saveObservation;
static void saveBefore(const CheckpointPushFrame* frame,void*) noexcept {
    InterlockedIncrement(reinterpret_cast<volatile LONG*>(&CheckpointPushReport.saveActiveCallbacks));
    saveObservation={frame->call_id,0,false,false};
    __try {
        ++CheckpointPushReport.saveCallbacks;
        auto self=uintptr_t(frame->args[0]),manager=base+MANAGER,stack=at<uintptr_t>(manager+0x20);
        bool related=self==CheckpointPushReport.queuedState && at<uint64_t>(manager+0x10)==6 && stack &&
            at<uintptr_t>(stack+40)==self && at<uintptr_t>(self)==base+0x12DC5F8 && boundSaveRequest();
        for(unsigned i=0;related&&i<5;++i)related=at<uintptr_t>(stack+i*8)==pinnedStates[i];
        if(!related){CheckpointPushReport.saveObservationError=60;restoreSaveSlot();restoreSlot();return;}
        auto phase=at<DWORD>(self+0x470);
        if(phase>4){CheckpointPushReport.saveObservationError=61;restoreSaveSlot();restoreSlot();return;}
        saveObservation.phase=phase;saveObservation.observed=true;saveObservation.terminal=phase==4;
        CheckpointPushReport.saveAssociationOk=1;CheckpointPushReport.savePhaseMask|=1u<<phase;
        if(phase==4){
            CheckpointPushReport.saveNativeSuccess=at<DWORD>(base+0x201EC2C)==1;
            CheckpointPushReport.saveFinalizerCalled=1;
            if(!restoreSaveSlot())CheckpointPushReport.saveObservationError=62;
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        CheckpointPushReport.saveObservationError=63;restoreSaveSlot();restoreSlot();
    }
}
static void saveAfter(const CheckpointPushFrame* frame,void*) noexcept {
    __try {
        ++CheckpointPushReport.saveOriginalCalls;CheckpointPushReport.saveRawRax=frame->result_rax;
        if(saveObservation.call!=frame->call_id){CheckpointPushReport.saveObservationError=68;saveObservation.observed=false;restoreSaveSlot();restoreSlot();}
        if(saveObservation.observed&&!saveObservation.terminal){
            auto next=at<DWORD>(uintptr_t(frame->args[0])+0x470);
            if(saveObservation.phase==1&&next==2)CheckpointPushReport.saveWorkerStarted=1;
            if(saveObservation.phase==2&&next==3)CheckpointPushReport.saveWorkerJoined=1;
        }
        if(saveObservation.observed&&saveObservation.terminal){
            // Native finalizer only QUEUES its pop; final User is observed separately.
            CheckpointPushReport.saveFinalizerReturned=1;
            CheckpointPushReport.saveGlobalsCleared=stringsIdle()&&cacheCleared();
            CheckpointPushReport.finalizedAt=GetTickCount64();
            CheckpointPushReport.saveObservationDone=1;
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        CheckpointPushReport.saveObservationError=64;restoreSaveSlot();restoreSlot();
    }
    InterlockedDecrement(reinterpret_cast<volatile LONG*>(&CheckpointPushReport.saveActiveCallbacks));
}
