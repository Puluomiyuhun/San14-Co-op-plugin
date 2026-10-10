"""Receiver-local configuration builder; never installs or joins a room.

Default/help and --template perform no game/file capture. Explicit --capture
requires --pid --game-dir --target --invitation --adapter-key --report-key
--cut-key --output. The target is the existing svdexccSC03.s14, not a file to
stage. The invitation supplies B's force; its ruler/main district are read from
this game's current world. Optional --target-ruler/--target-district pin them.
Output contains the invitation credential, so keep it local; stdout has only
the output path/hash and public key fingerprints. Capture is a finite read-only
observation, not a fence or installation permit. Execute repeats fresh checks.
"""
import argparse
from copy import deepcopy
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'outputs/san14-link'))
SCHEMA='san14.b-portable-local.v1'


def need(value,message):
    if not value:raise ValueError(message)


def template():
    return dict(schema=SCHEMA,template_only=True,capture_required=True,
        arguments=dict(pid='CURRENT_B_PID',game_dir='ABSOLUTE_GAME_DIRECTORY',
            target='ABSOLUTE_EXISTING_svdexccSC03.s14',invitation='B_INVITATION_JSON',
            adapter_key='LOCAL_ADAPTER_KEY',report_key='LOCAL_REPORT_KEY',cut_key='LOCAL_CUT_KEY',
            output='NEW_LOCAL_CONFIG_JSON'),game_access=False,install_permission=False)


def _path(value):
    p=Path(value)
    need(p.is_absolute() and '..' not in p.parts,'Explicit absolute local path required')
    return p


class ReadOnlyIO:
    """Only explicit PID read handles; no ProcessAPI, remote calls or discovery."""
    def open(self,pid):
        from game_reader import GameReader
        return GameReader(pid=pid)

    def birth(self,reader):
        from checkpoint_complete_live_capture import process_birth
        return process_birth(reader)

    def file(self,path):
        import b_warm_staging as files
        return files.read_file(files.clean_path(path))[0]

    def keys(self,paths):
        from b_warm_adapter_key import load_key,public
        return {name:public(load_key(path))['fingerprint'] for name,path in paths.items()}

    def metadata(self,r,target_force):
        from authority_reward import capture_context
        from human_rules_activation_room import rules
        snap=r.snapshot();b=r.memory.base
        root=r.pointer(b+0x1fca1e0);world=r.pointer(root+0x85130)
        r.require_type(root,'CSan14Data');r.require_type(world,'CWorldData')
        value=lambda at,fmt:struct.unpack(fmt,r.memory.read(at,struct.calcsize(fmt)))[0]
        need(value(b+0x1fd0c5c,'<i') not in (0,-1),'Native settings not initialized')
        players=[];hashes=[]
        for force in (snap['player']['force_id'],target_force):
            c=capture_context(r,force)
            need(c['viewer_force_id']==snap['player']['force_id'] and
                 all(c['date'][k]==snap['date'][k] for k in ('year','month','day')),
                 'Actor observation changed date/viewer')
            players.append(dict(force=force,ruler=c['ruler_id'],district=c['main_district_id']))
            hashes.append(c['context_sha256'])
        need(players[0]['ruler']==snap['player']['ruler_id'],'Current ruler differs from actor table')
        need(snap==r.snapshot() and root==r.pointer(b+0x1fca1e0) and world==r.pointer(root+0x85130),
             'World changed during local metadata sample')
        return dict(pid=r.pid,birth=self.birth(r),base=b,root=root,world=world,
            node=dict(**{k:snap['date'][k] for k in ('year','month','day')},phase='PLANNING_BOUNDARY'),
            source_player=players[0],target_player=players[1],actor_context_sha256=hashes,
            states=r.state_objects(),rules=rules(value(b+0x18eb628,'<I'),(value(world+0x16a8,'<I')>>8)&1))

    def planning(self,r,p,birth):
        from b_warm_profile_capture import capture_planning
        from checkpoint_complete_live_capture import process_birth
        need(process_birth(r)==birth,'Process incarnation changed')
        # Exactly two complete equal samples; no retry/fallback/field removal.
        result=capture_planning(r,p,p.source.ruler)
        need(result['birth']==birth and process_birth(r)==birth,'Process incarnation changed')
        return result

    def original(self,r,birth):
        from b_warm_pair_diagnostic import require_original_rules,require_no_debugger
        value=require_original_rules(r,pid=r.pid,birth=birth);require_no_debugger(r)
        return value

    def window(self,r):
        from player_input_lease_bootstrap_port import window_identity
        window=r.pointer(r.memory.base+0x19055d0+0x18)
        u=C.WinDLL('user32',use_last_error=True);pid=W.DWORD()
        u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
        u.GetWindowThreadProcessId.restype=W.DWORD
        thread=u.GetWindowThreadProcessId(window,C.byref(pid))
        need(thread and pid.value==r.pid,'Current game HWND belongs to another process')
        window_identity(SimpleNamespace(reader=r),window,thread)
        return dict(handle=window,thread=thread,timeout_ms=1000)

    def steam(self,r):
        from b_warm_pair_preflight import STEAM_HASHES
        from checkpoint_complete_live_capture import module_approval
        m=r.memory;p=m.p;entries=(C.c_void_p*2048)();n=W.DWORD()
        p.GetModuleFileNameExW.argtypes=[W.HANDLE,W.HMODULE,W.LPWSTR,W.DWORD]
        p.GetModuleFileNameExW.restype=W.DWORD
        need(p.EnumProcessModulesEx(m.handle,entries,C.sizeof(entries),C.byref(n),3) and
             0<n.value<=C.sizeof(entries) and n.value%C.sizeof(C.c_void_p)==0,'Module list invalid')
        found={name:[] for name in STEAM_HASHES}
        for base in entries[:n.value//C.sizeof(C.c_void_p)]:
            buf=C.create_unicode_buffer(32768)
            length=p.GetModuleFileNameExW(m.handle,base,buf,len(buf))
            need(0<length<len(buf),'Module path unavailable/truncated')
            path=Path(buf.value);name=path.name.lower()
            if name in found:found[name].append((base,path))
        result={}
        for name,rows in found.items():
            need(len(rows)==1,'Exact single loaded Steam module required: '+name)
            base,path=rows[0];module_approval(r,base,path,STEAM_HASHES[name]);result[name]=str(path)
        return result


def assemble(invitation,meta,target,target_identity,keys,window,steam_paths,*,wait_seconds=600,native_timeout=120):
    """Pure assembly of captured values; this function does not certify reads."""
    from observed_room_service import validate_invitation
    from human_rules_activation_room import GAME_SHA,rules
    from authoritative_sync import digest,validate_node
    from b_warm_refresh_start_support import identity
    from b_observed_start import make_profile
    from b_warm_pair_preflight import STEAM_HASHES
    n=validate_invitation(invitation);validate_node(meta['node']);identity(target_identity)
    need(type(meta['pid']) is int and 0<meta['pid']<2**32 and
         type(meta['birth']) is int and 0<meta['birth']<2**64,'Exact process incarnation required')
    for name in ('source_player','target_player'):
        player=meta[name]
        need(type(player) is dict and set(player)=={'force','ruler','district'} and
             all(type(player[k]) is int and 1<=player[k]<=high for k,high in (('force',51),('ruler',5999),('district',51))),
             'Exact bounded player identity required')
    need(type(window) is dict and set(window)=={'handle','thread','timeout_ms'} and
         all(type(window[k]) is int and lo<=window[k]<=hi for k,lo,hi in
             (('handle',1,2**64-1),('thread',1,2**32-1),('timeout_ms',50,5000))),
         'Exact local window identity required')
    need(type(steam_paths) is dict and set(steam_paths)==set(STEAM_HASHES),'Exact Steam paths required')
    for name,path in steam_paths.items():need(_path(path).name==name,'Steam basename differs')
    need(meta['target_player']['force']==n['force_id'],'Invitation force differs')
    settings=meta['rules'];need(settings==rules(settings.get('native_income_key5'),settings.get('native_world_option8')),
        'Unsupported native rules')
    need(n['profile'].get('game_sha256')==GAME_SHA and n['profile'].get('rules_sha256')==digest(settings),
        'Local game/rules differ from invitation')
    need(type(wait_seconds) is int and 1<=wait_seconds<=1800 and
         type(native_timeout) is int and 30<=native_timeout<=1800,'Bounded timeouts required')
    need(_path(target).name=='svdexccSC03.s14','Exact CC03 target required')
    need(type(keys) is dict and set(keys)=={'adapter','report','cut'},'Three local key paths required')
    for path in keys.values():_path(path)
    v=dict(pid=meta['pid'],birth=meta['birth'],target=str(target),initial_target=deepcopy(target_identity),
        initial_node=deepcopy(meta['node']),source_player=deepcopy(meta['source_player']),
        target_player=deepcopy(meta['target_player']),adapter_key_path=str(keys['adapter']),
        steam_paths=deepcopy(steam_paths),rules=deepcopy(settings),wait_seconds=wait_seconds,native_timeout=native_timeout)
    make_profile(v,target_identity,meta['node'],meta['node'],1)
    return dict(schema=SCHEMA,network=n,local=v,window=deepcopy(window),
        report_key_path=str(keys['report']),cut_key_path=str(keys['cut']))


def capture_local(*,pid,game_dir,target,invitation,adapter_key_path,report_key_path,cut_key_path,
                  target_ruler=None,target_district=None,_io=None):
    """Finite one-attempt capture. _io exists only for explicit owned tests."""
    need(type(pid) is int and 0<pid<2**32,'Explicit PID within Win32 range required')
    for value,high in ((target_ruler,5999),(target_district,51)):
        need(value is None or type(value) is int and 1<=value<=high,'Invalid expected target identity')
    game_dir=_path(game_dir);target=_path(target)
    need(target.name=='svdexccSC03.s14','Exact existing CC03 target required')
    keys={k:_path(v) for k,v in dict(adapter=adapter_key_path,report=report_key_path,cut=cut_key_path).items()}
    from observed_room_service import validate_invitation
    from b_observed_start import make_profile
    from human_rules_activation_room import GAME_SHA
    n=validate_invitation(invitation);io=_io or ReadOnlyIO()
    fingerprints=io.keys(keys);need(len(set(fingerprints.values()))==3,'Three independent key contents required')
    before=io.file(target);r=io.open(pid)
    try:
        need(r.pid==pid and r.sha256==GAME_SHA and r.memory.path.parent.resolve()==game_dir.resolve(),
             'Current process does not match supplied game directory/build')
        first=io.metadata(r,n['force_id']);birth=first['birth']
        need(first['pid']==pid and io.birth(r)==birth,'Initial incarnation mismatch')
        for key,value in (('ruler',target_ruler),('district',target_district)):
            need(value is None or first['target_player'][key]==value,'Target '+key+' differs from expectation')
        v=dict(source_player=first['source_player'],target_player=first['target_player'])
        p=make_profile(v,before,first['node'],first['node'],1)
        sample=io.planning(r,p,birth);original=io.original(r,birth)
        window=io.window(r);steam=io.steam(r)
        second=io.metadata(r,n['force_id'])
        need(first==second and sample['root']==first['root'] and sample['world']==first['world'] and
             sample['states']==[a for _,a in first['states']] and sample['base']==first['base'],
             'Complete local observations changed')
        need(io.window(r)==window and io.birth(r)==birth and io.file(target)==before and io.steam(r)==steam,
             'Window/process/CC03/storage changed during capture')
        io.original(r,birth)
        config=assemble(n,first,target,before,keys,window,steam)
        raw=json.dumps(sample,sort_keys=True,separators=(',',':')).encode()
        return dict(config=config,evidence=dict(result='READ_ONLY_LOCAL_CONFIGURATION',pid=pid,birth=birth,
            sample_sha256=hashlib.sha256(raw).hexdigest(),original_rules=original,key_fingerprints=fingerprints,
            finite_equal_samples=True,atomic_snapshot=False,input_exclusion_proven=False,
            scheduler_fence_proven=False,install_permission=False,native_calls=0,game_writes=0,
            fresh_execute_checks_required=True))
    finally:r.close()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group()
    m.add_argument('--template',action='store_true');m.add_argument('--capture',action='store_true')
    p.add_argument('--pid',type=int)
    for name in ('game-dir','target','invitation','adapter-key','report-key','cut-key','output'):p.add_argument('--'+name,type=Path)
    p.add_argument('--target-ruler',type=int);p.add_argument('--target-district',type=int);a=p.parse_args(argv)
    if a.template:print(json.dumps(template(),indent=2));return 0
    if not a.capture:p.print_help();return 0
    if any(getattr(a,k) is None for k in ('pid','game_dir','target','invitation','adapter_key','report_key','cut_key','output')):
        p.error('All local capture paths and explicit PID are required')
    try:
        output=_path(a.output);need(not output.exists(),'Refusing to overwrite local configuration')
        value=capture_local(pid=a.pid,game_dir=a.game_dir,target=a.target,
            invitation=json.loads(a.invitation.read_text(encoding='utf-8-sig')),adapter_key_path=a.adapter_key,
            report_key_path=a.report_key,cut_key_path=a.cut_key,target_ruler=a.target_ruler,target_district=a.target_district)
        raw=(json.dumps(value['config'],ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        with output.open('xb') as stream:stream.write(raw);stream.flush()
        print(json.dumps(dict(**value['evidence'],config_path=str(output),config_sha256=hashlib.sha256(raw).hexdigest())))
        return 0
    except Exception as exc:
        # Never echo invitations, raw arbitrary errors or secret key material.
        print(json.dumps(dict(result='LOCAL_SETUP_REFUSED',error_type=type(exc).__name__,install_permission=False)))
        return 1


if __name__=='__main__':raise SystemExit(main())
