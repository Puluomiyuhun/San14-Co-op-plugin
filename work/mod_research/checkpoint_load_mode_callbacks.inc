static void userBefore(const CheckpointPushFrame* f,void*) noexcept {
    InterlockedIncrement(&active);++depth;
    __try {__try {
        REPORT(++report.userBeforeCalls);
        if(InterlockedCompareExchange(&claim,1,0)==0){
            if(isStopped()||depth!=1){fail(50,"user_claim_reentrant_or_stopped",false);return;}
            ownerThread=f->thread_id;firstCall=f->call_id;auto caller=at<uintptr_t>(f->caller_entry_rsp);
            REPORT(report.queueThread=f->thread_id;report.firstUserCallId=f->call_id;report.userCaller=caller);
            if(f->args[0]!=cfg.expectedUser||!modeGuard(f->args[0],LM_GUARD_INITIAL)){fail(51,"initial_user_guard",false);return;}
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
            if(caller!=base+0x50B785){fail(52,"user_caller",false);return;}
#endif
            if(InterlockedCompareExchange(&state,LM_CLAIMED,LM_ARMED)!=LM_ARMED){fail(70,"state_changed_during_user_claim");return;}
        }else if(getState()==LM_CANCEL_QUEUED&&f->args[0]==cfg.expectedUser&&
                 at<uint64_t>(base+0x19E7310+0x10)==5&&at<uint64_t>(base+0x19E7310+0x30)==0){
            if(!modeGuard(f->args[0],LM_GUARD_RETURN)){fail(77,"returned_user_before_guard");return;}
            if(depth!=1){fail(53,"returned_user_depth");return;}
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
            if(at<uintptr_t>(f->caller_entry_rsp)!=base+0x50B785){fail(71,"returned_user_caller");return;}
#endif
            returnCall=f->call_id;returnOwnerThread=f->thread_id;REPORT(report.returnSeen=1;report.returnThread=f->thread_id;report.returnUserCallId=f->call_id);
            if(!restore(userHook))fail(54,"user_restore_before_returned_update");
        }
    }__except(EXCEPTION_EXECUTE_HANDLER){REPORT(report.exceptionCode=GetExceptionCode();++report.callbackFaults);fail(55,"user_before_exception");}}
    __finally {--depth;InterlockedDecrement(&active);}
}
static void userAfter(const CheckpointPushFrame* f,void*) noexcept {
    InterlockedIncrement(&active);++depth;
    __try {__try {
        REPORT(++report.userAfterCalls;report.userRawRax=f->result_rax);
        if(f->call_id==firstCall&&getState()==LM_CLAIMED){
            if(isStopped()){InterlockedExchange(&state,LM_CANCELLED);restore(userHook);return;}
            if(f->thread_id!=ownerThread||depth!=1||!modeGuard(f->args[0],LM_GUARD_INITIAL)){fail(56,"user_after_guard",false);return;}
            if(!cfg.execute){if(!restore(userHook)){fail(57,"dry_restore");return;}
                if(isStopped()||InterlockedCompareExchange(&state,LM_DRY_DONE,LM_CLAIMED)!=LM_CLAIMED){fail(72,"stopped_during_dry_cleanup");return;}stage("dry_guard_only");}
            else queueOnce();
        }else if(f->call_id==returnCall&&getState()==LM_CANCEL_QUEUED){
            bool matched=depth==1&&!isStopped()&&f->thread_id==returnOwnerThread&&modeGuard(f->args[0],LM_GUARD_RETURN);
            auto rng=at<DWORD>(base+0x18EB8B0),mode=at<DWORD>(pinned.cache+8);
            REPORT(report.returnMatched=matched;report.returnedRng=rng;report.returnedMode=mode);
            if(!matched){fail(58,"returned_user_after_guard");return;}
            if(!restore(menuHook)||!restore(userHook)){fail(59,"final_hook_cleanup");return;}
            if(isStopped()||InterlockedCompareExchange(&state,LM_USER_RETURNED,LM_CANCEL_QUEUED)!=LM_CANCEL_QUEUED){fail(73,"stopped_during_return_cleanup");return;}
            stage("same_user_returned_mode0");
        }
    }__except(EXCEPTION_EXECUTE_HANDLER){REPORT(report.exceptionCode=GetExceptionCode();++report.callbackFaults);fail(60,"user_after_exception");}}
    __finally {--depth;InterlockedDecrement(&active);}
}
static void menuBefore(const CheckpointPushFrame* f,void*) noexcept {
    InterlockedIncrement(&active);++depth;
    __try {__try {
        REPORT(++report.menuBeforeCalls);
        // Restore before original so any SEH/C++ exit leaves no menu hook.
        if(!restore(menuHook)){fail(61,"menu_restore_before_original");return;}
        if(InterlockedCompareExchange(&menuClaim,1,0)!=0){fail(62,"duplicate_menu_callback");return;}
        auto caller=at<uintptr_t>(f->caller_entry_rsp);menuCall=f->call_id;menuOwnerThread=f->thread_id;
        REPORT(report.menuCallId=f->call_id;report.menuThread=f->thread_id;report.menuCaller=caller);
        bool guarded=!isStopped()&&depth==1&&getState()==LM_QUEUED&&modeGuard(f->args[0],LM_GUARD_MENU);
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
        guarded=guarded&&caller==base+0x50B785;
#endif
        REPORT(report.menuGuardBefore=guarded;report.menuAssociation=f->args[0]==report.queuedState);
        if(!guarded){fail(63,"menu_before_guard");return;}
        if(InterlockedCompareExchange(&state,LM_MENU_CALLBACK,LM_QUEUED)!=LM_QUEUED){fail(74,"state_changed_before_menu_original");return;}
    }__except(EXCEPTION_EXECUTE_HANDLER){REPORT(report.exceptionCode=GetExceptionCode();++report.callbackFaults);fail(64,"menu_before_exception");}}
    __finally {--depth;InterlockedDecrement(&active);}
}
static void menuAfter(const CheckpointPushFrame* f,void*) noexcept {
    InterlockedIncrement(&active);++depth;
    __try {__try {
        REPORT(++report.menuAfterCalls;report.menuRawRax=f->result_rax;report.menuOriginalReturned=1);
        if(f->call_id!=menuCall||getState()!=LM_MENU_CALLBACK)return;
        if(f->thread_id!=menuOwnerThread){fail(75,"menu_after_thread_mismatch");return;}
        if(exactPop()){
            // A native cancel input may have queued one pop. Never append a
            // second pop. This operation is deliberately INCOMPLETE, not PASS.
            REPORT(report.nativeCancellationSeen=1);fail(65,"native_pop_already_queued_no_second_cancel");return;
        }
        const bool guarded=!isStopped()&&depth==1&&modeGuard(f->args[0],LM_GUARD_MENU);
        REPORT(report.menuGuardAfter=guarded);
        if(!guarded){fail(66,"menu_after_guard_no_cancel");return;}
        auto beforeCount=at<uint64_t>(base+0x19E7310+0x30);
        REPORT(report.cancelBefore=beforeCount;++report.cancelCalls);
        nativeCancel(reinterpret_cast<void*>(f->args[0]));
        const bool verified=exactPop();auto afterCount=at<uint64_t>(base+0x19E7310+0x30);
        REPORT(report.cancelReturned=1;report.cancelAfter=afterCount;report.cancelQueueVerified=verified);
        if(!verified){fail(67,"native_cancel_queue_not_verified");return;}
        if(isStopped()){fail(69,"stopped_during_native_cancel");return;}
        if(InterlockedCompareExchange(&state,LM_CANCEL_QUEUED,LM_MENU_CALLBACK)!=LM_MENU_CALLBACK){fail(76,"state_changed_during_native_cancel");return;}
        stage("cancel_queued_wait_same_user");
    }__except(EXCEPTION_EXECUTE_HANDLER){REPORT(report.exceptionCode=GetExceptionCode();++report.callbackFaults);fail(68,"menu_after_exception");}}
    __finally {--depth;InterlockedDecrement(&active);}
}
