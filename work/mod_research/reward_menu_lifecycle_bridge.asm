option casemap:none
.code
; Source investigation only: enter the proven nonzero-return continuation with
; exactly the Update frame. No receipt API, no arbitrary wrapper return value.
CompletionQueueTail PROC FRAME
    push rbx
    .pushreg rbx
    sub rsp,20h
    .allocstack 20h
    .endprolog
    jmp rcx
CompletionQueueTail ENDP

; Partial dispatcher harness. Actual code performs pending-copy/clear and type
; dispatch. The owned copied range redirects only its end to this epilogue.
CompletionConsume PROC FRAME
    push rbp
    .pushreg rbp
    push rbx
    .pushreg rbx
    push rsi
    .pushreg rsi
    push rdi
    .pushreg rdi
    push r12
    .pushreg r12
    push r13
    .pushreg r13
    push r14
    .pushreg r14
    push r15
    .pushreg r15
    sub rsp,178h
    .allocstack 178h
    lea rbp,[rsp+100h]
    .endprolog
    mov r15,rdx
    xor esi,esi
    mov qword ptr [rsp+30h],0
    mov qword ptr [rsp+38h],0
    jmp rcx
PUBLIC CompletionConsumeReturn
CompletionConsumeReturn LABEL BYTE
    lea rsp,[rbp+78h]
    pop r15
    pop r14
    pop r13
    pop r12
    pop rdi
    pop rsi
    pop rbx
    pop rbp
    ret
CompletionConsume ENDP

; OWNED TEST SPLICES ONLY. There is no production fault continuation here.
extern LifecycleCheck:proc
extern LifecycleFaultReturn:qword
extern LifecycleSuccessReturn:qword
GATE macro name:req,stage:req
name proc frame
 pushfq
 .allocstack 8
 push rax
 .pushreg rax
 push rcx
 .pushreg rcx
 push rdx
 .pushreg rdx
 push r8
 .pushreg r8
 push r9
 .pushreg r9
 push r10
 .pushreg r10
 push r11
 .pushreg r11
 sub rsp,0a8h
 .allocstack 0a8h
 .endprolog
 movdqu [rsp+30h],xmm0
 movdqu [rsp+40h],xmm1
 movdqu [rsp+50h],xmm2
 movdqu [rsp+60h],xmm3
 movdqu [rsp+70h],xmm4
 movdqu [rsp+80h],xmm5
 mov ecx,stage
 mov rdx,r15
 mov r8,r12
 mov r9,rdi
 mov [rsp+20h],r14
 call LifecycleCheck
 test eax,eax
 jnz good
 mov rax,LifecycleFaultReturn
 mov [rsp+0e8h],rax
 jmp finished
 good:
 if stage eq 3
 mov rax,LifecycleSuccessReturn
 mov [rsp+0e8h],rax
 endif
 finished:
 movdqu xmm0,[rsp+30h]
 movdqu xmm1,[rsp+40h]
 movdqu xmm2,[rsp+50h]
 movdqu xmm3,[rsp+60h]
 movdqu xmm4,[rsp+70h]
 movdqu xmm5,[rsp+80h]
 add rsp,0a8h
 pop r11
 pop r10
 pop r9
 pop r8
 pop rdx
 pop rcx
 pop rax
 popfq
 if stage eq 1
 mov [rsp+68h],r12
 elseif stage eq 2
 mov rcx,[r12+60h]
 endif
 ret
name endp
endm
GATE LifecycleSelect,1
GATE LifecycleFinalized,2
GATE LifecycleFreed,3
END
