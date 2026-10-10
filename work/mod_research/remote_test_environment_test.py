"""Owned memory and missing-dependency cases; no game, sockets or installation."""
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import contextlib,hashlib,io,json,sys,unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path.insert(0,str(PRIVATE/'python_deps'))
import remote_test_environment as environment

ROWS=[]


class Cases(unittest.TestCase):
    def test_actual_B_no_crypto_import(self):
        actual=environment._module
        def load(name):
            self.assertFalse(name.startswith('cryptography'))
            return actual(name)
        with patch.object(environment,'_module',load):row=environment.check('B')
        self.assertEqual(row['result'],'PASS_ENVIRONMENT');self.assertEqual(len(row['checks']),5);ROWS.append(row)

    def test_actual_A_memory_certificate(self):
        row=environment.check('A');self.assertEqual(row['result'],'PASS_ENVIRONMENT')
        certificate=next(r for r in row['checks'] if r['name']=='certificate_signing')
        self.assertTrue(certificate['detail']['signature_verified']);self.assertFalse(certificate['detail']['key_exported']);ROWS.append(row)

    def test_missing_pefile_reports_failure_and_keeps_other_results(self):
        actual=environment._module
        def load(name):
            if name=='pefile':raise ModuleNotFoundError('sentinel-secret',name=name)
            return actual(name)
        with patch.object(environment,'_module',load):row=environment.check('B')
        self.assertEqual(row['result'],'ENVIRONMENT_NOT_READY')
        self.assertEqual([r['name'] for r in row['checks'] if not r['passed']],['pefile'])
        self.assertNotIn('sentinel-secret',json.dumps(row));ROWS.append(row)

    def test_missing_crypto_is_A_only(self):
        actual=environment._module
        def load(name):
            if name.startswith('cryptography'):raise ModuleNotFoundError('missing',name='cryptography')
            return actual(name)
        with patch.object(environment,'_module',load):a,b=environment.check('A'),environment.check('B')
        self.assertEqual(a['result'],'ENVIRONMENT_NOT_READY');self.assertEqual(b['result'],'PASS_ENVIRONMENT')
        self.assertEqual([r['name'] for r in a['checks'] if not r['passed']],['certificate_signing']);ROWS.extend([a,b])

    def test_unsupported_platform_rejected(self):
        for facts in (dict(platform='linux',python=[3,11,0],pointer_bits=64,implementation='cpython'),
                      dict(platform='win32',python=[3,10,9],pointer_bits=64,implementation='cpython'),
                      dict(platform='win32',python=[3,11,0],pointer_bits=32,implementation='cpython')):
            with patch.object(environment,'_facts',return_value=facts):row=environment.check('B')
            self.assertFalse(row['checks'][0]['passed']);self.assertEqual(row['result'],'ENVIRONMENT_NOT_READY');ROWS.append(row)

    def test_default_help_inert_and_invalid_role(self):
        with patch.object(environment,'check',side_effect=AssertionError('No checks on help')),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(environment.main([]),0)
        with self.assertRaises(ValueError):environment.check('both')


def main():
    folder=PRIVATE/'remote_test_environment_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    pins={str(p):sha(p) for p in (HERE/'remote_test_environment.py',Path(__file__).resolve())}
    output=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
    run=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    (folder/'test.log').write_text(output.getvalue(),encoding='utf-8')
    unchanged=all(sha(p)==h for p,h in pins.items())
    result=dict(result='PASS' if run.wasSuccessful() and unchanged else 'FAIL',tests=run.testsRun,
        sources=pins,inputs_unchanged=unchanged,cases=ROWS,game_access=False,network_opened=False,
        artifacts={'test.log':sha(folder/'test.log')})
    (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(result=result['result'],tests=run.testsRun,path=str(folder/'result.json'))))
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
