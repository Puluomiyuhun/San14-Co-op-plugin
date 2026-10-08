// Owned business services only. Native 509FE0 parses/copies the actual queue,
// invokes Load.Finalize via vt+10, pops Load and enters its worker phase.
static b_reload_queue_parent_source::Binding queueBinding{};
static unsigned queueRuns=0,queueZeroCurrentChecks=0,queueStatusCalls=0,queuePopCallbacks=0;
static bool queueRunning=false;
static uintptr_t queueNull(){return 0;}
static uintptr_t queueStatus(){b_reload_queue_parent_source::QueueOwner q{};check(b_reload_queue_parent_source::Owner::CurrentQueueOwner(q)&&q.binding.generation==queueBinding.generation&&q.binding.attempt==queueBinding.attempt&&q.binding.epoch==queueBinding.epoch,"native queue status inherits exact authorized parent generation");check(!at<uintptr_t>(base+0x19E7310+0x48),"native queue keeps manager current null");++queueStatusCalls;++queueZeroCurrentChecks;return 0;}
static void queueReserve(uintptr_t triple,std::uint64_t capacity){check(capacity&&capacity<=64,"owned queue allocator bounded request");auto memory=alloc(size_t(capacity*16));const auto old=at<uintptr_t>(triple),end=at<uintptr_t>(triple+8);if(old&&end>old)memcpy(reinterpret_cast<void*>(memory),reinterpret_cast<void*>(old),size_t(end-old));put<uintptr_t>(triple,memory);put<uintptr_t>(triple+8,memory+(end-old));put<uintptr_t>(triple+16,memory+uintptr_t(capacity*16));}
static void queueFreed(uintptr_t,uintptr_t){}
static void queueDestructor(uintptr_t){}
static void queueExit(uintptr_t state){check(state==load&&!at<uintptr_t>(base+0x19E7310+0x48),"native top-state Exit precedes Finalize at current zero");++queuePopCallbacks;}
static void queueWriteSlot(uintptr_t address,uintptr_t value){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(address),8,PAGE_READWRITE,&old),"owned queue service slot writable");put<uintptr_t>(address,value);check(VirtualProtect(reinterpret_cast<void*>(address),8,old,&old),"owned queue service slot protection restored");}
static void prepareQueueMachine(){
 if(!generationIndex)parentJump(0x50B7A0,uintptr_t(&queueReserve));
 parentJump(0x172D0,uintptr_t(&queueNull));parentJump(0x3A58B0,uintptr_t(&queueNull));
 put<uintptr_t>(base+0x201D3B0,alloc(0xA0100));put<uintptr_t>(base+0x201D3B8,0);put<uintptr_t>(base+0x201D418,0);put<uintptr_t>(base+0x201D420,0);put<DWORD>(base+0x201D370,0);
}
static void queueIdlePasses(unsigned count){auto m=base+0x19E7310;const auto n=at<std::uint64_t>(m+0x10),pendingCount=at<std::uint64_t>(m+0x30),oldCurrent=at<uintptr_t>(m+0x48);b_reload_queue_parent_source::Report before{},after{};parentSource.Snapshot(before);put<std::uint64_t>(m+0x10,0);put<std::uint64_t>(m+0x30,0);put<uintptr_t>(m+0x48,0);
 using Native=void(*)(uintptr_t,uintptr_t,uintptr_t,uintptr_t);for(unsigned i=0;i<count;++i)reinterpret_cast<Native>(base+0x13DC05)(m,0,0,0);
 put<std::uint64_t>(m+0x10,n);put<std::uint64_t>(m+0x30,pendingCount);put<uintptr_t>(m+0x48,oldCurrent);parentSource.Snapshot(after);check(after.scopes==before.scopes&&after.idleForwarded==before.idleForwarded+count&&after.error==b_reload_queue_parent_source::Error::None,"ordinary scheduler calls do not consume any authorized load scopes");
}
static DWORD WINAPI queueFinalizeOnParent(void*){
 ++queueRuns;queueRunning=true;const auto m=base+0x19E7310,stack=at<uintptr_t>(m+0x20);check(at<std::uint64_t>(m+0x10)==4&&at<uintptr_t>(stack+24)==load&&!at<uintptr_t>(m+0x48),"real preceding scheduler returned with current null before queue Finalize");
 uintptr_t state[4]{},oldVt[4]{},oldWorker[4]{},statusSlots[4]{},statusValues[4]{};
 for(unsigned i=0;i<4;++i){state[i]=at<uintptr_t>(stack+i*8);oldVt[i]=at<uintptr_t>(state[i]);auto vt=oldVt[i];if(!vt){vt=alloc(4096);put<uintptr_t>(state[i],vt);}statusSlots[i]=vt+0x30;statusValues[i]=at<uintptr_t>(statusSlots[i]);queueWriteSlot(statusSlots[i],uintptr_t(&queueStatus));oldWorker[i]=at<uintptr_t>(state[i]+0x50);if(i<3){auto worker=alloc(4096);put<uintptr_t>(worker+0x10,worker+0x100);put<DWORD>(worker+0x78,1);put<uintptr_t>(state[i]+0x50,worker);}}
 const auto loadVt=at<uintptr_t>(load),titleVt=at<uintptr_t>(title);queueWriteSlot(loadVt+0x20,uintptr_t(&queueExit));queueWriteSlot(loadVt,uintptr_t(&queueDestructor));queueWriteSlot(titleVt+0x18,uintptr_t(&queueNull));put<DWORD>(title+0x6C,1);
 const auto allocator=alloc(4096),allocatorVt=alloc(4096);put<uintptr_t>(allocator,allocatorVt);put<uintptr_t>(allocatorVt+0x58,uintptr_t(&queueFreed));put<uintptr_t>(m,allocator);put<uintptr_t>(m+0x28,allocator);
 const auto queueEntry=alloc(4096);put<DWORD>(queueEntry,1);put<uintptr_t>(queueEntry+8,0);put<uintptr_t>(m+0x40,queueEntry);put<std::uint64_t>(m+0x30,1);put<std::uint64_t>(m+0x38,1);
 bool caught=false;__try {using Native=void(*)(uintptr_t,uintptr_t,uintptr_t,uintptr_t);reinterpret_cast<Native>(base+0x13DC05)(m,0,0,0);}
 __except(GetExceptionCode()==0xE014CC94?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}
 if(!caught)check(at<std::uint64_t>(m+0x10)==3&&!at<std::uint64_t>(m+0x30)&&!at<uintptr_t>(m+0x40)&&!at<uintptr_t>(m+0x48)&&at<uintptr_t>(stack+16)==title,"native queue popped Load and completed parent worker phase");
 for(unsigned i=0;i<4;++i){queueWriteSlot(statusSlots[i],statusValues[i]);put<uintptr_t>(state[i],oldVt[i]);put<uintptr_t>(state[i]+0x50,oldWorker[i]);}queueRunning=false;
 return caught?1:0;
}
