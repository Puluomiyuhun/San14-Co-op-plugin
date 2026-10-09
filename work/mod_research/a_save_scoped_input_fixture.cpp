// Inserted after the frozen parent fixture's need() in a private generated TU.
// These writes model the SCHEDULER's changing current-state slot; production
// sources never rewrite it to satisfy input validation.
struct ScopedNativeCurrent {
 uintptr_t prior;
 explicit ScopedNativeCurrent(uintptr_t state):prior(get<uintptr_t>(b+0x19E7310+0x48)){put<uintptr_t>(b+0x19E7310+0x48,state);}
 ~ScopedNativeCurrent(){put<uintptr_t>(b+0x19E7310+0x48,prior);}
};
static DWORD scopedGame(){ScopedNativeCurrent current(b+0x202000);return gameDispatch();}
static DWORD scopedUser(){ScopedNativeCurrent current(user);return rewardDispatch();}
static DWORD scopedDispatch(unsigned slot,uintptr_t state){ScopedNativeCurrent current(state);return dispatch(slot,state);}
static unsigned nativeScopeRejects=0;
static void rejectCurrent(uintptr_t state,const char*why){
 ScopedNativeCurrent current(state);checkpoint_native_input_pending::Config c{};
 need(inputSample(nullptr,c),"actual input sampler");checkpoint_native_input_pending::Adapter a;
 need(a.Bind(c)==checkpoint_native_input_pending::Error::None,"actual inspector binds expected layout");
 need(a.InspectCurrent(c.binding).error==checkpoint_native_input_pending::Error::Pointer,why);++nativeScopeRejects;
}
