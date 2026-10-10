"""Read actual three-slot build closure; reject stale identity without game access."""
from datetime import datetime
import copy,io,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import patch
import a_save_three_build_approval as approval
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
RUN=None;OUT=None

class Cases(unittest.TestCase):
    def setUp(self):
        self.record=json.loads((RUN/'result.json').read_text())
        self.args=N(build_run=RUN,publisher_build=Path(self.record['publisher']['path']).parent,
            repeat_abi_run=Path(self.record['repeat_abi_checks']['path']).parent)
    def test_actual_complete_build_package(self):
        result,abi,pub=approval.verify_native_build(self.args)
        self.assertEqual(result['production']['binaries']['a_save_local_runtime.dll'],self.record['production_dll']['sha256'])
        self.assertEqual(pub['binaries']['publisher.exe'],self.record['publisher']['sha256'])
        self.assertTrue(abi.is_dir())
    def test_legacy_magic_capacity_and_missing_source_rejected(self):
        original=approval._read
        for field,value in (('abi_magic',0x31585241),('capacity',2),('schema','legacy')):
            bad=copy.deepcopy(self.record);bad[field]=value
            with self.subTest(field=field),patch.object(approval,'_read',side_effect=lambda p:bad if Path(p)==RUN/'result.json' else original(p)):
                with self.assertRaises(RuntimeError):approval.verify_native_build(self.args)
        bad=copy.deepcopy(self.record);bad['sources'].pop(str(P/'a_native_turn_runtime.cpp'))
        with patch.object(approval,'_read',side_effect=lambda p:bad if Path(p)==RUN/'result.json' else original(p)):
            with self.assertRaisesRegex(RuntimeError,'Missing production source'):approval.verify_native_build(self.args)
    def test_third_slot_layout_and_wrong_publisher_folder_rejected(self):
        schema=json.loads(Path(self.record['schema_snapshot']['path']).read_text());schema['structures']['Snapshot']['fields']['mailboxStates']['size']=8
        with self.assertRaises(RuntimeError):approval._schema(schema,approval.wire.TYPES)
        self.args.publisher_build=RUN
        with self.assertRaisesRegex(RuntimeError,'publisher folder'):approval.verify_native_build(self.args)

def main():
    global RUN,OUT
    RUN=Path(sys.argv[1]).resolve(strict=True);OUT=PRIVATE/'a_save_three_build_approval_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUT.mkdir(parents=True)
    files=[Path(__file__),Path(approval.__file__),Path(approval.wire.__file__),Path(approval.repeat.__file__)]
    pins={str(p):approval.sha(p) for p in files};log=io.StringIO();r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUT/'tests.log').write_text(log.getvalue(),encoding='utf-8');stable=all(approval.sha(p)==h for p,h in pins.items())
    value=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=pins,inputs_unchanged=stable,game_access=False,
        actual_production_bundle=dict(path=str(RUN/'result.json'),sha256=approval.sha(RUN/'result.json')),artifacts={str(OUT/'tests.log'):approval.sha(OUT/'tests.log')})
    path=OUT/'result.json';path.write_text(json.dumps(value,indent=2)+'\n');print(log.getvalue());print(json.dumps(dict(result=value['result'],path=str(path),sha256=approval.sha(path))))
    return int(value['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
