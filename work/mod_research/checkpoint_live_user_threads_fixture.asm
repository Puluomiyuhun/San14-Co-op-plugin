option casemap:none
extern CheckpointLiveFixtureBody:proc
.code
CheckpointLiveFixtureOriginal proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call CheckpointLiveFixtureBody
 mov rax,0fedcba9876543210h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 ret
CheckpointLiveFixtureOriginal endp
end
