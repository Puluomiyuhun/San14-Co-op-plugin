option casemap:none
extern DynamicGuardEntries:qword
.code
public DynamicGuardReturn
DynamicGuardInvoke proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov r10,rcx
 mov rcx,rdx
 mov rdx,1001h
 mov r8,1002h
 mov r9,1003h
 lea rax,DynamicGuardEntries
 call qword ptr [rax+r10*8]
DynamicGuardReturn label near
 add rsp,28h
 ret
DynamicGuardInvoke endp
end
