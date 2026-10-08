option casemap:none
extern ReportEarlySnippet:QWORD
.code
ReportEarlyInvoke proc frame
 push rsi
 .pushreg rsi
 push rbp
 .pushreg rbp
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rsi,rcx
 xor ebp,ebp
 call qword ptr [ReportEarlySnippet]
 add rsp,28h
 pop rbp
 pop rsi
 ret
ReportEarlyInvoke endp
end
