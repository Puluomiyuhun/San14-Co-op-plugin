; Win64 4-integer-register bridge. Normal PE .pdata/.xdata, no copied trampoline.
option casemap:none
extern ASaveActionBridgeInvoke:proc
extern ASaveActionTailSelect:proc
extern ASaveActionUserEpilogue:QWORD
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
    call ASaveActionBridgeInvoke
    mov rax,qword ptr [rsp+40h]
    movdqa xmm0,xmmword ptr [rsp+50h]
    add rsp,88h
    ret
name endp
endm

BRIDGE_ENTRY ASaveActionBridge0, 0
BRIDGE_ENTRY ASaveActionBridge1, 1
BRIDGE_ENTRY ASaveActionBridge2, 2

; rcx=immutable original pointer, rdx=frame. Exact one direct native call.
ASaveActionBridgeCallOriginal proc frame
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
ASaveActionBridgeCallOriginal endp

; Mid-User call replacement. Preserve flags, every volatile GPR/XMM, and RSI.
; The original instruction is cmp [rsi+660h],ebp. The held branch returns to the
; original function epilogue BEFORE report flush, selection and action side effects.
; Hardware shadow-stack processes are explicitly refused at Initialize.

public ASaveActionTailRestoreBegin
public ASaveActionTailFlagsPush
public ASaveActionTailFlagsPop
public ASaveActionTailEpilogue
public ASaveActionTailPopRbp
public ASaveActionTailRet
public ASaveActionTailOriginalLoad
public ASaveEarlyCompareFlagsPush
public ASaveEarlyCompareFlagsPop
ASaveActionUserTail proc frame
 push rbp
 .pushreg rbp
 pushfq
 .allocstack 8
 sub rsp,0e8h
 .allocstack 0e8h
 lea rbp,[rsp+80h]
 .setframe rbp,80h
 .endprolog
 mov qword ptr [rsp+20h],rax
 mov qword ptr [rsp+28h],rcx
 mov qword ptr [rsp+30h],rdx
 mov qword ptr [rsp+38h],r8
 mov qword ptr [rsp+40h],r9
 mov qword ptr [rsp+48h],r10
 mov qword ptr [rsp+50h],r11
 movdqu xmmword ptr [rsp+60h],xmm0
 movdqu xmmword ptr [rsp+70h],xmm1
 movdqu xmmword ptr [rsp+80h],xmm2
 movdqu xmmword ptr [rsp+90h],xmm3
 movdqu xmmword ptr [rsp+0a0h],xmm4
 movdqu xmmword ptr [rsp+0b0h],xmm5
 mov rcx,rsi
 mov rdx,qword ptr [rsp+0f8h]
 call ASaveActionTailSelect
 test al,al
 jz ASaveActionTailOriginalLoad
 mov rax,qword ptr [ASaveActionUserEpilogue]
 mov qword ptr [rsp+0f8h],rax
 jmp ASaveActionTailRestoreBegin
ASaveActionTailOriginalLoad::
 ; Faultable original compare executes while the PE frame is still active.
 ; Caller EBP was saved before establishing this bridge's fixed RBP.
 mov eax,dword ptr [rsp+0f0h]
 cmp dword ptr [rsi+660h],eax
 ; Capture CMP flags into the existing restore slot without clobbering them.
ASaveEarlyCompareFlagsPush::
 pushfq
ASaveEarlyCompareFlagsPop::
 pop qword ptr [rsp+0e8h]
ASaveActionTailRestoreBegin::
 movdqu xmm0,xmmword ptr [rsp+60h]
 movdqu xmm1,xmmword ptr [rsp+70h]
 movdqu xmm2,xmmword ptr [rsp+80h]
 movdqu xmm3,xmmword ptr [rsp+90h]
 movdqu xmm4,xmmword ptr [rsp+0a0h]
 movdqu xmm5,xmmword ptr [rsp+0b0h]
 mov rax,qword ptr [rsp+20h]
 mov rcx,qword ptr [rsp+28h]
 mov rdx,qword ptr [rsp+30h]
 mov r8,qword ptr [rsp+38h]
 mov r9,qword ptr [rsp+40h]
 mov r10,qword ptr [rsp+48h]
 mov r11,qword ptr [rsp+50h]
ASaveActionTailFlagsPush::
 ; RBP remains fixed across this temporary push: body unwind stays valid.
 push qword ptr [rsp+0e8h]
ASaveActionTailFlagsPop::
 popfq
ASaveActionTailEpilogue::
 ; Canonical Win64 frame-pointer epilogue; LEA/pop/ret preserve flags.
 lea rsp,[rbp+70h]
ASaveActionTailPopRbp::
 pop rbp
ASaveActionTailRet::
 ret
ASaveActionUserTail endp
end
