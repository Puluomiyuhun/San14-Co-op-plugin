"""Read-only post-attempt observations; no installation or native calls."""
import json,struct,sys
from datetime import datetime
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
from battle_observer import BattleObserver
from checkpoint_complete_live_start import live_hook_evidence,save,target_files
from checkpoint_complete_live_capture import known_snapshot
from checkpoint_push_start import process_birth

def main():
    claim=json.loads((P/'checkpoint_complete_live_once.json').read_text('utf8'));run=Path(claim['run'])
    result=json.loads((run/'result.json').read_text('utf8'))
    if not result.get('install_completed') or result.get('control_lifetime_uncertain') is not False:
        raise RuntimeError('Require known completed controls')
    desc=json.loads((run/'description.json').read_text('utf8'));bindings=json.loads((run/'bindings.json').read_text('utf8'))
    reader=BattleObserver()
    try:
        assert (reader.pid,process_birth(reader),reader.memory.base)==(claim['pid'],claim['birth'],claim['base'])
        m=reader.memory;b=m.base;q=lambda a:struct.unpack('<Q',m.read(a,8))[0]
        d=lambda a:struct.unpack('<I',m.read(a,4))[0]
        current=[dict(name=n,address=a,phase=d(a+0x470),disabled=d(a+0x68)) for n,a in reader.state_objects()]
        old=json.loads((run/'hook-before.json').read_text('utf8'))
        owned=desc['dispatchBridge']+[desc['workerBridge'],desc['readBridge']]
        hooks=live_hook_evidence(reader,bindings['planning'],bindings['storage'],expected=owned,baseline=old)
        snapshot=known_snapshot(reader,expected_user_hook=owned[0])
        prior=json.loads((run/'known-before.json').read_text('utf8'))
        files=target_files()
        output=dict(schema='san14.complete-load-postcapture.v1',read_only=True,native_calls=0,
            original_attempt_result=result['result'],current_states=current,current_dispatch=q(b+0x19e7358),
            cache=q(b+0x2025318),pending=struct.unpack('<i',m.read(q(b+0x2025318)+0x3ec,4))[0],
            hooks=hooks,known_snapshot=snapshot,save_files_unchanged=prior['save_files']==snapshot['save_files'],
            target_files=files,full_world_verified=False,planning_callback_proven=False)
        dest=run/('postcapture-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json');save(dest,output)
        print(json.dumps(dict(path=str(dest),states=current,context=snapshot['context'],save_files_unchanged=output['save_files_unchanged']),ensure_ascii=False))
    finally:reader.close()

if __name__=='__main__':main()
