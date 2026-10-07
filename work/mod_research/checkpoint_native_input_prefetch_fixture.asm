; Owned PE test host with normal unwind metadata. No game code is patched.
option casemap:none
include checkpoint_native_input_prefetch_archived.inc
extern CheckpointPrefetchMidBridge:proc
extern PrefetchFixtureUser:qword
extern PrefetchFixtureBefore:byte,PrefetchFixtureAfter:byte,PrefetchFixtureSeed:byte
extern PrefetchFixtureFetched:dword
public PrefetchFixtureCallReturn,PrefetchFixtureBeforeCall,PrefetchFixtureAfterNative

SNAPSHOT macro output:req
    mov qword ptr [output+00h],rax
    mov qword ptr [output+08h],rcx
    mov qword ptr [output+10h],rdx
    mov qword ptr [output+18h],rbx
    mov qword ptr [output+20h],rsp
    mov qword ptr [output+28h],rbp
    mov qword ptr [output+30h],rsi
    mov qword ptr [output+38h],rdi
    mov qword ptr [output+40h],r8
    mov qword ptr [output+48h],r9
    mov qword ptr [output+50h],r10
    mov qword ptr [output+58h],r11
    mov qword ptr [output+60h],r12
    mov qword ptr [output+68h],r13
    mov qword ptr [output+70h],r14
    mov qword ptr [output+78h],r15
    pushfq
    pop qword ptr [output+80h]
    movdqu xmmword ptr [output+90h],xmm0
    movdqu xmmword ptr [output+0a0h],xmm1
    movdqu xmmword ptr [output+0b0h],xmm2
    movdqu xmmword ptr [output+0c0h],xmm3
    movdqu xmmword ptr [output+0d0h],xmm4
    movdqu xmmword ptr [output+0e0h],xmm5
    movdqu xmmword ptr [output+0f0h],xmm6
    movdqu xmmword ptr [output+100h],xmm7
    movdqu xmmword ptr [output+110h],xmm8
    movdqu xmmword ptr [output+120h],xmm9
    movdqu xmmword ptr [output+130h],xmm10
    movdqu xmmword ptr [output+140h],xmm11
    movdqu xmmword ptr [output+150h],xmm12
    movdqu xmmword ptr [output+160h],xmm13
    movdqu xmmword ptr [output+170h],xmm14
    movdqu xmmword ptr [output+180h],xmm15
    stmxcsr dword ptr [output+190h]
endm
.code
PrefetchFixtureSite proc frame
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
    sub rsp,0c8h
    .allocstack 0c8h
    movdqa [rsp+20h],xmm6
    .savexmm128 xmm6,20h
    movdqa [rsp+30h],xmm7
    .savexmm128 xmm7,30h
    movdqa [rsp+40h],xmm8
    .savexmm128 xmm8,40h
    movdqa [rsp+50h],xmm9
    .savexmm128 xmm9,50h
    movdqa [rsp+60h],xmm10
    .savexmm128 xmm10,60h
    movdqa [rsp+70h],xmm11
    .savexmm128 xmm11,70h
    movdqa [rsp+80h],xmm12
    .savexmm128 xmm12,80h
    movdqa [rsp+90h],xmm13
    .savexmm128 xmm13,90h
    movdqa [rsp+0a0h],xmm14
    .savexmm128 xmm14,0a0h
    movdqa [rsp+0b0h],xmm15
    .savexmm128 xmm15,0b0h
    .endprolog
    stmxcsr [rsp+0c0h]
    mov rax,01111111111111111h
    mov rcx,02222222222222222h
    mov rdx,03333333333333333h
    mov rbx,04444444444444444h
    mov rbp,05555555555555555h
    mov rsi,PrefetchFixtureUser
    mov rdi,07777777777777777h
    mov r8,08888888888888888h
    mov r9,09999999999999999h
    mov r10,0aaaaaaaaaaaaaaaah
    mov r11,0bbbbbbbbbbbbbbbbh
    mov r12,0cccccccccccccccch
    mov r13,0ddddddddddddddddh
    mov r14,0eeeeeeeeeeeeeeeeh
    mov r15,0ffffffffffffffffh
    movdqu xmm0,xmmword ptr [PrefetchFixtureSeed+00h]
    movdqu xmm1,xmmword ptr [PrefetchFixtureSeed+10h]
    movdqu xmm2,xmmword ptr [PrefetchFixtureSeed+20h]
    movdqu xmm3,xmmword ptr [PrefetchFixtureSeed+30h]
    movdqu xmm4,xmmword ptr [PrefetchFixtureSeed+40h]
    movdqu xmm5,xmmword ptr [PrefetchFixtureSeed+50h]
    movdqu xmm6,xmmword ptr [PrefetchFixtureSeed+60h]
    movdqu xmm7,xmmword ptr [PrefetchFixtureSeed+70h]
    movdqu xmm8,xmmword ptr [PrefetchFixtureSeed+80h]
    movdqu xmm9,xmmword ptr [PrefetchFixtureSeed+90h]
    movdqu xmm10,xmmword ptr [PrefetchFixtureSeed+0a0h]
    movdqu xmm11,xmmword ptr [PrefetchFixtureSeed+0b0h]
    movdqu xmm12,xmmword ptr [PrefetchFixtureSeed+0c0h]
    movdqu xmm13,xmmword ptr [PrefetchFixtureSeed+0d0h]
    movdqu xmm14,xmmword ptr [PrefetchFixtureSeed+0e0h]
    movdqu xmm15,xmmword ptr [PrefetchFixtureSeed+0f0h]
    cmp eax,011111111h
    stc
    std
    SNAPSHOT PrefetchFixtureBefore
PrefetchFixtureBeforeCall label byte
    call CheckpointPrefetchMidBridge
PrefetchFixtureCallReturn label byte
    nop
    nop
    ; Snapshot is fixture instrumentation only, before native instructions alter flags/R14.
    SNAPSHOT PrefetchFixtureAfter
    PREFETCH_REMAINING_CONSUMER
PrefetchFixtureAfterNative label byte
    mov PrefetchFixtureFetched,r14d
    cld
    ldmxcsr [rsp+0c0h]
    movdqa xmm6,[rsp+20h]
    movdqa xmm7,[rsp+30h]
    movdqa xmm8,[rsp+40h]
    movdqa xmm9,[rsp+50h]
    movdqa xmm10,[rsp+60h]
    movdqa xmm11,[rsp+70h]
    movdqa xmm12,[rsp+80h]
    movdqa xmm13,[rsp+90h]
    movdqa xmm14,[rsp+0a0h]
    movdqa xmm15,[rsp+0b0h]
    add rsp,0c8h
    pop r15
    pop r14
    pop r13
    pop r12
    pop rdi
    pop rsi
    pop rbp
    pop rbx
    ret
PrefetchFixtureSite endp

; A legal observer callee which clobbers volatile integer/XMM/flags state.
PrefetchFixtureClobber proc
    mov rax,01234h
    mov rcx,05678h
    mov rdx,09abch
    mov r8,0101h
    mov r9,0202h
    mov r10,0303h
    mov r11,0404h
    pxor xmm0,xmm0
    pxor xmm1,xmm1
    pxor xmm2,xmm2
    pxor xmm3,xmm3
    pxor xmm4,xmm4
    pxor xmm5,xmm5
    xor eax,eax
    clc
    ret
PrefetchFixtureClobber endp
end

