; Own-process callers/native substitutes, all with real PE unwind metadata.
option casemap:none
extern GuestSessionSlots:qword

extern GuestSessionWorkerBody:proc
extern GuestSessionReadBody:proc
extern GuestSessionParent:qword
extern GuestSessionReadRax:qword
extern GuestSessionWorkerRax:qword
extern GuestSessionReadXmm:byte
extern GuestSessionWorkerXmm:byte
extern GuestSessionPattern:byte
.code
public GuestSessionWorkerReturn
public GuestSessionReadReturn
GuestSessionWorkerInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov rax,GuestSessionSlots
    call qword ptr [rax+20h]
GuestSessionWorkerReturn label near
    mov GuestSessionWorkerRax,rax
    movdqu xmmword ptr [GuestSessionWorkerXmm],xmm0
    add rsp,28h
    ret
GuestSessionWorkerInvoke endp
GuestSessionReadInvoke proc frame
    sub rsp,68h
    .allocstack 68h
    .endprolog
    mov rax,GuestSessionParent
    ; Bridge entry RSP is current RSP-8; entry+50h == current+48h.
    mov qword ptr [rsp+48h],rax
    mov rax,GuestSessionSlots
    call qword ptr [rax+28h]
GuestSessionReadReturn label near
    mov GuestSessionReadRax,rax
    movdqu xmmword ptr [GuestSessionReadXmm],xmm0
    add rsp,68h
    ret
GuestSessionReadInvoke endp
GuestSessionWorkerOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call GuestSessionWorkerBody
    mov rax,0aabbccdd87654321h
    movdqu xmm0,xmmword ptr [GuestSessionPattern]
    add rsp,28h
    ret
GuestSessionWorkerOriginal endp
GuestSessionReadOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call GuestSessionReadBody
    movdqu xmm0,xmmword ptr [GuestSessionPattern+10h]
    add rsp,28h
    ret
GuestSessionReadOriginal endp

option casemap:none

extern GuestSessionUpdateBody:proc
.code
public GuestSessionUpdateReturn
GuestSessionUpdateInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov rax,GuestSessionSlots
    call qword ptr [rax+18h]
GuestSessionUpdateReturn label near
    add rsp,28h
    ret
GuestSessionUpdateInvoke endp
GuestSessionUpdateOriginal proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call GuestSessionUpdateBody
    mov rax,0fedcba9876543210h
    pcmpeqd xmm0,xmm0
    add rsp,28h
    ret
GuestSessionUpdateOriginal endp

extern GuestSessionUserBody:proc
public GuestSessionUserReturn
GuestSessionUserInvoke proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rax,GuestSessionSlots
 call qword ptr [rax+0h]
GuestSessionUserReturn label near
 add rsp,28h
 ret
GuestSessionUserInvoke endp
GuestSessionUserOriginal proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call GuestSessionUserBody
 mov rax,0fedcba9876543210h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 ret
GuestSessionUserOriginal endp

extern GuestSessionMenuBody:proc
public GuestSessionMenuReturn
GuestSessionMenuInvoke proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rax,GuestSessionSlots
 call qword ptr [rax+8h]
GuestSessionMenuReturn label near
 add rsp,28h
 ret
GuestSessionMenuInvoke endp
GuestSessionMenuOriginal proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call GuestSessionMenuBody
 mov rax,0fedcba9876543210h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 ret
GuestSessionMenuOriginal endp

extern GuestSessionGameBody:proc
public GuestSessionGameReturn
GuestSessionGameInvoke proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rax,GuestSessionSlots
 call qword ptr [rax+10h]
GuestSessionGameReturn label near
 add rsp,28h
 ret
GuestSessionGameInvoke endp
GuestSessionGameOriginal proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call GuestSessionGameBody
 mov rax,0fedcba9876543210h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 ret
GuestSessionGameOriginal endp
end
