option casemap:none
extern TaskPortsPayloadSnapshot:byte
extern NativeLoadPayloadBody:proc
extern CheckpointLoadWorkerBridge1:proc
.code
NativeLoadPayloadDouble proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    mov qword ptr [TaskPortsPayloadSnapshot+000h],rax
    mov qword ptr [TaskPortsPayloadSnapshot+008h],rcx
    mov qword ptr [TaskPortsPayloadSnapshot+010h],rdx
    mov qword ptr [TaskPortsPayloadSnapshot+018h],rbx
    mov qword ptr [TaskPortsPayloadSnapshot+020h],rsp
    mov qword ptr [TaskPortsPayloadSnapshot+028h],rbp
    mov qword ptr [TaskPortsPayloadSnapshot+030h],rsi
    mov qword ptr [TaskPortsPayloadSnapshot+038h],rdi
    mov qword ptr [TaskPortsPayloadSnapshot+040h],r8
    mov qword ptr [TaskPortsPayloadSnapshot+048h],r9
    mov qword ptr [TaskPortsPayloadSnapshot+050h],r10
    mov qword ptr [TaskPortsPayloadSnapshot+058h],r11
    mov qword ptr [TaskPortsPayloadSnapshot+060h],r12
    mov qword ptr [TaskPortsPayloadSnapshot+068h],r13
    mov qword ptr [TaskPortsPayloadSnapshot+070h],r14
    mov qword ptr [TaskPortsPayloadSnapshot+078h],r15
    pushfq
    pop qword ptr [TaskPortsPayloadSnapshot+080h]
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+090h],xmm0
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+0a0h],xmm1
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+0b0h],xmm2
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+0c0h],xmm3
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+0d0h],xmm4
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+0e0h],xmm5
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+0f0h],xmm6
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+100h],xmm7
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+110h],xmm8
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+120h],xmm9
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+130h],xmm10
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+140h],xmm11
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+150h],xmm12
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+160h],xmm13
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+170h],xmm14
    movdqu xmmword ptr [TaskPortsPayloadSnapshot+180h],xmm15
    stmxcsr dword ptr [TaskPortsPayloadSnapshot+190h]
    call NativeLoadPayloadBody
    add rsp,28h
    ret
NativeLoadPayloadDouble endp
CompletionTitleInvoke proc frame
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call CheckpointLoadWorkerBridge1
CompletionTitleReturn label byte
    add rsp,28h
    ret
CompletionTitleInvoke endp
public CompletionTitleReturn
end
