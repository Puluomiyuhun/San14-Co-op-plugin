; Own-process callers/native substitutes, all with real PE unwind metadata.
option casemap:none
extern CheckpointLoadWorkerBridge0:proc
extern CheckpointLoadWorkerBridge1:proc
extern CcLoadFixtureWorkerBody:proc
extern CcLoadFixtureReadBody:proc
extern CcLoadFixtureParent:qword
extern CcLoadFixtureReadRax:qword
extern CcLoadFixtureWorkerRax:qword
extern CcLoadFixtureReadXmm:byte
extern CcLoadFixtureWorkerXmm:byte
extern CcLoadFixturePattern:byte
.code
public CcLoadFixtureWorkerReturn
public CcLoadFixtureReadReturn
CcLoadFixtureWorkerInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CheckpointLoadWorkerBridge0
CcLoadFixtureWorkerReturn label near
    mov CcLoadFixtureWorkerRax,rax
    movdqu xmmword ptr [CcLoadFixtureWorkerXmm],xmm0
    add rsp,28h
    ret
CcLoadFixtureWorkerInvoke endp
CcLoadFixtureReadInvoke proc frame
    sub rsp,68h
    .allocstack 68h
    .endprolog
    mov rax,CcLoadFixtureParent
    ; Bridge entry RSP is current RSP-8; entry+50h == current+48h.
    mov qword ptr [rsp+48h],rax
    call CheckpointLoadWorkerBridge1
CcLoadFixtureReadReturn label near
    mov CcLoadFixtureReadRax,rax
    movdqu xmmword ptr [CcLoadFixtureReadXmm],xmm0
    add rsp,68h
    ret
CcLoadFixtureReadInvoke endp
CcLoadFixtureWorkerOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CcLoadFixtureWorkerBody
    mov rax,0aabbccdd87654321h
    movdqu xmm0,xmmword ptr [CcLoadFixturePattern]
    add rsp,28h
    ret
CcLoadFixtureWorkerOriginal endp
CcLoadFixtureReadOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CcLoadFixtureReadBody
    movdqu xmm0,xmmword ptr [CcLoadFixturePattern+10h]
    add rsp,28h
    ret
CcLoadFixtureReadOriginal endp
end
