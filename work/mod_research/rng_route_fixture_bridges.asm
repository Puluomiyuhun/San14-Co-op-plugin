; Dedicated-process ABI harness. These are NOT patches for the game.
option casemap:none
.code
CallTextBridge proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov rax,rcx
    mov rcx,rdx
    call rax
    add rsp,28h
    ret
CallTextBridge endp
; Leaf tail jump preserves the caller's return address and stack alignment.
TailRandomBridge proc
    mov rax,rcx
    mov ecx,edx
    jmp rax
TailRandomBridge endp
; Verify representative nonvolatile GPRs across a normal text callback.
CheckNonvolatileBridge proc frame
    push rbx
    .pushreg rbx
    push rsi
    .pushreg rsi
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov rax,rcx
    mov rcx,rdx
    mov rbx,1122334455667788h
    mov rsi,7766554433221100h
    call rax
    mov rdx,1122334455667788h
    cmp rbx,rdx
    jne bad
    mov rdx,7766554433221100h
    cmp rsi,rdx
    jne bad
    mov eax,1
    jmp done
bad:
    xor eax,eax
done:
    add rsp,28h
    pop rsi
    pop rbx
    ret
CheckNonvolatileBridge endp
end
