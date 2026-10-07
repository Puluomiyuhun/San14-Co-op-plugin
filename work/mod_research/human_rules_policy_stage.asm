option casemap:none
EXTERN HumanRulesPolicyIncomeTarget:QWORD
.code
PUBLIC HumanRulesPolicyIncome
HumanRulesPolicyIncome PROC
 ; No CALL or stack frame: original native CALL return PC reaches the frozen
 ; predicate so its _ReturnAddress still identifies 28DE76 or 28DAAA.
 jmp QWORD PTR [HumanRulesPolicyIncomeTarget]
HumanRulesPolicyIncome ENDP
END
