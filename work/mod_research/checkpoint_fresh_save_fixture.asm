option casemap:none
EXTERN CheckpointPersistentBridge0:PROC
EXTERN CheckpointPersistentBridge1:PROC
PUBLIC FreshDispatch
PUBLIC FreshDispatchReturn
.code
FreshDispatch PROC FRAME
 sub rsp,28h
 .allocstack 28h
 .endprolog
 lea r11,CheckpointPersistentBridge0
 test ecx,ecx
 jz chosen
 lea r11,CheckpointPersistentBridge1
chosen:
 mov rcx,rdx
 mov edx,1122h
 mov r8d,3344h
 mov r9d,5566h
 call r11
FreshDispatchReturn::
 add rsp,28h
 ret
FreshDispatch ENDP
END
