; Own-process ABI probes only. No patching or game references.
option casemap:none
extern CheckpointPushFixtureBeforeRecord:proc
extern CheckpointPushFixtureAfterRecord:proc
extern CheckpointPushFixtureMaybeThrow:proc
extern CheckpointPushFixtureArgs:qword
extern CheckpointPushFixtureModulo:qword
extern CheckpointPushFixtureNativeCalls:qword
extern CheckpointPushFixtureNvPattern:byte
extern CheckpointPushFixtureReturnPattern:byte
.code

CLOBBER macro
    mov rax,01122334455667788h
    mov rcx,02233445566778899h
    mov rdx,033445566778899aah
    mov r8,0445566778899aabbh
    mov r9,05566778899aabbcch
    mov r10,066778899aabbccddh
    mov r11,0778899aabbccddefh
    pcmpeqd xmm0,xmm0
    pcmpeqd xmm1,xmm1
    pcmpeqd xmm2,xmm2
    pcmpeqd xmm3,xmm3
    pcmpeqd xmm4,xmm4
    pcmpeqd xmm5,xmm5
endm

OBSERVER macro name:req, recorder:req
name proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call recorder
    CLOBBER
    add rsp,28h
    ret
name endp
endm
OBSERVER CheckpointPushFixtureBefore, CheckpointPushFixtureBeforeRecord
OBSERVER CheckpointPushFixtureAfter, CheckpointPushFixtureAfterRecord

ORIGINAL macro name:req, slotid:req
name proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov qword ptr [CheckpointPushFixtureArgs+slotid*32],rcx
    mov qword ptr [CheckpointPushFixtureArgs+slotid*32+8],rdx
    mov qword ptr [CheckpointPushFixtureArgs+slotid*32+16],r8
    mov qword ptr [CheckpointPushFixtureArgs+slotid*32+24],r9
    lea rax,[rsp+28h]
    and eax,15
    mov qword ptr [CheckpointPushFixtureModulo+slotid*8],rax
    lock inc qword ptr [CheckpointPushFixtureNativeCalls+slotid*8]
    ; Deliberately use every byte of our caller-provided 32-byte home area.
    mov rax,0123456789abcdef0h
    mov qword ptr [rsp+30h],rax
    mov qword ptr [rsp+38h],rax
    mov qword ptr [rsp+40h],rax
    mov qword ptr [rsp+48h],rax
    mov ecx,slotid
    call CheckpointPushFixtureMaybeThrow
    mov rax,0fedcba9876543210h
    add rax,slotid
    movdqu xmm0,xmmword ptr [CheckpointPushFixtureReturnPattern+slotid*16]
    add rsp,28h
    ret
name endp
endm
ORIGINAL CheckpointPushFixtureOriginal0, 0
ORIGINAL CheckpointPushFixtureOriginal1, 1
ORIGINAL CheckpointPushFixtureOriginal2, 2
ORIGINAL CheckpointPushFixtureOriginal3, 3

; rcx=entry, rdx=capture. Set/check all Win64 nonvolatile GPRs/XMMs.
CheckpointPushFixtureRun proc frame
    push rbx
    .pushreg rbx
    push rbp
    .pushreg rbp
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
    sub rsp,0d8h
    .allocstack 0d8h
    movdqa xmmword ptr [rsp+30h],xmm6
    .savexmm128 xmm6,30h
    movdqa xmmword ptr [rsp+40h],xmm7
    .savexmm128 xmm7,40h
    movdqa xmmword ptr [rsp+50h],xmm8
    .savexmm128 xmm8,50h
    movdqa xmmword ptr [rsp+60h],xmm9
    .savexmm128 xmm9,60h
    movdqa xmmword ptr [rsp+70h],xmm10
    .savexmm128 xmm10,70h
    movdqa xmmword ptr [rsp+80h],xmm11
    .savexmm128 xmm11,80h
    movdqa xmmword ptr [rsp+90h],xmm12
    .savexmm128 xmm12,90h
    movdqa xmmword ptr [rsp+0a0h],xmm13
    .savexmm128 xmm13,0a0h
    movdqa xmmword ptr [rsp+0b0h],xmm14
    .savexmm128 xmm14,0b0h
    movdqa xmmword ptr [rsp+0c0h],xmm15
    .savexmm128 xmm15,0c0h
    .endprolog
    mov qword ptr [rsp+20h],rcx
    mov qword ptr [rsp+28h],rdx
    mov qword ptr [rdx+20h],rsp
    mov rbx,01111111122222222h
    mov rbp,02222222233333333h
    mov rsi,03333333344444444h
    mov rdi,04444444455555555h
    mov r12,05555555566666666h
    mov r13,06666666677777777h
    mov r14,07777777788888888h
    mov r15,08888888899999999h
    movdqu xmm6,xmmword ptr [CheckpointPushFixtureNvPattern]
    movdqu xmm7,xmmword ptr [CheckpointPushFixtureNvPattern+10h]
    movdqu xmm8,xmmword ptr [CheckpointPushFixtureNvPattern+20h]
    movdqu xmm9,xmmword ptr [CheckpointPushFixtureNvPattern+30h]
    movdqu xmm10,xmmword ptr [CheckpointPushFixtureNvPattern+40h]
    movdqu xmm11,xmmword ptr [CheckpointPushFixtureNvPattern+50h]
    movdqu xmm12,xmmword ptr [CheckpointPushFixtureNvPattern+60h]
    movdqu xmm13,xmmword ptr [CheckpointPushFixtureNvPattern+70h]
    movdqu xmm14,xmmword ptr [CheckpointPushFixtureNvPattern+80h]
    movdqu xmm15,xmmword ptr [CheckpointPushFixtureNvPattern+90h]
    mov rcx,01020304050607080h
    mov rdx,090a0b0c0d0e0f001h
    mov r8,0f123456789abcdefh
    mov r9,0fedcba9876543210h
    call qword ptr [rsp+20h]
    mov r10,qword ptr [rsp+28h]
    mov qword ptr [r10],rax
    movdqu xmmword ptr [r10+10h],xmm0
    mov qword ptr [r10+28h],rsp
    mov qword ptr [r10+30h],rbx
    mov qword ptr [r10+38h],rbp
    mov qword ptr [r10+40h],rsi
    mov qword ptr [r10+48h],rdi
    mov qword ptr [r10+50h],r12
    mov qword ptr [r10+58h],r13
    mov qword ptr [r10+60h],r14
    mov qword ptr [r10+68h],r15
    movdqu xmmword ptr [r10+70h],xmm6
    movdqu xmmword ptr [r10+80h],xmm7
    movdqu xmmword ptr [r10+90h],xmm8
    movdqu xmmword ptr [r10+0a0h],xmm9
    movdqu xmmword ptr [r10+0b0h],xmm10
    movdqu xmmword ptr [r10+0c0h],xmm11
    movdqu xmmword ptr [r10+0d0h],xmm12
    movdqu xmmword ptr [r10+0e0h],xmm13
    movdqu xmmword ptr [r10+0f0h],xmm14
    movdqu xmmword ptr [r10+100h],xmm15
    movdqa xmm6,xmmword ptr [rsp+30h]
    movdqa xmm7,xmmword ptr [rsp+40h]
    movdqa xmm8,xmmword ptr [rsp+50h]
    movdqa xmm9,xmmword ptr [rsp+60h]
    movdqa xmm10,xmmword ptr [rsp+70h]
    movdqa xmm11,xmmword ptr [rsp+80h]
    movdqa xmm12,xmmword ptr [rsp+90h]
    movdqa xmm13,xmmword ptr [rsp+0a0h]
    movdqa xmm14,xmmword ptr [rsp+0b0h]
    movdqa xmm15,xmmword ptr [rsp+0c0h]
    add rsp,0d8h
    pop r15
    pop r14
    pop r13
    pop r12
    pop rdi
    pop rsi
    pop rbp
    pop rbx
    ret
CheckpointPushFixtureRun endp
end
