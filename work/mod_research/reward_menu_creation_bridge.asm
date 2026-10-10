option casemap:none
EXTERN RewardMenuCreationActivated:PROC
IFDEF REWARD_MENU_CREATION_SHADOW_STRESS
EXTERN CreationShadowPressure:PROC
ENDIF
.code
RewardMenuCreationActivation PROC FRAME
 push rbp
 .pushreg rbp
 pushfq
 .allocstack 8
 sub rsp,0E8h
 .allocstack 0E8h
 lea rbp,[rsp+80h]
 .setframe rbp,80h
 .endprolog
 ; [RSP..RSP+1Fh] is exclusively the callee's home area.
 mov [rbp-60h],rax
 mov [rbp-58h],rcx
 mov [rbp-50h],rdx
 mov [rbp-48h],r8
 mov [rbp-40h],r9
 mov [rbp-38h],r10
 mov [rbp-30h],r11
 movdqu [rbp-20h],xmm0
 movdqu [rbp-10h],xmm1
 movdqu [rbp],xmm2
 movdqu [rbp+10h],xmm3
 movdqu [rbp+20h],xmm4
 movdqu [rbp+30h],xmm5
 mov rcx,r15
 mov rdx,r13
 mov r8,[rbp+78h]
IFDEF REWARD_MENU_CREATION_SHADOW_STRESS
 call CreationShadowPressure
ELSE
 call RewardMenuCreationActivated
ENDIF
 push qword ptr [rbp+68h]
 popfq
 movdqu xmm0,[rbp-20h]
 movdqu xmm1,[rbp-10h]
 movdqu xmm2,[rbp]
 movdqu xmm3,[rbp+10h]
 movdqu xmm4,[rbp+20h]
 movdqu xmm5,[rbp+30h]
 mov rax,[rbp-60h]
 mov rcx,[rbp-58h]
 mov rdx,[rbp-50h]
 mov r8,[rbp-48h]
 mov r9,[rbp-40h]
 mov r10,[rbp-38h]
 mov r11,[rbp-30h]
 ; Replay precisely the two MOV instructions replaced at 50B35B.
 mov rcx,[r15+10h]
 mov rax,[r15+20h]
 lea rsp,[rbp+70h]
 pop rbp
 ret
RewardMenuCreationActivation ENDP
END
