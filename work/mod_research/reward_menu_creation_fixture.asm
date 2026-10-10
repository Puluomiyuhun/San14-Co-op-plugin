option casemap:none
EXTERN RewardMenuCreationActivation:PROC
EXTERN RewardMenuCreationActivated:PROC
.code
; Deliberately destructive but ABI-legal fixture callee. Tail call retains the
; actual observer and caller provenance; no receipt or permit is fabricated.
CreationShadowPressure PROC
 mov rax,0BADC0FFEE0DDF00Dh
 mov [rsp+8],rax
 mov [rsp+10h],rax
 mov [rsp+18h],rax
 mov [rsp+20h],rax
 pcmpeqd xmm0,xmm0
 pcmpeqd xmm1,xmm1
 pcmpeqd xmm2,xmm2
 pcmpeqd xmm3,xmm3
 pcmpeqd xmm4,xmm4
 pcmpeqd xmm5,xmm5
 jmp RewardMenuCreationActivated
CreationShadowPressure ENDP

; Third argument is exactly the arithmetic flags pattern to preserve.
CreationProbeActivation PROC FRAME
 push r13
 .pushreg r13
 push r15
 .pushreg r15
 sub rsp,48h
 .allocstack 48h
 .endprolog
 mov r15,rcx
 mov r13,rdx
 mov [rsp+20h],r8
 mov edx,11223344h
 mov r8d,22334455h
 mov r9d,33445566h
 mov r10d,44556677h
 mov r11d,55667788h
 mov rax,123456789ABCDEF0h
 movq xmm0,rax
 movq xmm1,rax
 movq xmm2,rax
 movq xmm3,rax
 movq xmm4,rax
 movq xmm5,rax
 push qword ptr [rsp+20h]
 popfq
 call RewardMenuCreationActivation
 pushfq
 pop qword ptr [rsp+28h]
 cmp rcx,[r15+10h]
 jne probeFail
 cmp rax,[r15+20h]
 jne probeFail
 cmp edx,11223344h
 jne probeFail
 cmp r8d,22334455h
 jne probeFail
 cmp r9d,33445566h
 jne probeFail
 cmp r10d,44556677h
 jne probeFail
 cmp r11d,55667788h
 jne probeFail
 mov rax,[rsp+28h]
 xor rax,[rsp+20h]
 test eax,8D5h
 jne probeFail
 mov rdx,123456789ABCDEF0h
 movq rax,xmm0
 cmp rax,rdx
 jne probeFail
 movq rax,xmm1
 cmp rax,rdx
 jne probeFail
 movq rax,xmm2
 cmp rax,rdx
 jne probeFail
 movq rax,xmm3
 cmp rax,rdx
 jne probeFail
 movq rax,xmm4
 cmp rax,rdx
 jne probeFail
 movq rax,xmm5
 cmp rax,rdx
 jne probeFail
 ; Each seed's upper 64 bits are zero; pressure writes every bit to one.
 psrldq xmm0,8
 psrldq xmm1,8
 psrldq xmm2,8
 psrldq xmm3,8
 psrldq xmm4,8
 psrldq xmm5,8
 por xmm0,xmm1
 por xmm0,xmm2
 por xmm0,xmm3
 por xmm0,xmm4
 por xmm0,xmm5
 movq rax,xmm0
 test rax,rax
 jne probeFail
 mov eax,1
 jmp probeDone
probeFail:
 xor eax,eax
probeDone:
 add rsp,48h
 pop r15
 pop r13
 ret
CreationProbeActivation ENDP

; Owned caller frame for the archived 3FA094 command-dispatch tail only.
; It does not execute the preceding native User update or its input paths.
CreationUserTail PROC FRAME
 push rsi
 .pushreg rsi
 sub rsp,40h
 .allocstack 40h
 .endprolog
 mov [rsp+50h],rbx
 mov [rsp+58h],rbp
 mov [rsp+38h],r14
 mov rsi,rdx
 mov r14d,r8d
 jmp rcx
CreationUserTail ENDP

CreationConsume PROC FRAME
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
PUBLIC CreationConsumeReturn
CreationConsumeReturn LABEL BYTE
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
CreationConsume ENDP
END
