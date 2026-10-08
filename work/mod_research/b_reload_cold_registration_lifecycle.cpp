// Explicit successor object. Frozen source remains unchanged; only AFTER's
// registration callee is redirected. Activation's RegisterColdPool is not renamed.
#define RegisterColdPool CoordinatedRegisterColdPool
#include "b_reload_lifecycle.cpp"
#undef RegisterColdPool
