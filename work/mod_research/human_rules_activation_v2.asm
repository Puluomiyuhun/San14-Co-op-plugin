option casemap:none
EXTERN HumanRulesActivationIncomeTarget:QWORD
.code
PUBLIC HumanRulesActivationIncome
HumanRulesActivationIncome PROC
 jmp QWORD PTR [HumanRulesActivationIncomeTarget]
HumanRulesActivationIncome ENDP
END
