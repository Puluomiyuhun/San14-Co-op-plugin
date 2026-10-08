option casemap:none
extern InputFixtureUi:QWORD
extern InputGameTail:proc
extern ActionPanelSnippet:QWORD
extern ActionUserSnippet:QWORD
extern ActionGame:QWORD
extern FixtureUserBody:proc
extern ActionInjectTail:proc
extern InputUiBody:proc
public InputGameDispatch
public InputGameReturn
public InputUiReturn
public InputGameBody
public InputUiRaw
public ActionRawUser
.const
align 16
InputXmm byte 16 dup(42h)
.code
InputGameDispatch proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rax,qword ptr [rcx]
 mov edx,1122h
 mov r8d,3344h
 mov r9d,5566h
 call qword ptr [rax+28h]
InputGameReturn::
 movdqa xmm1,xmmword ptr [InputXmm]
 pcmpeqb xmm1,xmm0
 pmovmskb r10d,xmm1
 cmp r10d,0ffffh
 je input_xmm_ok
 xor eax,eax
input_xmm_ok:
 add rsp,28h
 ret
InputGameDispatch endp
InputGameBody proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rcx,InputFixtureUi
 mov edx,1122h
 mov r8d,3344h
 mov r9d,5566h
 mov rax,qword ptr [rcx]
 call qword ptr [rax+18h]
InputUiReturn::
 call InputGameTail
 mov rcx,ActionGame
 call qword ptr [ActionPanelSnippet]
 mov rax,0ABCDEF1234567890h
 movdqa xmm0,xmmword ptr [InputXmm]
 add rsp,28h
 ret
InputGameBody endp
InputUiRaw proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call InputUiBody
 movdqa xmm0,xmmword ptr [InputXmm]
 add rsp,28h
 ret
InputUiRaw endp

ActionRawUser proc frame
 push rsi
 .pushreg rsi
 sub rsp,20h
 .allocstack 20h
 .endprolog
 mov rsi,rcx
 call FixtureUserBody
 call ActionInjectTail
 mov rcx,rsi
 call qword ptr [ActionUserSnippet]
 mov rax,0FEDCBA9876543210h
 movdqa xmm0,xmmword ptr [InputXmm]
 add rsp,20h
 pop rsi
 ret
ActionRawUser endp
end
