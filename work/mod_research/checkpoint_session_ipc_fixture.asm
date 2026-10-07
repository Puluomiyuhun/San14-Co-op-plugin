; Own-process callers/native substitutes, all with real PE unwind metadata.
option casemap:none
extern IpcFixtureSlots:qword

extern IpcFixtureWorkerBody:proc
extern IpcFixtureReadBody:proc
extern IpcFixtureParent:qword
extern IpcFixtureReadRax:qword
extern IpcFixtureWorkerRax:qword
extern IpcFixtureReadXmm:byte
extern IpcFixtureWorkerXmm:byte
extern IpcFixturePattern:byte
.code
public IpcFixtureWorkerReturn
public IpcFixtureReadReturn
IpcFixtureWorkerInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov rax,IpcFixtureSlots
    call qword ptr [rax+20h]
IpcFixtureWorkerReturn label near
    mov IpcFixtureWorkerRax,rax
    movdqu xmmword ptr [IpcFixtureWorkerXmm],xmm0
    add rsp,28h
    ret
IpcFixtureWorkerInvoke endp
IpcFixtureReadInvoke proc frame
    sub rsp,68h
    .allocstack 68h
    .endprolog
    mov rax,IpcFixtureParent
    ; Bridge entry RSP is current RSP-8; entry+50h == current+48h.
    mov qword ptr [rsp+48h],rax
    mov rax,IpcFixtureSlots
    call qword ptr [rax+28h]
IpcFixtureReadReturn label near
    mov IpcFixtureReadRax,rax
    movdqu xmmword ptr [IpcFixtureReadXmm],xmm0
    add rsp,68h
    ret
IpcFixtureReadInvoke endp
IpcFixtureWorkerOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call IpcFixtureWorkerBody
    mov rax,0aabbccdd87654321h
    movdqu xmm0,xmmword ptr [IpcFixturePattern]
    add rsp,28h
    ret
IpcFixtureWorkerOriginal endp
IpcFixtureReadOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call IpcFixtureReadBody
    movdqu xmm0,xmmword ptr [IpcFixturePattern+10h]
    add rsp,28h
    ret
IpcFixtureReadOriginal endp

option casemap:none

extern IpcFixtureUpdateBody:proc
.code
public IpcFixtureUpdateReturn
IpcFixtureUpdateInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov rax,IpcFixtureSlots
    call qword ptr [rax+18h]
IpcFixtureUpdateReturn label near
    add rsp,28h
    ret
IpcFixtureUpdateInvoke endp
IpcFixtureUpdateOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call IpcFixtureUpdateBody
    mov rax,0fedcba9876543210h
    pcmpeqd xmm0,xmm0
    add rsp,28h
    ret
IpcFixtureUpdateOriginal endp

extern IpcFixtureUserBody:proc
public IpcFixtureUserReturn
IpcFixtureUserInvoke proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rax,IpcFixtureSlots
 call qword ptr [rax+0h]
IpcFixtureUserReturn label near
 add rsp,28h
 ret
IpcFixtureUserInvoke endp
IpcFixtureUserOriginal proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call IpcFixtureUserBody
 mov rax,0fedcba9876543210h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 ret
IpcFixtureUserOriginal endp

extern IpcFixtureMenuBody:proc
public IpcFixtureMenuReturn
IpcFixtureMenuInvoke proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rax,IpcFixtureSlots
 call qword ptr [rax+8h]
IpcFixtureMenuReturn label near
 add rsp,28h
 ret
IpcFixtureMenuInvoke endp
IpcFixtureMenuOriginal proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call IpcFixtureMenuBody
 mov rax,0fedcba9876543210h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 ret
IpcFixtureMenuOriginal endp

extern IpcFixtureGameBody:proc
public IpcFixtureGameReturn
IpcFixtureGameInvoke proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rax,IpcFixtureSlots
 call qword ptr [rax+10h]
IpcFixtureGameReturn label near
 add rsp,28h
 ret
IpcFixtureGameInvoke endp
IpcFixtureGameOriginal proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call IpcFixtureGameBody
 mov rax,0fedcba9876543210h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 ret
IpcFixtureGameOriginal endp
end
