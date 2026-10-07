option casemap:none
extern CheckpointPushBridge0:proc
extern CcLifecycleFixtureBody:proc
.code
public CcLifecycleFixtureReturn
CcLifecycleFixtureInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CheckpointPushBridge0
CcLifecycleFixtureReturn label near
    add rsp,28h
    ret
CcLifecycleFixtureInvoke endp
CcLifecycleFixtureOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CcLifecycleFixtureBody
    mov rax,0fedcba9876543210h
    pcmpeqd xmm0,xmm0
    add rsp,28h
    ret
CcLifecycleFixtureOriginal endp
end
