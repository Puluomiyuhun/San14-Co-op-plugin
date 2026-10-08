option casemap:none
.code
; Run the owned archived method with actual Windows x64 call/return, check RBX/RSP.
InvokeOwnedUpdate PROC FRAME
    push rbp
    .pushreg rbp
    mov rbp,rsp
    .setframe rbp,0
    push rbx
    .pushreg rbx
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov rax,rcx
    mov rcx,rdx
    mov rbx,0123456789abcdef0h
    call rax
    lea rdx,[rbp-30h]
    cmp rsp,rdx
    sete al
    mov rdx,0123456789abcdef0h
    cmp rbx,rdx
    sete dl
    and al,dl
    movzx eax,al
    lea rsp,[rbp-8]
    pop rbx
    pop rbp
    ret
InvokeOwnedUpdate ENDP
END
