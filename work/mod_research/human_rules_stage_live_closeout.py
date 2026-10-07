"""Validate retained preparation evidence; no game read, call or retry."""
from pathlib import Path
import hashlib
import json
from human_rules_stage_live_start import same_known_data, DLL_SHA, profiles

P=Path(__file__).resolve().parent
RUN=P/'human_rules_stage_live_runs/20261007-222556-471691'


def read(path):return json.loads(path.read_text(encoding='utf8'))
def ref(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    before=read(RUN/'known-before.json');after=read(RUN/'known-after.json')
    raw=read(RUN/'result.json');fresh=read(RUN/'inspection-222710-428096.json')
    assert raw['result']=='INCOMPLETE' and raw['prepare_exit']==0
    assert raw['error']=="RuntimeError('Known planning data changed during preparation')"
    assert same_known_data(before,after)
    # Verify the comparator does not silently exclude actual tile/game data.
    import copy
    altered=copy.deepcopy(after);altered['tiles']['ordered_payload_hex']+='00'
    assert not same_known_data(before,altered)
    assert before['tiles']['created']!=after['tiles']['created']
    assert fresh['descriptor']==raw['descriptor']
    assert fresh['counters']==raw['counters']==dict(state=2,error=0,entered=[0]*6,exited=[0]*6,
        active=0,abnormal=0,unexpected_income_caller=0)
    assert fresh['source_bytes']==[expected.hex() for _,_,expected in profiles()]
    assert fresh['snapshot']==after['context']['snapshot']
    assert raw['dll_sha256']==DLL_SHA
    assert ref(Path(raw['dll']))['sha256']==DLL_SHA
    result=dict(result='PASS_REAL_GAME_PREPARED_NOT_PUBLISHED',original_result_retained=ref(RUN/'result.json'),
        independent_later_inspection=ref(RUN/'inspection-222710-428096.json'),
        before=ref(RUN/'known-before.json'),after=ref(RUN/'known-after.json'),
        cause='Only tiles.created wall-clock capture metadata differs; all remaining fields are exactly equal.',
        descriptor=raw['descriptor'],dll=ref(Path(raw['dll'])),game_orders=0,source_patches=0,
        prepare_retried=False,module_retained=True,full_world_verified=False,
        publication_authorized=False,two_player_ready=False)
    path=RUN/'preparation-closeout.json'
    with path.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'result':result['result'],'path':str(path),'sha256':ref(path)['sha256']}))


if __name__=='__main__':main()
