// Private parent/owned-child control only. No server, network, paths or pointers
// accepted over stdin. This file has no game discovery or live-game adapter.
static std::string runtimeHex(const unsigned char*p,size_t n){
    static const char h[]="0123456789abcdef";std::string s;for(size_t i=0;i<n;++i){s+=h[p[i]>>4];s+=h[p[i]&15];}return s;
}
static bool runtimeId(const std::string&s,unsigned char out[16]){
    if(s.size()!=32)return false;unsigned any=0;
    for(unsigned i=0;i<16;++i){unsigned v=0;for(unsigned j=0;j<2;++j){char c=s[i*2+j];if(c>='0'&&c<='9')v=v*16+unsigned(c-'0');else if(c>='a'&&c<='f')v=v*16+unsigned(c-'a'+10);else return false;}out[i]=static_cast<unsigned char>(v);any|=v;}return any!=0;
}
static bool runtimeLine(std::string&line,DWORD timeout){
    const auto end=GetTickCount64()+timeout;HANDLE input=GetStdHandle(STD_INPUT_HANDLE);line.clear();
    while(GetTickCount64()<end){DWORD n=0;if(!PeekNamedPipe(input,nullptr,0,nullptr,&n,nullptr))return false;
        if(!n){Sleep(5);continue;}char c=0;DWORD got=0;if(!ReadFile(input,&c,1,&got,nullptr)||got!=1)return false;
        if(c=='\n')return true;if(c<' '||c>'~'||line.size()>=100)return false;line+=c;
    }return false;
}
static bool runtimeCommand(const std::string&line,const char*command,std::string&a,std::string&i){
    const std::string prefix=std::string(command)+" ";if(line.size()!=prefix.size()+65||line.compare(0,prefix.size(),prefix)||line[prefix.size()+32]!=' ')return false;
    a=line.substr(prefix.size(),32);i=line.substr(prefix.size()+33);unsigned char x[16]{},y[16]{};return runtimeId(a,x)&&runtimeId(i,y);
}
static bool runtimeDurable(const std::wstring&path,const std::string&value){
    HANDLE h=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);if(h==INVALID_HANDLE_VALUE)return false;
    DWORD n=0;bool ok=WriteFile(h,value.data(),static_cast<DWORD>(value.size()),&n,nullptr)&&n==value.size()&&FlushFileBuffers(h);if(!CloseHandle(h))ok=false;return ok;
}
static bool runtimeArchive(const std::wstring&path){
    FILE*f=nullptr;_wfopen_s(&f,path.c_str(),L"rb");if(!f)return false;std::vector<unsigned char> raw(by::TargetSize);const bool exact=fread(raw.data(),1,raw.size(),f)==raw.size()&&fgetc(f)==EOF;fclose(f);
    unsigned char hash[32]{};return exact&&native_storage_read::Sha256(raw.data(),raw.size(),hash)&&!memcmp(hash,by::TargetSha256,32);
}
static bool runtimeMarker(const std::wstring&path,const std::string&expected){
    FILE*f=nullptr;_wfopen_s(&f,path.c_str(),L"rb");if(!f)return false;std::vector<char>raw(expected.size());bool ok=fread(raw.data(),1,raw.size(),f)==raw.size()&&fgetc(f)==EOF;fclose(f);return ok&&!memcmp(raw.data(),expected.data(),raw.size());
}
static const char*runtimeWorldSource="verified_workspace_stage";
static std::uint64_t runtimeBirth(){FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return 0;return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
static void runtimeError(const char*message){printf("{\"event\":\"ERROR\",\"error\":\"%s\",\"fullWorldVerified\":false,\"inputExclusionProven\":false,\"native_gameplay_enabled\":false}\n",message);fflush(stdout);}
static void runtimeResult(const std::string&attempt,const std::string&intent,std::uint64_t birth,int code){
    ns::Report r{};session.Snapshot(r);pr::Report p{};pr::Snapshot(planning,p);ad::Report ar{};const bool admittedSnapshot=admission.Snapshot(ar);
    unsigned authorized=0,archiveExecutions=0;for(auto item:admissionTrace){if(item==unsigned(ad::Event::Authorize))++authorized;if(item==101)++archiveExecutions;}
    const bool prefetched=admittedSnapshot&&ar.prefetch.status==pf::Status::Observed;
    const bool eligible=prefetched&&!ar.blocked&&ar.error==ad::Error::None&&ar.after.pending_admission_candidate;

    const bool bound=r.attempt==runtimeAttempt&&p.attempt==runtimeAttempt&&p.epoch==runtimeEpoch;
    const bool linked=p.identityWorkerCall==r.identity.workerCall&&p.completedLoadCall==r.lifecycle.completedCall;
    const bool binding=bound&&(!p.planningBoundaryObserved||linked);
    const BYTE observedForce=at<BYTE>(world+0x3A);
    const unsigned observedRuler=observedForce==2?at<WORD>(forceB+0x10):observedForce==12?at<WORD>(forceA+0x10):0;
    const bool noClaims=admittedSnapshot&&!ar.full_input_hold&&!ar.game_hook_installed&&!r.inputExclusionProven&&!r.presentationProven&&!r.nativePlanningReady&&!r.fullWorldVerified&&
        !p.fullWorldVerified&&!p.inputExclusionProven&&!p.pixelPresentationProven&&!p.oldStateDestructorsDirectlyObserved&&!p.allWorkersFinishedProven;
    printf("{\"event\":\"RUNTIME_RESULT\",\"schema\":\"san14.admitted-runtime-fixture.v1\",\"provenance\":\"FIXTURE_ONLY\",\"pid\":%lu,\"birth\":\"%llu\",\"attempt\":\"%s\",\"intent\":\"%s\",\"binding_sha256\":\"%s\",\"native_attempt\":\"%llu\",\"observer_epoch\":\"%llu\",\"native_binding_matches\":%s,\"fixture_case\":\"%ls\",\"fixture_checks_passed\":%s,\"fixture_failures\":%u,\"session_state\":%u,\"session_error\":%ld,\"session_exception\":%lu,\"armed\":%u,\"cas_attempts\":%u,\"cas_published\":%u,\"request_intent_durable\":%s,\"preflight_read_calls\":%u,\"bytesReady\":%u,\"lifecycleReady\":%u,\"identityReady\":%u,\"planningBoundaryObserved\":%u,\"planning_error\":%ld,\"planning_failed_field\":\"%s\",\"planning_before\":%u,\"planning_after\":%u,\"planning_inflight\":%u,\"planning_user_call\":\"%llu\",\"identity_worker_call\":\"%llu\",\"completed_load_call\":\"%llu\",\"planning_upstream_links_match\":%s,\"session_active_dispatch\":%u,\"session_active_worker\":%u,\"session_active_read\":%u,\"dispatch_unpaired\":%u,\"user_controller_calls\":%u,\"old_user_calls\":%u,\"new_user_calls\":%u,\"load_worker_calls\":%u,\"load_update_calls\":%u,\"worker_join_calls\":%u,\"actual_archive_read_sha256\":\"%s\",\"actual_archive_read_bytes\":%u,\"identity_force\":%u,\"identity_ruler\":%u,\"planning_thread\":%lu,\"planning_native_rax\":\"%llu\",\"unsupported_claims_clear\":%s,\"fullWorldVerified\":false,\"inputExclusionProven\":false,\"pixelPresentationProven\":false,\"native_gameplay_enabled\":false,\"game_access\":false,\"native_game_code_executed\":false,\"upstream_receipts_fabricated\":false,\"fixed_archive_only\":true,\"consumed_world_source\":\"%s\",\"admission_wired\":true,\"admission_prefetched\":%s,\"admission_eligible\":%s,\"admission_blocked\":%s,\"admission_error\":%u,\"admission_pending_error\":%u,\"admission_pending_decision\":%u,\"admission_queue_authorizations\":%u,\"admission_queue_calls\":%u,\"admission_queue_returned\":%u,\"admission_commit_succeeded\":%u,\"admission_menu_bound\":%u,\"admission_scope_started\":%u,\"admission_scope_finished\":%u,\"admission_original_abnormal\":%u,\"admission_reentry\":%u,\"admission_native_rax\":\"%llu\",\"admission_native_fetched\":%d,\"archived_menu_block_executed_in_owned_rx\":%s,\"production_enabled\":false,\"same_process_repeat_load_proven\":false}\n",
        GetCurrentProcessId(),static_cast<unsigned long long>(birth),attempt.c_str(),intent.c_str(),runtimeHex(runtimeBinding,32).c_str(),
        static_cast<unsigned long long>(runtimeAttempt),static_cast<unsigned long long>(runtimeEpoch),binding?"true":"false",scenario.c_str(),code==0&&noClaims?"true":"false",failures,unsigned(r.state),r.error,r.exceptionCode,r.armed,r.request.casAttempts,r.casPublished,r.request.intentDurable?"true":"false",r.request.read.readCalls,
        r.bytes.observedWorkerAndBytes,r.lifecycle.receiptReady,r.identity.receiptReady,p.planningBoundaryObserved,p.error,p.failedField,p.before,p.after,p.inFlight,
        static_cast<unsigned long long>(p.userCall),static_cast<unsigned long long>(p.identityWorkerCall),static_cast<unsigned long long>(p.completedLoadCall),linked?"true":"false",r.activeDispatch,r.activeWorker,r.activeRead,r.dispatchUnpaired,r.userControllerCalls,userBodies-planningBodies,planningBodies,loadBodies,updateCalls,joinCalls,
        runtimeHex(r.bytes.sha256,32).c_str(),r.bytes.returned,unsigned(observedForce),observedRuler,p.thread,static_cast<unsigned long long>(p.nativeRax),noClaims?"true":"false",runtimeWorldSource,prefetched?"true":"false",eligible?"true":"false",ar.blocked?"true":"false",unsigned(ar.error),unsigned(ar.after.error),unsigned(ar.after.decision),authorized,ar.queue_calls,ar.queue_returned,ar.commit_succeeded,ar.menu_bound,ar.scope_started,ar.scope_finished,ar.original_abnormal,ar.reentry,static_cast<unsigned long long>(ar.native_rax),PrefetchFixtureFetched,archiveExecutions?"true":"false");fflush(stdout);
}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);std::wstring chosen=L"success-new";
    if(argc==3&&!wcscmp(argv[1],L"--case"))chosen=argv[2];else if(argc!=1)return 2;
    const wchar_t*allowed[]={L"success-new",L"success-reused",L"entry-pending",L"late-pending",L"entry-ui",L"missing-prefetch",L"wrong-site",L"wrong-menu",L"foreign-menu",L"queue-exception",L"original-exception",L"reentry",L"stop-original",L"stop-before-user",L"stop-queue",L"stop-after-cas",L"actual-byte-mismatch",L"user-exception",L"report-state",L"stale-attempt",L"epoch-after"};
    bool known=false;for(auto item:allowed)known=known||chosen==item;if(!known)return 2;
    wchar_t image[32768]{};const auto length=GetModuleFileNameW(nullptr,image,_countof(image));if(!length||length>=_countof(image))return 3;auto slash=wcsrchr(image,L'\\');if(!slash)return 3;*slash=0;std::wstring directory=image;
    const auto birth=runtimeBirth();if(!birth)return 3;
    printf("{\"event\":\"PREPARED\",\"schema\":\"san14.admitted-runtime-fixture.v1\",\"provenance\":\"FIXTURE_ONLY\",\"pid\":%lu,\"birth\":\"%llu\",\"has_window\":false,\"archive_sha256\":\"%s\",\"archive_size\":%u,\"fixture_case\":\"%ls\",\"fixed_archive_only\":true}\n",GetCurrentProcessId(),static_cast<unsigned long long>(birth),runtimeHex(by::TargetSha256,32).c_str(),by::TargetSize,chosen.c_str());fflush(stdout);
    std::string line,attempt,intent;if(!runtimeLine(line,120000))return 4;if(line=="STOP"){printf("{\"event\":\"CLOSED\",\"arm_consumed\":false}\n");fflush(stdout);return 0;}
    if(!runtimeCommand(line,"BIND",attempt,intent)){runtimeError("BIND_REQUIRED");return 4;}
    unsigned char a[16]{},i[16]{};runtimeId(attempt,a);runtimeId(intent,i);memcpy(runtimeAttemptId,a,16);
    static const char domain[]="san14.guest-runtime-fixture.binding.v1";std::vector<unsigned char> input(domain,domain+sizeof(domain)-1);input.insert(input.end(),a,a+16);input.insert(input.end(),i,i+16);
    if(!native_storage_read::Sha256(input.data(),input.size(),runtimeBinding))return 4;
    memcpy(&runtimeAttempt,runtimeBinding,8);memcpy(&runtimeEpoch,runtimeBinding+8,8);if(!runtimeAttempt||!runtimeEpoch)return 4;
    std::wstring source;const auto stage=directory+L"\\checkpoint_admitted_runtime_stages\\"+std::wstring(attempt.begin(),attempt.end());
    DWORD attrs=GetFileAttributesW(stage.c_str());
    if(attrs!=INVALID_FILE_ATTRIBUTES){
        if(!(attrs&FILE_ATTRIBUTE_DIRECTORY)||(attrs&FILE_ATTRIBUTE_REPARSE_POINT)){runtimeError("INVALID_STAGE_DIRECTORY");return 4;}
        source=stage+L"\\world.s14";const auto marker=stage+L"\\stage-ready.json",once=stage+L"\\stage-once.json";
        const std::string expected="{\"attempt\":\""+attempt+"\",\"intent\":\""+intent+"\",\"sha256\":\""+runtimeHex(by::TargetSha256,32)+"\",\"size\":274880}";
        for(auto path:{source,marker,once}){attrs=GetFileAttributesW(path.c_str());if(attrs==INVALID_FILE_ATTRIBUTES||(attrs&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))){runtimeError("INVALID_STAGE_FILE");return 4;}}
        if(!runtimeMarker(marker,expected)||!runtimeMarker(once,expected)||!runtimeArchive(source)){runtimeError("STAGE_BINDING_OR_BYTES_REJECTED");return 4;}
        runtimeWorldSource="verified_workspace_stage";
    }else {runtimeError("STAGED_ARCHIVE_REQUIRED");return 4;}
    const auto parent=directory+L"\\checkpoint_admitted_runtime_runs";if(!CreateDirectoryW(parent.c_str(),nullptr)&&GetLastError()!=ERROR_ALREADY_EXISTS)return 4;
    attrs=GetFileAttributesW(parent.c_str());if(attrs==INVALID_FILE_ATTRIBUTES||!(attrs&FILE_ATTRIBUTE_DIRECTORY)||(attrs&FILE_ATTRIBUTE_REPARSE_POINT)){runtimeError("INVALID_RUN_ROOT");return 4;}
    const auto run=parent+L"\\"+std::wstring(attempt.begin(),attempt.end());if(!CreateDirectoryW(run.c_str(),nullptr)){runtimeError("ATTEMPT_DIRECTORY_EXISTS");return 4;}
    const auto local=run+L"\\svdexccSC03.s14",request=run+L"\\load-request.intent",identity=run+L"\\identity.intent";
    const std::string binding="{\"schema\":\"san14.admitted-runtime-fixture-binding.v1\",\"attempt\":\""+attempt+"\",\"intent\":\""+intent+"\",\"binding_sha256\":\""+runtimeHex(runtimeBinding,32)+"\",\"fixed_archive_only\":true,\"game_access\":false}";
    if(!runtimeDurable(run+L"\\binding.json",binding)||!CopyFileW(source.c_str(),local.c_str(),TRUE)||!runtimeArchive(local)){runtimeError("LOCAL_STAGE_FAILED");return 4;}
    printf("{\"event\":\"BOUND\",\"attempt\":\"%s\",\"intent\":\"%s\",\"binding_sha256\":\"%s\",\"native_attempt\":\"%llu\",\"observer_epoch\":\"%llu\",\"archive_sha256\":\"%s\",\"archive_size\":%u,\"armed\":false,\"consumed_world_source\":\"%s\"}\n",attempt.c_str(),intent.c_str(),runtimeHex(runtimeBinding,32).c_str(),static_cast<unsigned long long>(runtimeAttempt),static_cast<unsigned long long>(runtimeEpoch),runtimeHex(by::TargetSha256,32).c_str(),by::TargetSize,runtimeWorldSource);fflush(stdout);
    if(!runtimeLine(line,120000))return 4;
    if(line=="STOP "+attempt+" "+intent){printf("{\"event\":\"CLOSED\",\"arm_consumed\":false}\n");fflush(stdout);return 0;}
    if(line!="ARM "+attempt+" "+intent){runtimeError("EXACT_ARM_REQUIRED");return 4;}
    // Durable control intent is reserved before even entering the first setup/
    // Initialize/Arm call. A lost result can never resend this process's ARM.
    if(!runtimeDurable(run+L"\\arm-once.json",binding)){runtimeError("ARM_INTENT_UNCONFIRMED");return 4;}
    wchar_t label[]=L"owned-runtime";wchar_t*args[]={label,const_cast<wchar_t*>(chosen.c_str()),const_cast<wchar_t*>(local.c_str()),const_cast<wchar_t*>(request.c_str()),const_cast<wchar_t*>(identity.c_str())};
    const int result=runBoundSession(5,args);runtimeResult(attempt,intent,birth,result);
    while(runtimeLine(line,120000)){
        if(line=="STOP "+attempt+" "+intent){session.Stop();printf("{\"event\":\"CLOSED\",\"arm_consumed\":true,\"observers_retained_until_process_exit\":true}\n");fflush(stdout);return result;}
        runtimeError("ARM_ALREADY_CONSUMED");
    }
    session.Stop();return result;
}
