option casemap:none
.code
; OWNED TEST SPLICES ONLY. There is no production fault continuation here.
extern DispatchCheck:proc
extern DispatchFaultReturn:qword
extern DispatchSuccessReturn:qword
extern DispatchCookieReturn:qword
extern DispatchGetter:qword
GATE macro name:req,stage:req
name proc frame
 pushfq
 .allocstack 8
 push rax
 .pushreg rax
 push rcx
 .pushreg rcx
 push rdx
 .pushreg rdx
 push r8
 .pushreg r8
 push r9
 .pushreg r9
 push r10
 .pushreg r10
 push r11
 .pushreg r11
 sub rsp,0a8h
 .allocstack 0a8h
 .endprolog
 movdqu [rsp+30h],xmm0
 movdqu [rsp+40h],xmm1
 movdqu [rsp+50h],xmm2
 movdqu [rsp+60h],xmm3
 movdqu [rsp+70h],xmm4
 movdqu [rsp+80h],xmm5
 mov ecx,stage
 mov rdx,r15
 mov r8,r12
 mov r9,rdi
 mov [rsp+20h],r14
 lea rax,[rsp+0f0h]
 mov [rsp+28h],rax
 call DispatchCheck
 test eax,eax
 jnz good
 if stage eq 4
 mov rax,DispatchCookieReturn
 else
 mov rax,DispatchFaultReturn
 endif
 mov [rsp+0e8h],rax
 jmp finished
 good:
 if stage eq 3
 mov rax,DispatchSuccessReturn
 mov [rsp+0e8h],rax
 endif
 finished:
 movdqu xmm0,[rsp+30h]
 movdqu xmm1,[rsp+40h]
 movdqu xmm2,[rsp+50h]
 movdqu xmm3,[rsp+60h]
 movdqu xmm4,[rsp+70h]
 movdqu xmm5,[rsp+80h]
 add rsp,0a8h
 pop r11
 pop r10
 pop r9
 pop r8
 pop rdx
 pop rcx
 pop rax
 popfq
 if stage eq 1
 mov [rsp+68h],r12
 elseif stage eq 2
 mov rcx,[r12+60h]
 endif
 if stage eq 4
 mov rax,DispatchCookieReturn
 cmp [rsp],rax
 je boundary_reject
 jmp qword ptr [DispatchGetter]
 boundary_reject:
 endif
 ret
name endp
endm
GATE DispatchSelect,1
GATE DispatchFinalized,2
GATE DispatchFreed,3
GATE DispatchBoundary,4

extern DispatchExpectedRsp:qword
public DispatchInvokeReturn
DispatchInvoke proc frame
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
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov DispatchExpectedRsp,rsp
 mov rax,rcx
 mov rcx,rdx
 xor edx,edx
 xor r8d,r8d
 xor r9d,r9d
 mov ebp,1101h
 mov ebx,1102h
 mov esi,1103h
 mov edi,1104h
 mov r12d,1105h
 mov r13d,1106h
 mov r14d,1107h
 mov r15d,1108h
 call rax
DispatchInvokeReturn::
 cmp rsp,DispatchExpectedRsp
 jne bad
 cmp rbp,1101h
 jne bad
 cmp rbx,1102h
 jne bad
 cmp rsi,1103h
 jne bad
 cmp rdi,1104h
 jne bad
 cmp r12,1105h
 jne bad
 cmp r13,1106h
 jne bad
 cmp r14,1107h
 jne bad
 cmp r15,1108h
 jne bad
 mov eax,1
 jmp finished
bad:
 xor eax,eax
finished:
 add rsp,28h
 pop r15
 pop r14
 pop r13
 pop r12
 pop rdi
 pop rsi
 pop rbx
 pop rbp
 ret
DispatchInvoke endp
END
