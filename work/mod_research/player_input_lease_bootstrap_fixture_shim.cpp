// Linked only into the owned-window fixture DLL.
#include <windows.h>
void PlayerInputLeaseBeforePublish(HWND){char value[8]{};if(GetEnvironmentVariableA("OWNED_INPUT_BOOTSTRAP_DELAY",value,sizeof value)&&value[0]=='1')Sleep(400);}
