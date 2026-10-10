"""Owned memory and temporary-file tests only; no game/Steam/process access."""
from copy import deepcopy
from datetime import datetime
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_guest_local_setup as setup
import b_warm_profile_capture_test as memory
import b_warm_profile_capture as capture
from authoritative_sync import digest
from human_rules_activation_room import rules,GAME_SHA
import b_observed_start as startup


class OwnedIO(setup.ReadOnlyIO):
    def __init__(self,folder):
        self.folder=folder;self.reader=memory.Reader();r=self.reader
        r.memory.path=folder/'SAN14PK_SC.exe';r.snapshot=lambda:r.context()['snapshot']
        r.memory.put(r.memory.base+0x1fd0c5c,1,'<i');r.closed=False
        r.close=lambda:setattr(r,'closed',True)
        self.opens=0;self.meta_count=0;self.fault=None
        self.target=folder/'svdexccSC03.s14';self.target.write_bytes(b'owned non-save fixture')

    def open(self,pid):self.opens+=1;return self.reader
    def keys(self,paths):return {k:hashlib.sha256(k.encode()).hexdigest() for k in paths}
    def file(self,path):
        raw=path.read_bytes()
        return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),file_id=[1,0,9,0,len(raw),0,2])
    def birth(self,r):return r.birth
    def actor(self,r,force):
        return dict(viewer_force_id=r.profile.currentForce,date=r.snapshot()['date'],ruler_id=666 if force==12 else 952,
                    main_district_id=11 if force==12 else 2,context_sha256=hashlib.sha256(str(force).encode()).hexdigest())
    def metadata(self,r,force):
        self.meta_count+=1
        if self.meta_count==2:
            if self.fault=='birth':r.birth+=1
            if self.fault=='world':r.memory.put(r.root+0x85130,r.world+8);r.types[r.world+8]='CWorldData'
        with patch('authority_reward.capture_context',self.actor):
            return super().metadata(r,force)
    def planning(self,r,p,birth):
        r.profile=p
        if self.fault=='hook':r.memory.put(r.memory.base+capture.SLOTS[0][0],0x77770000)
        return capture.capture_planning(r,p,p.source.ruler,context_reader=lambda r:r.context(),
                birth_reader=lambda r:r.birth,range_check=lambda r,a,n:r.memory.span(a,n))
    def original(self,r,birth):
        if self.fault=='rules':raise ValueError('owned rules source changed')
        return dict(six_sources_original=True)
    def window(self,r):return dict(handle=0x123456789,thread=9,timeout_ms=1000)
    def steam(self,r):return {n:str(self.folder/n) for n in ('steam_api64.dll','steamclient64.dll')}


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name).resolve();self.io=OwnedIO(self.folder)
        self.invitation=dict(schema='san14.observed-pilot-invitation.v1',host='127.0.0.1',control_port=1234,
            download_port=1235,fingerprint='a'*64,credential='OWNED_TEST_CREDENTIAL',force_id=2,
            profile=dict(game_sha256=GAME_SHA,rules_sha256=digest(rules(0,0))))
        self.kw=dict(pid=1234,game_dir=self.folder,target=self.io.target,invitation=self.invitation,
            adapter_key_path=self.folder/'adapter.key',report_key_path=self.folder/'report.key',
            cut_key_path=self.folder/'cut.key',_io=self.io)

    def test_capture_real_planning_algorithm_and_exact_local_schema(self):
        result=setup.capture_local(**self.kw);c=result['config'];v=c['local']
        self.assertEqual(v['source_player'],dict(force=12,ruler=666,district=11))
        self.assertEqual(v['target_player'],dict(force=2,ruler=952,district=2))
        self.assertEqual(v['initial_node'],dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY'))
        self.assertEqual(set(v),startup.LOCAL_KEYS-{'pair_build','helper_build','rules_build','source_manifest','records'})
        self.assertEqual(set(c),{'schema','network','local','window','report_key_path','cut_key_path'})
        # The actual frozen startup validator accepts the assembled local fields
        # once the portable entry contributes its distribution-only fields.
        full=deepcopy(v)
        for name in ('pair_build','helper_build','source_manifest'):
            full[name]=dict(path=str(self.folder/(name+'.json')),sha256='a'*64)
        full['records']=str(self.folder/'new-records')
        full['rules_build']=dict(stage=str(self.folder/'production.dll'),publisher=str(self.folder/'publisher.exe'))
        startup.validate_config(dict(schema=startup.SCHEMA,network=c['network'],local=full))
        self.assertTrue(self.io.reader.closed);self.assertFalse(result['evidence']['install_permission'])
        self.assertNotIn('OWNED_TEST_CREDENTIAL',json.dumps(result['evidence']))

    def test_original_hook_and_rules_refuse_and_close(self):
        for fault in ('hook','rules'):
            with self.subTest(fault=fault):
                x=OwnedIO(self.folder);x.fault=fault
                with self.assertRaises(ValueError):setup.capture_local(**dict(self.kw,_io=x))
                self.assertTrue(x.reader.closed)

    def test_birth_and_world_drift_refuse(self):
        for fault in ('birth','world'):
            with self.subTest(fault=fault):
                x=OwnedIO(self.folder);x.fault=fault
                with self.assertRaisesRegex(ValueError,'observations changed'):setup.capture_local(**dict(self.kw,_io=x))
                self.assertTrue(x.reader.closed)

    def test_invitation_rules_and_target_identity_refuse(self):
        with self.assertRaisesRegex(ValueError,'Target ruler'):setup.capture_local(**self.kw,target_ruler=1)
        x=OwnedIO(self.folder);n=deepcopy(self.invitation);n['profile']['rules_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'differ from invitation'):setup.capture_local(**dict(self.kw,_io=x,invitation=n))

    def test_cc03_changes_refuse(self):
        original=self.io.file;count=0
        def file(path):
            nonlocal count
            count+=1
            if count==2:path.write_bytes(b'owned changed fixture')
            return original(path)
        self.io.file=file
        with self.assertRaisesRegex(ValueError,'CC03/storage changed'):setup.capture_local(**self.kw)

    def test_pid_truncation_and_wrong_target_refuse_before_open(self):
        for pid in (True,0,2**32):
            with self.assertRaises(ValueError):setup.capture_local(**dict(self.kw,pid=pid))
        with self.assertRaises(ValueError):setup.capture_local(**dict(self.kw,target=self.folder/'other.s14'))
        self.assertEqual(self.io.opens,0)

    def test_duplicate_keys_refuse_before_open(self):
        self.io.keys=lambda paths:{k:'a'*64 for k in paths}
        with self.assertRaisesRegex(ValueError,'independent'):setup.capture_local(**self.kw)
        self.assertEqual(self.io.opens,0)

    def test_help_and_template_have_no_capture_or_file_calls(self):
        with patch.object(setup,'capture_local',side_effect=AssertionError('capture forbidden')):
            for argv in ([],['--template']):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(setup.main(argv),0)
                self.assertNotIn('OWNED_TEST_CREDENTIAL',output.getvalue())

    def test_cli_writes_exact_config_exclusively_and_does_not_print_credential(self):
        value=setup.capture_local(**self.kw)
        invite=self.folder/'invitation.json';invite.write_text(json.dumps(self.invitation))
        output=self.folder/'local.json'
        argv=['--capture','--pid','1234','--game-dir',str(self.folder),'--target',str(self.io.target),
            '--invitation',str(invite),'--adapter-key',str(self.kw['adapter_key_path']),
            '--report-key',str(self.kw['report_key_path']),'--cut-key',str(self.kw['cut_key_path']),
            '--output',str(output)]
        with patch.object(setup,'capture_local',return_value=value) as call:
            text=io.StringIO()
            with contextlib.redirect_stdout(text):self.assertEqual(setup.main(argv),0)
            self.assertEqual(json.loads(output.read_text()),value['config'])
            self.assertNotIn('OWNED_TEST_CREDENTIAL',text.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(setup.main(argv),1)
            self.assertEqual(call.call_count,1)


if __name__=='__main__':
    out=PRIVATE/'b_guest_local_setup_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    paths={Path(m.__file__).resolve() for m in sys.modules.values() if getattr(m,'__file__',None) and
           Path(m.__file__).resolve().is_relative_to(ROOT)}|{Path(__file__).resolve()}
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    stable=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    for m in list(sys.modules.values()):
        if getattr(m,'__file__',None):
            p=Path(m.__file__).resolve()
            if p.is_relative_to(ROOT):before.setdefault(str(p),hashlib.sha256(p.read_bytes()).hexdigest())
    (out/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    result=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=before,
        sources_unchanged=stable,game_access=False,steam_access=False,process_opened=False,
        sampling='original complete planning sampler on owned byte memory; actor contexts, Win32 window/storage/original-rules are explicit doubles',
        production_capture_executed=False,failures=[(str(t),s) for t,s in r.errors+r.failures],
        artifacts={str(out/'test.log'):hashlib.sha256((out/'test.log').read_bytes()).hexdigest()})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(out/'result.json');raise SystemExit(result['result']!='PASS')
