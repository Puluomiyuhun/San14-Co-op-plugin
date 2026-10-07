"""Reuse read-only precheck utilities in a NEW launcher, never enable old one."""
from pathlib import Path
P=Path(__file__).resolve().parent
old=(P/'private_checkpoint_save_start.py').read_text(encoding='utf8')
text=old[:old.index('def gate_evidence(')]
text=text.replace('PrivateCheckpointSave','CheckpointPush').replace('private_checkpoint_save_','checkpoint_push_')
text=text.replace('mpckpt01.s14','mppush01.s14')
text=text.replace('from checkpoint_push_contract import REPORT,decode,dry_ok,native_lifecycle_ok,complete_ok,read_std_string,pending_vector_valid',
                  'from checkpoint_push_contract import REPORT,decode,dry_ok,native_lifecycle_ok,complete_ok,completion_evidence,read_std_string,pending_vector_valid')
text=text.replace("i(cache+8)==0 and i(cache+0x3EC)==-1", "i(cache+8) in (0,1) and i(cache+0x3EC)==-1 and i(cache+0x3F0)==0 and q(cache+0x18)==0")
text=text.replace("    need(ctx==capture_startup_context(reader) and business==reader.capture(),'sampling_changed')", '''    stack=q(state_manager+0x20);user=q(stack+32);game=q(stack+16)
    toolbar=q(user+0x478);panel=q(game+0x480);special=q(m.base+0x201EC70)
    need(i(toolbar+0x88)==-1 and i(game+0x47C)==0 and panel and i(panel+0x1B0)==0,'pending_menu_or_advance')
    need(all(q(user+o)==0 for o in (0x4A8,0x4B0,0x4B8)),'selection_not_empty')
    need(not special or i(special)==0,'special_context_active')
    need(i(m.base+0x1A38EC8+0x28)==0 and i(m.base+0x19E7510+0x13C)==1,'controls_not_resumed')
    for off,rva in ((0x18,0x3F5530),(0x20,0x3F5920),(0x58,0x3F7710),(0x60,0x3F7A70)):
        need(q(m.base+0x12CC4A8+off)==m.base+rva,'User_lifecycle_hook_present')
    need(ctx==capture_startup_context(reader) and business==reader.capture(),'sampling_changed')''')
text=text.replace("'game_writes':0,'scope':", "'pinned_user':hex(user),'pinned_game':hex(game),'pinned_world':hex(world),'cache_mode':i(cache+8),'global_rng':i(m.base+0x18EB8B0)&0xffffffff,'game_writes':0,'scope':")
text=text.replace('Fixed mppush01.s14 export pilot.', 'Separate type0 push/export pilot for mppush01.s14.')
with (P/'checkpoint_push_start.py').open('x',encoding='utf8') as f:f.write(text)
print('Created new read-only precheck section; no game access')
