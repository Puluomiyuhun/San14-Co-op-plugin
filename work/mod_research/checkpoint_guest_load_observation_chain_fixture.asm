; Own-process callers/native substitutes, all with real PE unwind metadata.
option casemap:none
extern CheckpointLoadWorkerBridge0:proc
extern CheckpointLoadWorkerBridge1:proc
extern GuestChainWorkerBody:proc
extern GuestChainReadBody:proc
extern GuestChainParent:qword
extern GuestChainReadRax:qword
extern GuestChainWorkerRax:qword
extern GuestChainReadXmm:byte
extern GuestChainWorkerXmm:byte
extern GuestChainPattern:byte
.code
public GuestChainWorkerReturn
public GuestChainReadReturn
GuestChainWorkerInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CheckpointLoadWorkerBridge0
GuestChainWorkerReturn label near
    mov GuestChainWorkerRax,rax
    movdqu xmmword ptr [GuestChainWorkerXmm],xmm0
    add rsp,28h
    ret
GuestChainWorkerInvoke endp
GuestChainReadInvoke proc frame
    sub rsp,68h
    .allocstack 68h
    .endprolog
    mov rax,GuestChainParent
    ; Bridge entry RSP is current RSP-8; entry+50h == current+48h.
    mov qword ptr [rsp+48h],rax
    call CheckpointLoadWorkerBridge1
GuestChainReadReturn label near
    mov GuestChainReadRax,rax
    movdqu xmmword ptr [GuestChainReadXmm],xmm0
    add rsp,68h
    ret
GuestChainReadInvoke endp
GuestChainWorkerOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call GuestChainWorkerBody
    mov rax,0aabbccdd87654321h
    movdqu xmm0,xmmword ptr [GuestChainPattern]
    add rsp,28h
    ret
GuestChainWorkerOriginal endp
GuestChainReadOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call GuestChainReadBody
    movdqu xmm0,xmmword ptr [GuestChainPattern+10h]
    add rsp,28h
    ret
GuestChainReadOriginal endp

option casemap:none
extern CheckpointPushBridge0:proc
extern GuestChainUpdateBody:proc
.code
public GuestChainUpdateReturn
GuestChainUpdateInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CheckpointPushBridge0
GuestChainUpdateReturn label near
    add rsp,28h
    ret
GuestChainUpdateInvoke endp
GuestChainUpdateOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call GuestChainUpdateBody
    mov rax,0fedcba9876543210h
    pcmpeqd xmm0,xmm0
    add rsp,28h
    ret
GuestChainUpdateOriginal endp
end
