; Win64 4-integer-register bridge. Normal PE .pdata/.xdata, no copied trampoline.
option casemap:none
extern CheckpointPersistentBridgeInvoke:proc
.code

BRIDGE_ENTRY macro name:req, slotid:req
name proc frame
    sub rsp,88h
    .allocstack 88h
    .endprolog
    ; 20h shadow space followed by an aligned 60h frame; +8 alignment padding.
    mov qword ptr [rsp+20h],rcx
    mov qword ptr [rsp+28h],rdx
    mov qword ptr [rsp+30h],r8
    mov qword ptr [rsp+38h],r9
    xor eax,eax
    mov qword ptr [rsp+40h],rax
    mov qword ptr [rsp+48h],rax
    pxor xmm0,xmm0
    movdqa xmmword ptr [rsp+50h],xmm0
    lea rax,[rsp+88h]
    mov qword ptr [rsp+60h],rax
    mov qword ptr [rsp+78h],0
    mov ecx,slotid
    lea rdx,[rsp+20h]
    call CheckpointPersistentBridgeInvoke
    mov rax,qword ptr [rsp+40h]
    movdqa xmm0,xmmword ptr [rsp+50h]
    add rsp,88h
    ret
name endp
endm

BRIDGE_ENTRY CheckpointPersistentBridge0, 0
BRIDGE_ENTRY CheckpointPersistentBridge1, 1
BRIDGE_ENTRY CheckpointPersistentBridge2, 2
BRIDGE_ENTRY CheckpointPersistentBridge3, 3
BRIDGE_ENTRY CheckpointPersistentBridge4, 4
BRIDGE_ENTRY CheckpointPersistentBridge5, 5

; rcx=immutable original pointer, rdx=frame. Exact one direct native call.
CheckpointPersistentBridgeCallOriginal proc frame
    push rbx
    .pushreg rbx
    sub rsp,20h
    .allocstack 20h
    .endprolog
    mov rbx,rdx
    mov rax,rcx
    mov rcx,qword ptr [rbx]
    mov rdx,qword ptr [rbx+8]
    mov r8,qword ptr [rbx+10h]
    mov r9,qword ptr [rbx+18h]
    call rax
    mov qword ptr [rbx+20h],rax
    movdqu xmmword ptr [rbx+30h],xmm0
    add rsp,20h
    pop rbx
    ret
CheckpointPersistentBridgeCallOriginal endp
end
