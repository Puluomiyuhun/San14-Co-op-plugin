"""Explicit production three-slot reward/planning export overlay."""
from pathlib import Path
from a_runtime_reward_three_sources import sources as runtime_sources
from a_save_three_cycle_sources import replace
def sources(root):
 root=Path(root);out=runtime_sources(root)
 h=(root/'a_save_runtime_exports.h').read_text(encoding='utf-8')
 out['a_save_runtime_exports.h']=replace(replace(h,'Magic=0x31585241','Magic=0x33585241'),'mailboxStates[2]','mailboxStates[3]')
 return out
