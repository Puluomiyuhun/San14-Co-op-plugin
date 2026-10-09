// Read-only parent samples. A parent return is not proof of global worker drain.
static unsigned pointEpoch=0;
static uint64_t selectedUser=0,selectedStack=0,filteredHits=0;
static DWORD observationPid=0;
static uint64_t observationBirth=0,observationBase=0;
static bool chainComplete=false;
static const char* stopReason="timeout_or_cancel";
static char expectedName[64]{};
static bool setExpectedName(const wchar_t* s){unsigned i=0;for(;s[i]&&i<63;++i){if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='z')||s[i]=='-'))return false;expectedName[i]=char(s[i]);}return i&&i<63&&!s[i];}
static void need(bool v,const char* s){if(!v)throw std::runtime_error(s);}
static bool formalUser(HANDLE p,uint64_t b){const auto m=b+0x19E7310;return rd<uint64_t>(p,m+0x10)==5&&rd<uint64_t>(p,m+0x20)==selectedStack&&!rd<uint64_t>(p,m+0x30)&&rd<uint64_t>(p,selectedStack+32)==selectedUser&&rd<uint64_t>(p,selectedUser)==b+0x12CC4A8&&rd<DWORD>(p,selectedUser+0x470)==2&&!rd<DWORD>(p,selectedUser+0x68)&&rd<uint64_t>(p,b+0x12CC4D0)==b+0x3F9B00&&rd<uint64_t>(p,b+0x12CC9E0)==b+0x3F8140;}
static void emitBinding(FILE* f){fprintf(f,"{\"event\":\"observation_binding\",\"pid\":%lu,\"birth\":%llu,\"base\":%llu,\"run_id\":\"%s\"}\n",observationPid,observationBirth,observationBase,expectedName);fflush(f);}
static void armPoints(CONTEXT& c,uint64_t b,uint64_t,DWORD){c.Dr0=b+0x13DC09;c.Dr1=b+0x13DC0E;c.Dr2=b+0x50B598;c.Dr3=b+0x50B632;c.Dr6=0;c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x55;}
static DWORD parentThread=0;
static uint64_t parentRsp=0,parentApp=0,frames=0;
static bool inside=false;
static uint64_t pinnedStates[5]{},pinnedVtables[5]{};
static void stateRecord(FILE*f,HANDLE p,uint64_t b,unsigned index,const char* point,uint64_t workerOverride=0){
 const auto s=rd<uint64_t>(p,selectedStack+index*8),vt=rd<uint64_t>(p,s),worker=rd<uint64_t>(p,s+0x50),w=workerOverride?workerOverride:worker;
 if(!pinnedStates[index]){pinnedStates[index]=s;pinnedVtables[index]=vt;}need(s==pinnedStates[index]&&vt==pinnedVtables[index],"Formal state identity changed");
 uint64_t callable=0,threadObject=0;DWORD done=0,yield=0,thread=0;
 if(w){callable=rd<uint64_t>(p,w+0x50);done=rd<DWORD>(p,w+0x58);yield=rd<DWORD>(p,w+0x78);threadObject=rd<uint64_t>(p,w+8);if(threadObject)thread=rd<DWORD>(p,threadObject+0x10);}
 fprintf(f,"{\"seq\":%llu,\"event\":\"state\",\"frame\":%llu,\"point\":\"%s\",\"index\":%u,\"state\":%llu,\"vtable_rva\":%llu,\"state_worker\":%llu,\"sampled_worker\":%llu,\"callable\":%llu,\"done\":%lu,\"yield\":%lu,\"worker_thread\":%lu}\n",++sequence,frames,point,index,s,vt-b,worker,w,callable,done,yield,thread);
}
static bool observe(FILE*f,HANDLE p,uint64_t b,const CONTEXT&c,DWORD tid){
 need(++stageSamples<1024,"Parent observation event bound exceeded");const auto r=c.Rip-b,m=b+0x19E7310;
 // Attachment may start mid-frame. Such initial hits are censored, never paired.
 if(!parentThread&&r!=0x13DC09){++filteredHits;return false;}
 need(formalUser(p,b),"Selected idle FormalUser changed");
 if(!parentThread){parentThread=tid;parentRsp=c.Rsp;parentApp=c.Rdi;}
 need(tid==parentThread,"Parent thread changed");
 const char* point=nullptr;
 if(r==0x13DC09){need(!inside&&c.Rsp==parentRsp&&c.Rdi==parentApp&&c.Rcx==m,"Parent call identity or recursion mismatch");inside=true;++frames;point="before";}
 else if(r==0x13DC0E){need(inside&&c.Rsp==parentRsp&&c.Rdi==parentApp,"Unpaired parent return");point="after";}
 else {need(inside,"Task outside selected parent frame");const auto slot=rd<uint64_t>(p,c.Rsp+0x40);need(slot>=selectedStack&&slot<selectedStack+40&&!((slot-selectedStack)%8),"Task slot outside formal stack");const auto s=rd<uint64_t>(p,slot);need(rd<uint64_t>(p,m+0x48)==s,"Manager current state differs");
  need(r==0x50B598||r==0x50B632,"Unknown parent point");point=r==0x50B598?"created":"complete_or_yield";
  const auto worker=rd<uint64_t>(p,s+0x50);need(c.Rdi&&(r!=0x50B598||worker==c.Rdi),"Task worker mismatch");
  if(r==0x50B632&&worker)need(worker==c.Rdi&&rd<DWORD>(p,worker+0x78),"Remaining task is not matching yielded worker");
  stateRecord(f,p,b,unsigned((slot-selectedStack)/8),point,c.Rdi);
 }
 fprintf(f,"{\"seq\":%llu,\"event\":\"parent\",\"frame\":%llu,\"point\":\"%s\",\"rva\":%llu,\"tid\":%lu,\"rsp\":%llu,\"manager\":%llu,\"manager_current\":%llu,\"selected_user\":%llu}\n",++sequence,frames,point,r,tid,c.Rsp,m,rd<uint64_t>(p,m+0x48),selectedUser);
 if(r==0x13DC09||r==0x13DC0E)for(unsigned i=0;i<5;++i)stateRecord(f,p,b,i,point);
 if(r==0x13DC0E){inside=false;if(frames==16){chainComplete=true;stopReason="sixteen_parent_frames_observed";fflush(f);need(!ferror(f),"Parent log write failed");return true;}}
 fflush(f);need(!ferror(f),"Parent log write failed");return false;
}
