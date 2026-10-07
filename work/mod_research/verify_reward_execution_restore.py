"""Read-only verification after the user loads checkpoint34 through the game."""
import json
from pathlib import Path
from run_reward_execution_pilot import ROOT,CHECKPOINT,capture,diff_records,save
from battle_observer import BattleObserver
from pilot_evidence import load_json,require,check_restored,check_checkpoint

def main():
    live=load_json(ROOT/'reward-execution-live-latest.json');run=Path(live['directory'])
    before=load_json(run/'before.json');reader=BattleObserver()
    try:
        restored=capture(reader)
        differences=diff_records(before,restored)
        save(run/'restore-raw-differences.json',differences)
        # Native loading rebuilds CUnitArmy objects. CArmyUnitData+148 points
        # to that runtime object; current RTTI plus its +40 backlink establish
        # the owning army. Never mask unrelated fields or resource differences.
        substantive=[row for row in differences if not row['object'].startswith('army:')
                     or any(c['offset'] not in range(0x148,0x150) for c in row['changes'])]
        if substantive:
            print(json.dumps({'result':'RESTORE_PENDING','changed_objects':[r['object'] for r in substantive]},ensure_ascii=True))
            return
        root=reader.pointer(reader.memory.base+0x1FCA1E0);links=[]
        for unit in restored['focused']['all_active_units']:
            address=reader.pointer(root+0x7DF60+unit['id']*8)
            old=int.from_bytes(bytes.fromhex(before['records'][f"army:{unit['id']}"])[0x138:0x140],'little')
            pointer=int.from_bytes(reader.memory.read(address+0x148,8),'little')
            require(bool(old)==bool(pointer),'Runtime army presence changed')
            if pointer:
                reader.require_type(pointer,'CUnitArmy')
                require(reader.pointer(pointer+0x40)==address,'Runtime army backlink mismatch')
            links.append({'army_id':unit['id'],'runtime_present':bool(pointer),'pointer_rebuilt':old!=pointer})
        require(restored==capture(reader),'Restored state is not stable')
        comparison=check_restored(before['focused'],restored['focused'])
        require(before['eligibility']==restored['eligibility'],'Person/task state does not match baseline')
        base=reader.memory.base;slot=int.from_bytes(reader.memory.read(base+0x12CC4A8+0x28,8),'little')
        require(slot==base+0x3F9B00,'Original update slot not restored')
        check_checkpoint(CHECKPOINT)
        save(run/'restored.json',restored)
        result={'result':'PASS','method':'User loaded checkpoint34 through native game UI',
                'focused_state':comparison,'sampled_raw_record_count':len(before['records']),
                'sampled_records_match_except_validated_runtime_army_pointer':True,
                'raw_records_byte_identical':not differences,
                'runtime_pointer_exception':{'army_offset':'0x148..0x150','pointee_type':'CUnitArmy',
                                             'backlink_offset':'0x40','validated_links':links},
                'persons':before['eligibility']['person_count'],
                'tasks':before['eligibility']['task_count'],'active_armies':len(before['focused']['all_active_units']),
                'person_records_sha256':restored['eligibility']['person_records_sha256'],
                'task_fields_sha256':restored['eligibility']['task_fields_sha256'],
                'checkpoint34_unchanged':True,'original_update_restored':True,
                'scope':before['record_scope']+' Restore comparison permits only the validated CUnitArmy runtime pointer at army+148; no blanket pointer masking.'}
        save(run/'restore-verification.json',result)
        live['stage']='NATIVE_REWARD_EXECUTION_AND_RESTORE_PASS';live['restore_verified']=True;live['restoration']=result
        save(run/'result.json',live);save(ROOT/'reward-execution-live-latest.json',live)
        print(json.dumps({k:v for k,v in result.items() if k!='runtime_pointer_exception'},ensure_ascii=True,indent=2))
    finally:reader.close()

if __name__=='__main__':main()
