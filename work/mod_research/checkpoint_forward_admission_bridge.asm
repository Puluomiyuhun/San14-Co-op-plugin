; Ordinary function-entry wrapper ONLY. The separately frozen prefetch bridge
; handles the mid-function ABI. PE metadata supports original exception unwind.
option casemap:none
extern CheckpointForwardAdmissionRun:proc
.code
CheckpointForwardAdmissionOriginal proc frame
    sub rsp,68h
    .allocstack 68h
    .endprolog
    mov [rsp+20h],rcx
    mov [rsp+28h],rdx
    mov [rsp+30h],r8
    mov [rsp+38h],r9
    lea rcx,[rsp+20h]
    call CheckpointForwardAdmissionRun
    mov rax,[rsp+40h]
    movdqu xmm0,xmmword ptr [rsp+50h]
    add rsp,68h
    ret
CheckpointForwardAdmissionOriginal endp
CheckpointForwardAdmissionCallOriginal proc frame
    push rbx
    .pushreg rbx
    sub rsp,20h
    .allocstack 20h
    .endprolog
    mov rbx,rcx
    mov rcx,[rbx]
    mov rdx,[rbx+8]
    mov r8,[rbx+10h]
    mov r9,[rbx+18h]
    call qword ptr [rbx+28h]
    mov [rbx+20h],rax
    movdqu xmmword ptr [rbx+30h],xmm0
    add rsp,20h
    pop rbx
    ret
CheckpointForwardAdmissionCallOriginal endp
end
