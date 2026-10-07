option casemap:none
EXTERN ReadyInputGlobalUiEntry:PROC
EXTERN ReadyInputPanelEntry:PROC
EXTERN ReadyFixtureUi:QWORD
EXTERN ReadyFixtureGame:QWORD
PUBLIC ReadyFixtureGameBody
PUBLIC ReadyFixtureGlobalReturn
PUBLIC ReadyFixturePanelReturn
.code
ReadyFixtureGameBody PROC FRAME
 sub rsp,28h
 .allocstack 28h
 .endprolog
 mov rcx,ReadyFixtureUi
 mov rdx,12345678h
 mov r8,23456789h
 mov r9,3456789ah
 call ReadyInputGlobalUiEntry
ReadyFixtureGlobalReturn::
 mov rcx,ReadyFixtureGame
 mov rdx,12345678h
 mov r8,23456789h
 mov r9,3456789ah
 call ReadyInputPanelEntry
ReadyFixturePanelReturn::
 mov rax,0abcdef1234567890h
 add rsp,28h
 ret
ReadyFixtureGameBody ENDP
END

