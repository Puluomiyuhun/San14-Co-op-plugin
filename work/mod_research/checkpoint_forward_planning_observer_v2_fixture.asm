option casemap:none
extern CheckpointLoadDispatchBridge0:proc
extern PlanningFixtureBody:proc
.code
public PlanningFixtureReturn
PlanningFixtureInvoke proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call CheckpointLoadDispatchBridge0
PlanningFixtureReturn label near
 add rsp,28h
 ret
PlanningFixtureInvoke endp
PlanningFixtureOriginal proc frame
 sub rsp,28h
 .allocstack 28h
 .endprolog
 call PlanningFixtureBody
 mov rax,0aabbcc1234567890h
 pcmpeqd xmm0,xmm0
 add rsp,28h
 ret
PlanningFixtureOriginal endp
end
