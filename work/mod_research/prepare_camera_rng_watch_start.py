"""Generate strict read-only launcher; reference changes must be explicit."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'start_camera_route_observer.py').read_text(encoding='utf-8')
s=s.replace("args=p.parse_args()", "p.add_argument('--reference',required=True);args=p.parse_args()\nassert args.reference.replace('-','').isalnum()")
s=s.replace('observe_camera_route.exe','observe_camera_rng_watch.exe').replace('camera-route-validation.json','camera-rng-watch-validation.json')
s=s.replace("ROOT/'lockstep-traces/restored-next-cell-j2.json'", "ROOT/'lockstep-traces'/(args.reference+'.json')")
s=s.replace('points=(0x15b070,0x15b12f,0x3aa805,0x3f9344)', 'points=(0x15b070,0x15b12f,0x3f9344)')
s=s.replace("    run.mkdir()", '''    root=r.pointer(r.memory.base+0x1FCA1E0)
    tactic_table=[]
    for identity in range(201):
        address=r.pointer(root+0x76C00+identity*8);r.require_type(address,'CTacticsData')
        raw=r.memory.read(address,0x88)
        tactic_table.append({'id':identity,'address':hex(address),'name':raw[0x10:0x40].decode('utf-16le').split('\\0')[0],'raw_hex':raw.hex()})
    assert before==sample(r),'Game changed while capturing tactics table'
    run.mkdir()
    (run/'tactics-table.json').write_text(json.dumps(tactic_table,ensure_ascii=False,indent=2),encoding='utf-8')''')
s=s.replace("'marker_rvas':[hex(v) for v in points]", "'marker_rvas':[hex(v) for v in points],'rng_data_watch_rva':'0x18eb8b0','reference':args.reference")
s=s.replace('primary RNG writer','all writes to the watched global RNG state')
s=s.replace('Other RNG writers are not hooked.', 'Only the known global RNG state is watched; other undiscovered generators remain outside scope. Prior observed value is not guaranteed atomic before-value for racing writers.')
(ROOT/'start_camera_rng_watch.py').write_text(s,encoding='utf-8')
