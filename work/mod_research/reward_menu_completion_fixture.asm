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
END
