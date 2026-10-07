option casemap:none
extern CheckpointLoadWorkerBridge0:proc
extern TitleIdentityFixtureBody:proc
extern TitleIdentityFixtureRax:qword
extern TitleIdentityFixtureXmm:byte
.code
public TitleIdentityFixtureReturn
TitleIdentityFixtureInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CheckpointLoadWorkerBridge0
TitleIdentityFixtureReturn label near
    mov TitleIdentityFixtureRax,rax
    movdqu xmmword ptr [TitleIdentityFixtureXmm],xmm0
    add rsp,28h
    ret
TitleIdentityFixtureInvoke endp
TitleIdentityFixtureOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call TitleIdentityFixtureBody
    mov rax,0abcd987612345678h
    pcmpeqd xmm0,xmm0
    add rsp,28h
    ret
TitleIdentityFixtureOriginal endp
end
