"""One-time source refactor of the separate candidate, never the retired pilot."""
from pathlib import Path
P=Path(__file__).resolve().parent
path=P/'checkpoint_push_pilot.cpp'
text=path.read_text(encoding='utf8')
a=text.index('static void __fastcall saveUpdateHook(')
b=text.index('static bool installSaveObserver()',a)
text=text[:a]+'#include "checkpoint_push_save_callbacks.inc"\n\n'+text[b:]
a=text.index('static void __fastcall updateHook(')
b=text.index('extern "C" __declspec(dllexport) DWORD WINAPI InstallCheckpointPush',a)
text=text[:a]+'#include "checkpoint_push_user_callbacks.inc"\n\n'+text[b:]
old='''#ifndef CHECKPOINT_PUSH_FIXTURE
    // RETIRED: 412520 is replace-top (type2), not a push/save-and-return entry.
    // Root observed unintended date advancement. Never re-enable this profile.
    (void)input;return 9001;
#endif
'''
assert old in text
text=text.replace(old,'    // Distinct candidate: 2DF990/type0. Old private_checkpoint_save stays retired.\n')
text=text.replace('&saveUpdateHook','&CheckpointPushBridge1').replace('&updateHook','&CheckpointPushBridge0')
text=text.replace('cfg.version!=1','cfg.version!=2')
text=text.replace('base+0x412520','base+0x2DF990')
text=text.replace('at<uint32_t>(queue)==2','at<uint32_t>(queue)==0')
text=text.replace('static bool guard(void* self){','static bool guard(void* self,bool returned){')
text=text.replace('return pathsAndSlot();','return returned || pathsAndSlot();')
text=text.replace('if(!cache || at<int32_t>(cache+8)!=0 || at<int32_t>(cache+0x3EC)!=-1)return reject(19);',
'''if(!cache || (at<uint32_t>(cache+8)>1) || at<int32_t>(cache+0x3EC)!=-1 ||
       at<uint32_t>(cache+0x3F0)!=0 || at<uint64_t>(cache+0x18)!=0)return reject(19);''')
text=text.replace('queueSave(reinterpret_cast<void*>(manager),reinterpret_cast<const char*>(base+0x12AA8E0),0);',
'''alignas(16) unsigned char emptyCallback[64]{};
    queueSave(reinterpret_cast<void*>(manager),reinterpret_cast<const char*>(base+0x12AA8E0),0,emptyCallback);''')
path.write_text(text,encoding='utf8')
print('Refactored candidate only')
