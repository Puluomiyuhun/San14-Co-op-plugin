option casemap:none
EXTERN SelectionGuardEvent:PROC
.code
; Fixture-only probe for the original 4FABD7 tail jump. The original seven
; bytes already loaded parent/event. Its instrumented CALL supplies an actual
; return PC; C++ observes it, then executes the original 509F50 handler.
; The extra RET at 4FABDC is owned-fixture instrumentation, not a live detour.
SelectionGuardEventBridge PROC
 mov r8,[rsp]
 sub rsp,20h
 call SelectionGuardEvent
 add rsp,20h
 ret
SelectionGuardEventBridge ENDP
END
