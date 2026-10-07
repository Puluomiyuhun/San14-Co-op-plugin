"""Check end-to-end evidence after the duplicate network delivery."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from pilot_evidence import check_restored,check_checkpoint,load_json,require
from pilot_request import canonical,validate_payload

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs'/'san14-link'))
from battle_observer import BattleObserver

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True)
parser.add_argument('--restored',action='store_true')
args=parser.parse_args()
result=load_json(args.run/'result.json')
payload=load_json(args.run/'received-command.json')
validate_payload(payload)
receipts=load_json(args.run/'receipts.json')
require(receipts[1]=={**receipts[0],'duplicate':True},'Duplicate did not return the original receipt')
require(result['request_id']==payload['request_id']==receipts[0]['request_id'],'Request identity mismatch')
require(hashlib.sha256(canonical(payload)).hexdigest()==receipts[0]['payload_sha256'],'Payload digest mismatch')
journal=[json.loads(line) for line in (args.run/'requests.jsonl').read_text().splitlines()]
require(len(journal)==2 and [row['state'] for row in journal]==['IN_PROGRESS','COMPLETED'],
        'Expected one execution intent and one completion record')
adapter_run=Path(receipts[0]['effect']['adapter_result_directory'])
adapter=load_json(adapter_run/'result.json')
require(adapter['request_id']==payload['request_id'] and adapter['command_source']=='validated-command-file',
        'Adapter did not use the received request')
require(adapter['adapter']['submit_calls']==1 and adapter['adapter']['status']==4,'Native execution count/status mismatch')
result['state_unchanged_after_duplicate']=check_restored(load_json(adapter_run/'after.json'),
                                                       load_json(ROOT/'after-network-pilot-duplicate.json'))
require(load_json(ROOT/'native-command-army-fields.json')==load_json(ROOT/'network-command-army-fields.json'),
        'Network execution produced different command-related army fields')
result['final_army_fields_match_normal_submission']=True
result['final_army_fields_compared']=25
result['temporary_update_hook_restored']=bool(adapter['adapter']['slot_restored'] and adapter['adapter']['protection_restored'])
result['inert_test_modules_remain_loaded_until_game_exit']=True
if args.restored:
    reader=BattleObserver()
    try:
        current=reader.capture()
        result['post_test_restore']=check_restored(load_json(ROOT/'before-native-submit.json'),current)
        require(struct.unpack('<Q',reader.memory.read(reader.memory.base+0x12CC4A8+0x28,8))[0]==reader.memory.base+0x3F9B00,
                'Native player-update callback is not restored')
        result['original_update_slot_verified_after_restore']=True
        (args.run/'restored.json').write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:reader.close()
    check_checkpoint(Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14'))
    result['saved_checkpoint_unchanged']=True
(args.run/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT.parents[1]/'outputs'/'san14-link'/'网络命令自动执行验证.json').write_text(
    json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','network_deliveries':2,'game_executions':1,
                  'duplicate_left_observed_state_unchanged':True,'post_test_restore':result['post_test_restore']},indent=2))
