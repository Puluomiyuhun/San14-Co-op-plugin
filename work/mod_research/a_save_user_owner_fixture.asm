option casemap:none
extern FixtureUserBody:proc
extern FixtureSaveBody:proc
public FreshDispatch
public FreshDispatchReturn
public FreshRawUser
public FreshRawSave
public FreshSuppressed
.const
align 16
ExpectedXmm byte 16 dup(42h)
.code
FreshDispatch proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 ; Fetch the actual own-object vtable slot, not a hand-filled observer frame.
 mov rcx,rdx
 mov r11,qword ptr [rcx]
 mov r11,qword ptr [r11+28h]
 mov edx,1122h
 mov r8d,3344h
 mov r9d,5566h
 call r11
FreshDispatchReturn::
 movdqa xmm1,xmmword ptr [ExpectedXmm]
 pcmpeqb xmm1,xmm0
 pmovmskb r10d,xmm1
 cmp r10d,0ffffh
 je xmm_ok
 xor eax,eax
xmm_ok:
 add rsp,28h
 ret
FreshDispatch endp
RAW_ENTRY macro name:req, body:req
name proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call body
 movdqa xmm0,xmmword ptr [ExpectedXmm]
 add rsp,28h
 ret
name endp
endm
RAW_ENTRY FreshRawUser,FixtureUserBody
RAW_ENTRY FreshRawSave,FixtureSaveBody
; An owned planning suppression fixture. It does not invoke raw User at all.
FreshSuppressed proc
 mov eax,7777h
 ret
FreshSuppressed endp
end
