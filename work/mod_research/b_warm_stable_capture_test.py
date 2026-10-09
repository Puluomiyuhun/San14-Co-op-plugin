"""Actual frozen two-sample algorithm on explicit fake RAM; no process access."""
from datetime import datetime
from pathlib import Path
import hashlib
import io
import json
import sys
import unittest
from unittest.mock import patch

import b_warm_stable_capture as stable
import b_warm_profile_capture as original
from b_warm_profile_capture_test import Reader

HERE=Path(__file__).resolve().parent;PRIVATE=HERE.parents[2]/'mod_research'
OUTPUT=None
FROZEN_CAPTURE=original.capture_planning


class Clock:
    def __init__(self):self.now=0.0
    def monotonic(self):return self.now
    def sleep(self,n):self.now+=n


class Cases(unittest.TestCase):
    def setUp(self):self.reader=Reader();self.evidence={};self.context_calls=0
    def run_capture(self,context=None,**kwargs):
        def capture(r,p,ruler):
            return FROZEN_CAPTURE(r,p,ruler,context_reader=context or (lambda r:r.context()),
                birth_reader=lambda r:r.birth,range_check=lambda r,a,n:r.memory.span(a,n))
        with patch.object(original,'capture_planning',side_effect=capture):
            return stable.capture_planning(self.reader,self.reader.profile,self.reader.ruler,
                expected_birth=1234567,birth_reader=lambda r:r.birth,evidence=self.evidence,interval=0,**kwargs)
    def tearDown(self):
        (OUTPUT/(self._testMethodName+'.json')).write_text(json.dumps(self.evidence,indent=2)+'\n')

    def test_transient_current_field_requires_new_two_complete_samples(self):
        def context(r):
            self.context_calls+=1
            if self.context_calls==2:r.memory.put(r.memory.base+0x19e7310+0x48,r.states[4])
            return r.context()
        result=self.run_capture(context)
        self.assertEqual(self.context_calls,4);self.assertEqual(self.evidence['accepted_attempt'],2)
        self.assertEqual(result['current'],self.reader.states[4]);self.assertFalse(result['atomic_snapshot'])
        self.assertEqual(self.evidence['attempts'][0]['error'],stable.RETRYABLE)

    def test_unstable_all_attempts_refuse_without_erasing_field(self):
        def context(r):
            self.context_calls+=1;r.memory.put(r.states[4]+0x50,self.context_calls*8);return r.context()
        with self.assertRaisesRegex(ValueError,'attempt limit'):self.run_capture(context,max_attempts=3)
        self.assertEqual(self.context_calls,6);self.assertEqual(len(self.evidence['attempts']),3)
        self.assertTrue(all(r['retryable_two_sample_mismatch'] for r in self.evidence['attempts']))

    def test_wrong_date_no_retry(self):
        def context(r):
            self.context_calls+=1;value=r.context();value['snapshot']['date']['day']=21;return value
        with self.assertRaisesRegex(ValueError,'Current date differs'):self.run_capture(context)
        self.assertEqual(self.context_calls,1);self.assertEqual(len(self.evidence['attempts']),1)

    def test_birth_change_inside_old_capture_is_not_transient(self):
        def context(r):
            self.context_calls+=1
            if self.context_calls==2:r.birth+=1
            return r.context()
        with self.assertRaisesRegex(ValueError,'attachment/profile identity changed'):self.run_capture(context)
        self.assertEqual(self.context_calls,2);self.assertEqual(len(self.evidence['attempts']),1)
        self.assertEqual(self.evidence['attempts'][0]['error'],stable.RETRYABLE)

    def test_fixed_expected_birth_mismatch_refuses_before_old_sampler(self):
        self.reader.birth+=1
        with patch.object(original,'capture_planning',side_effect=AssertionError('must not sample')) as sampler:
            with self.assertRaisesRegex(ValueError,'attachment/profile identity changed'):
                stable.capture_planning(self.reader,self.reader.profile,self.reader.ruler,expected_birth=1234567,
                    birth_reader=lambda r:r.birth,evidence=self.evidence)
            sampler.assert_not_called()

    def test_budget_expiry_during_unstable_sample_does_not_retry(self):
        clock=Clock()
        def context(r):
            self.context_calls+=1;clock.now+=0.2;r.memory.put(r.states[4]+0x50,self.context_calls*8);return r.context()
        with patch.object(stable.time,'monotonic',clock.monotonic),patch.object(stable.time,'sleep',clock.sleep):
            with self.assertRaisesRegex(ValueError,'deadline'):self.run_capture(context,timeout=.3)
        self.assertEqual(self.context_calls,2);self.assertEqual(len(self.evidence['attempts']),1)

    def test_budget_expiry_after_equal_sample_still_refuses(self):
        clock=Clock()
        def context(r):self.context_calls+=1;clock.now+=0.2;return r.context()
        with patch.object(stable.time,'monotonic',clock.monotonic),patch.object(stable.time,'sleep',clock.sleep):
            with self.assertRaisesRegex(ValueError,'deadline'):self.run_capture(context,timeout=.3)
        self.assertEqual(self.evidence['attempts'][0]['outcome'],'REJECTED_AFTER_SAMPLE')

    def test_similar_or_subclass_error_does_not_retry(self):
        class Other(ValueError):pass
        for exc in (ValueError(stable.RETRYABLE+'!'),Other(stable.RETRYABLE)):
            e={}
            with patch.object(original,'capture_planning',side_effect=exc) as sampler:
                with self.assertRaises(type(exc)):
                    stable.capture_planning(self.reader,self.reader.profile,self.reader.ruler,expected_birth=1234567,
                        birth_reader=lambda r:r.birth,evidence=e)
                self.assertEqual(sampler.call_count,1)
        self.evidence=e


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    global OUTPUT
    OUTPUT=PRIVATE/'b_warm_stable_capture_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    names={Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,'__file__',None)
        and str(Path(m.__file__).resolve()).startswith(str(HERE)) and str(m.__file__).endswith('.py')}
    names.add(Path(__file__).resolve());pins={str(p):sha(p) for p in names}
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'tests.log').write_text(stream.getvalue());unchanged=all(sha(p)==h for p,h in pins.items())
    report=dict(result='PASS' if result.wasSuccessful() and unchanged else 'FAIL',tests=result.testsRun,
        sources=pins,inputs_unchanged=unchanged,game_process_access=False,native_calls=0,
        original_complete_sampler_executed=True,memory_reader_is_explicit_double=True,
        artifacts={str(p):sha(p) for p in OUTPUT.iterdir() if p.is_file()})
    path=OUTPUT/'result.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(stream.getvalue());print(json.dumps(dict(result=report['result'],path=str(path),sha256=sha(path))))
    return report['result']!='PASS'

if __name__=='__main__':raise SystemExit(main())
