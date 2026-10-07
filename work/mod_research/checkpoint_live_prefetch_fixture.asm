option casemap:none
include checkpoint_native_input_prefetch_archived.inc
extern CheckpointLiveFixtureBody:proc
public CheckpointLivePrefetchFixtureSite
.code
CheckpointLiveFixtureOriginal proc frame
 push rsi
 .pushreg rsi
 push r14
 .pushreg r14
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rsi,rcx
 call CheckpointLiveFixtureBody
CheckpointLivePrefetchFixtureSite label byte
 PREFETCH_REPLAY_LOAD
 PREFETCH_REMAINING_CONSUMER
 mov rax,0fedcba9876543210h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 pop r14
 pop rsi
 ret
CheckpointLiveFixtureOriginal endp
end
