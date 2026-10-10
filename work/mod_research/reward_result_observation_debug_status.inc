// DR6 B0..B3/BD/BS/BT are event ownership, not reserved-bit normalization.
// Requires Registers and ownedTrap from the debugger core above this include.
static constexpr DWORD64 debugEventMask=0xE00F;
static bool debugStatusVacant(const CONTEXT& c){return (c.Dr6&debugEventMask)==0;}
static bool mayRestoreDebugStatus(const CONTEXT& current,const Registers& original,
        const Registers& armed,bool deliveredOwned,uint64_t pendingRip=0,
        uint64_t pendingDr6=0,const Registers* pendingArmed=nullptr){
    if((current.Dr6&debugEventMask)==(original.dr6&debugEventMask))return true;
    // deliveredOwned is computed from the current real DEBUG_EVENT identity,
    // handled status, thread and exception address; it alone is insufficient.
    if(deliveredOwned&&ownedTrap(current,armed))return true;
    // A queued event must match the exact frozen ownership snapshot, including
    // its event bits. A mere thread entry in pendingOwned never suffices.
    return pendingArmed&&current.Rip==pendingRip&&
        (current.Dr6&debugEventMask)==(pendingDr6&debugEventMask)&&ownedTrap(current,*pendingArmed);
}
