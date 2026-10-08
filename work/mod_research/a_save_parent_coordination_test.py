"""Offline runner: source pins, bounded archive CPU paths and honest doubles.

Requires SAN14_PRIVATE_FIXTURE_ROOT; reads only two fixed archived research
files and python_deps there. No game lookup, saves, UI, debugger or network.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import sys
import traceback

P=Path(__file__).resolve().parent
SOURCES=('a_save_parent_coordination_test.py','a_save_parent_coordination_audit.py',
         'a_save_writer_scope_audit.py','private_checkpoint_save_apply_regression.py',
         'save_return_menu_regression.py')
ARCHIVE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
PDATA_SHA='74e018f15ec009af5fd0e0d91ce981b82d7d970150b3dce5861f17d11eea2e9f'


def hashes():return {n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in SOURCES}


def main():
    run=P/'a_save_parent_coordination_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    r=dict(schema='san14.a-save-parent-coordination.test.v1',result='FAIL',cases=[],
           game_access=False,production_permit=False,save_files_written=False,
           actual_os_threads=False,full_writer_exclusion=False,source_sha256=hashes())
    status=1
    try:
        private=Path(os.environ['SAN14_PRIVATE_FIXTURE_ROOT']).resolve()
        sys.path.insert(0,str(private/'python_deps'))
        import a_save_parent_coordination_audit as a
        raw=(private/'game-runtime-image.bin').read_bytes()
        pdata=(private/'runtime-pdata.bin').read_bytes()
        a.need(hashlib.sha256(raw).hexdigest()==ARCHIVE_SHA,'fixed archive identity')
        a.need(hashlib.sha256(pdata).hexdigest()==PDATA_SHA,'fixed pdata identity')
        r.update(archive_sha256=ARCHIVE_SHA,pdata_sha256=PDATA_SHA)
        r['ranges']={n:dict(begin=x,end=y,sha256=hashlib.sha256(raw[x:y]).hexdigest())
                     for n,(x,y) in dict(a.prior.RANGES,**a.EXTRA).items()}
        r['cases'].append(a.static_case(raw))
        menu=a.menu_source(raw); r['cases'].append(menu); names=menu['stacks'][-1]
        for mode in ('empty','held-army','join-without-producer','join-then-restart'):
            for locked in (False,True):r['cases'].append(a.frames_case(raw,names,mode,locked))
        r['cases'].append(a.queue_barrier_case(raw,names))
        r['observation_spec']=a.observation_spec(raw)
        r['execution_limits']=[
          'Seven-state order is constructed by archived menu/queue fragments; all menu lifecycle/UI callbacks there remain the frozen explicit doubles.',
          'Frame VM maps that resulting order into new owned objects: no full native menu-to-worker lifetime claim.',
          'Archived scheduler/Game/User/Save Update and army pending-to-working transfer execute on one emulated CPU.',
          'Root pool dispatch/callable storage, other state Updates, UI descendants, OS thread and container allocation/clear services are explicit doubles.',
          'Army and Save thread dispatch records are separate service attempts; neither worker body nor file serializer executes in this frame experiment.',
          'Join cases deliberately reset phase to zero before an extra frame, then optionally run the actual producer; this probes a prior-drain claim, not natural uninterrupted Save timing.',
          'No result establishes an observed real race, bad save, absent transitive coordination, or a production exclusion lease.'
        ]
        a.need(hashes()==r['source_sha256'],'source changed during test')
        a.need(hashlib.sha256((private/'game-runtime-image.bin').read_bytes()).hexdigest()==ARCHIVE_SHA,'archive changed during test')
        a.need(hashlib.sha256((private/'runtime-pdata.bin').read_bytes()).hexdigest()==PDATA_SHA,'pdata changed during test')
        r.update(result='PASS',source_unchanged=True,archive_unchanged=True,pdata_unchanged=True)
        status=0
    except Exception as exc:
        r['error']=repr(exc);r['traceback']=traceback.format_exc()
    finally:
        (run/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(result=r['result'],cases=len(r['cases']),path=str(run/'result.json'),error=r.get('error'))))
    return status


if __name__=='__main__':raise SystemExit(main())
