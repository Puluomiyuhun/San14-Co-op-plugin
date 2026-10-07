option casemap:none
extern BindingFixtureGeneration:qword
.code
; The archived initialized ContextInit fastpath shape, never invoked by adapter.
BindingFixtureContextInit proc
    db 40h,53h,48h,83h,0ech,20h,48h,8bh,51h,08h,48h,8bh,0d9h
    mov rax,qword ptr [BindingFixtureGeneration]
    db 48h,3bh,0d0h,74h,42h
    db 66 dup(0cch)
    db 48h,8dh,41h,10h,48h,83h,0c4h,20h,5bh,0c3h
BindingFixtureContextInit endp
end
