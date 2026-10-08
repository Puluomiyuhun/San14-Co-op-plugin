; Static runtime-function entries for bounded owned MEM_IMAGE fixture ranges.
; Unwind data is populated before Bootstrap, never used by the ordinary CRT.
option dotname
.pdata SEGMENT READONLY ALIGN(4)
 DD 01447B2h,01447C0h,02300000h
 DD 0509580h,0509639h,02300040h
 DD 050B730h,050B79Ah,02300080h
 DD 0834D10h,0834E75h,023000C0h
 DD 083A930h,083AA2Dh,02300100h
.pdata ENDS
END
