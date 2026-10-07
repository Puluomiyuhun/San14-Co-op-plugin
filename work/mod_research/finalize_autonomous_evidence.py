"""Finalize real autonomous evidence and, optionally, verify native-save restore."""
import argparse
import json
from pathlib import Path
import struct
import sys
from pilot_evidence import load_json,check_restored,check_checkpoint,require

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs'/'san14-link'))
from battle_observer import BattleObserver

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True)
parser.add_argument('--restored',action='store_true')
parser.add_argument('--army-fields',type=Path,default=ROOT/'autonomous-command-army-fields.json')
args=parser.parse_args()
result=load_json(args.run/'result.json')
require(result['result']=='PASS' and result['mode']=='autonomous-single-sortie','Expected successful autonomous execution')
normal_fields=load_json(ROOT/'native-command-army-fields.json')
autonomous_fields=load_json(args.army_fields)
require(normal_fields==autonomous_fields,'Final army fields disagree with normal submission')
result['compared_final_army_fields']=len(normal_fields['comparisons'])
result['final_army_fields_match_normal_submission']=True
if args.restored:
    reader=BattleObserver()
    try:
        restored=reader.capture()
        result['post_test_restore']=check_restored(load_json(ROOT/'before-native-submit.json'),restored)
        slot=reader.memory.base+0x12CC4A8+0x28
        require(struct.unpack('<Q',reader.memory.read(slot,8))[0]==reader.memory.base+0x3F9B00,
                'Player update slot is not the original game function')
        result['original_update_slot_verified_after_restore']=True
        (args.run/'restored.json').write_text(json.dumps(restored,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:reader.close()
    check_checkpoint(ROOT.parent/'mod_test'/'replay-checkpoint-34'/'svdexSC34.s14')
    check_checkpoint(Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14'))
    result['saved_checkpoint_unchanged']=True
(args.run/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
destination=ROOT.parents[1]/'outputs'/'san14-link'/'自动出征试验.json'
destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':result['result'],'compared_fields':result['compared_final_army_fields'],
                  'post_test_restore':result['post_test_restore']},ensure_ascii=True,indent=2))
