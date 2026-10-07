option casemap:none
extern PersistentAuthorizedFixtureBody:proc
.const
expectedXmm byte 070h,071h,072h,073h,074h,075h,076h,077h,078h,079h,07ah,07bh,07ch,07dh,07eh,07fh
.code
PersistentAuthorizedFixtureNative proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call PersistentAuthorizedFixtureBody
    movdqu xmm0,xmmword ptr [expectedXmm]
    add rsp,28h
    ret
PersistentAuthorizedFixtureNative endp
; rcx=entry, rdx=user, r8=mode, r9=output
PersistentAuthorizedFixtureCall proc frame
    push rbx
    .pushreg rbx
    sub rsp,20h
    .allocstack 20h
    .endprolog
    mov rbx,r9
    mov rax,rcx
    mov rcx,rdx
    mov rdx,r8
    xor r8,r8
    xor r9,r9
    call rax
    mov [rbx],rax
    movdqu xmmword ptr [rbx+10h],xmm0
    add rsp,20h
    pop rbx
    ret
PersistentAuthorizedFixtureCall endp
end
