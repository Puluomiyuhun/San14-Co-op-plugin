; Win64 mid-function CALL bridge, not a function-entry detour.
; Callsite RSP must be 16-byte aligned before CALL. Replay only the audited
; seven-byte load. All other native instructions remain with their original owner.
option casemap:none
include checkpoint_native_input_prefetch_archived.inc
extern CheckpointPrefetchObserve:proc
public CheckpointPrefetchMidBody,CheckpointPrefetchReplayLoad
.code
CheckpointPrefetchMidBridge proc frame
    push rbp
    .pushreg rbp
    pushfq
    .allocstack 8
    sub rsp,1c8h
    .allocstack 1c8h
    mov rbp,rsp
    .setframe rbp,0
    mov [rsp+38h],rbx
    .savereg rbx,38h
    mov [rsp+50h],rsi
    .savereg rsi,50h
    mov [rsp+58h],rdi
    .savereg rdi,58h
    mov [rsp+80h],r12
    .savereg r12,80h
    mov [rsp+88h],r13
    .savereg r13,88h
    mov [rsp+90h],r14
    .savereg r14,90h
    mov [rsp+98h],r15
    .savereg r15,98h
    movdqa [rsp+110h],xmm6
    .savexmm128 xmm6,110h
    movdqa [rsp+120h],xmm7
    .savexmm128 xmm7,120h
    movdqa [rsp+130h],xmm8
    .savexmm128 xmm8,130h
    movdqa [rsp+140h],xmm9
    .savexmm128 xmm9,140h
    movdqa [rsp+150h],xmm10
    .savexmm128 xmm10,150h
    movdqa [rsp+160h],xmm11
    .savexmm128 xmm11,160h
    movdqa [rsp+170h],xmm12
    .savexmm128 xmm12,170h
    movdqa [rsp+180h],xmm13
    .savexmm128 xmm13,180h
    movdqa [rsp+190h],xmm14
    .savexmm128 xmm14,190h
    movdqa [rsp+1a0h],xmm15
    .savexmm128 xmm15,1a0h
    .endprolog
CheckpointPrefetchMidBody label byte
    mov [rsp+20h],rax
    mov [rsp+28h],rcx
    mov [rsp+30h],rdx
    mov [rsp+60h],r8
    mov [rsp+68h],r9
    mov [rsp+70h],r10
    mov [rsp+78h],r11
    movdqa [rsp+0b0h],xmm0
    movdqa [rsp+0c0h],xmm1
    movdqa [rsp+0d0h],xmm2
    movdqa [rsp+0e0h],xmm3
    movdqa [rsp+0f0h],xmm4
    movdqa [rsp+100h],xmm5
    stmxcsr [rsp+1b0h]
    mov dword ptr [rsp+1b4h],0
    mov qword ptr [rsp+1b8h],0
    lea rax,[rsp+1e0h]
    mov [rsp+40h],rax
    mov rax,[rsp+1d0h]
    mov [rsp+48h],rax
    mov rax,[rsp+1c8h]
    mov [rsp+0a0h],rax
    mov rax,[rsp+1d8h]
    mov [rsp+0a8h],rax
    ; The original DF is saved. C++ observer obeys the normal clear-DF ABI.
    cld
    lea rcx,[rsp+20h]
    call CheckpointPrefetchObserve
    mov rsi,[rsp+50h]
CheckpointPrefetchReplayLoad label byte
    PREFETCH_REPLAY_LOAD
    mov [rsp+20h],rax
    ; Faults in the original load occur while the complete unwind frame exists.
    ldmxcsr [rsp+1b0h]
    movdqa xmm0,[rsp+0b0h]
    movdqa xmm1,[rsp+0c0h]
    movdqa xmm2,[rsp+0d0h]
    movdqa xmm3,[rsp+0e0h]
    movdqa xmm4,[rsp+0f0h]
    movdqa xmm5,[rsp+100h]
    movdqa xmm6,[rsp+110h]
    movdqa xmm7,[rsp+120h]
    movdqa xmm8,[rsp+130h]
    movdqa xmm9,[rsp+140h]
    movdqa xmm10,[rsp+150h]
    movdqa xmm11,[rsp+160h]
    movdqa xmm12,[rsp+170h]
    movdqa xmm13,[rsp+180h]
    movdqa xmm14,[rsp+190h]
    movdqa xmm15,[rsp+1a0h]
    mov rax,[rsp+20h]
    mov rcx,[rsp+28h]
    mov rdx,[rsp+30h]
    mov rbx,[rsp+38h]
    mov rsi,[rsp+50h]
    mov rdi,[rsp+58h]
    mov r8,[rsp+60h]
    mov r9,[rsp+68h]
    mov r10,[rsp+70h]
    mov r11,[rsp+78h]
    mov r12,[rsp+80h]
    mov r13,[rsp+88h]
    mov r14,[rsp+90h]
    mov r15,[rsp+98h]
    ; RBP is a stable frame pointer: temporary push/pop is unwindable through it.
    push qword ptr [rbp+1c8h]
    popfq
    ; Recognizable Win64 epilog; LEA/POP/RET leave the restored flags intact.
    lea rsp,[rbp+1d0h]
    pop rbp
    ret
CheckpointPrefetchMidBridge endp
end
