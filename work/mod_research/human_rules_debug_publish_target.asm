option casemap:none
.code
OwnedBreak PROC
 int 3
 ret
OwnedBreak ENDP
EXTERN Running:DWORD
Busy PROC
 cmp DWORD PTR [Running],0
 jne Busy
 ret
Busy ENDP
MAKE_SITE MACRO number
PUBLIC Site&number
Site&number PROC
 REPT 14
 nop
 ENDM
 mov eax,number
 ret
Site&number ENDP
ENDM
MAKE_SITE 0
MAKE_SITE 1
MAKE_SITE 2
MAKE_SITE 3
MAKE_SITE 4
MAKE_SITE 5
END
