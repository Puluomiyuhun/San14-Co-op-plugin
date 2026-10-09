"""Real TLS/separate B process tests; native Save/load/RAM/fence are doubles."""
from datetime import datetime
from pathlib import Path
import base64
import hashlib
import io
import json
import sys
import unittest
from unittest.mock import patch
import b_warm_remote_completion_test as prior
from b_warm_settled_completion import SettledRemoteCompletionRoom
from b_warm_remote_completion_test import (sha, put_date, incompressible_tables, Profile,
    Date, Identity, next_node, run_model, host_observation, model_artifact)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'


class Cases(prior.Cases):
    def setUp(self):
        with patch.object(prior, 'RemoteCompletionRoom', SettledRemoteCompletionRoom):
            super().setUp()

    def one(self, generation, mode='normal', *, before_mode=None):
        node = next_node(self.c.node); put_date(self.host_reader,node)
        if mode == 'incompressible': incompressible_tables(self.host_reader)
        data = ('explicit Save double '+str(generation)).encode()*3000
        p=Profile(); p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=len(data);p.file.sha256[:]=bytes.fromhex(sha(data))
        p.before=Date(*(self.c.node[k] for k in ('year','month','day')));p.loaded=Date(*(node[k] for k in ('year','month','day')))
        p.source=Identity(666,12,11);p.target=Identity(952,2,2);p.currentForce=12 if generation==1 else 2
        if generation > 1: p.before=Date(*(node[k] for k in ('year','month','day')))
        if before_mode == 'old': p.before=Date(*(self.c.node[k] for k in ('year','month','day')))
        if before_mode == 'future': p.before=Date(*(next_node(node)[k] for k in ('year','month','day')))
        if before_mode == 'target': p.before=Date(*(node[k] for k in ('year','month','day')))
        self.host_key=sha(('A actual receipt model '+str(generation)).encode())
        run_model(self.c)
        observe=lambda:host_observation(self.c,reader=self.host_reader,read_birth=lambda:1001,verify_held=lambda:True,source_ruler=666)
        reserved=self.binding.reserve(generation,f'mp{generation:08d}.s14',observe())
        self.artifacts[generation]=model_artifact(reserved.request,generation,data=data)
        package=self.binding.publish(generation,observe)
        context=dict(scope=self.c.scope,manifest=package.manifest,checkpoint_id=package.checkpoint_id,attachments=self.c.attachments.copy())
        result=self.b.send(dict(op='run',profile=base64.b64encode(bytes(p)).decode(),context=context,bootstrap=generation==1,
            download=self.download,fingerprint=self.fp,directory=str(self.folder/f'received-{generation}'),mode=mode))
        return result, package

    def refused(self, generation, mode):
        before = self.b.send(dict(op='request', packet={'action':'warm_rules_binding'}))
        self.assertTrue(before['ok'])
        r,_ = self.one(generation,before_mode=mode)
        self.assertFalse(r['ok'],r)
        self.assertEqual(r['loads'],generation-1)
        self.assertIsNone(self.c.load_intent)
        self.assertFalse(r['retry_succeeded'])
        self.assertEqual(self.c.period,generation)
        prior.EVIDENCE.append(dict(case='wrong-pre-load-date',generation=generation,mode=mode,result=r))

    def test_ordinary_old_date_refused(self):
        self.assertTrue(self.one(1)[0]['ok'])
        self.refused(2,'old')

    def test_ordinary_future_date_refused(self):
        self.assertTrue(self.one(1)[0]['ok'])
        self.refused(2,'future')

    def test_bootstrap_still_requires_initial_date(self):
        self.refused(1,'target')


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    folder=PRIVATE/'b_warm_settled_completion_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    prior.transport.OUTPUT=folder;before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (folder/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    stable=all(sources.get(k)==v for k,v in before.items())
    report=dict(result='PASS' if result.wasSuccessful() and result.testsRun==8 and stable else 'FAIL',tests=result.testsRun,
        sources=sources,inputs_unchanged=stable,cases=prior.EVIDENCE,actual_tls=True,independent_guest_process=True,
        game_access=False,native_save_load=False,fake_reader=True,fake_boundary=True,
        date_contract='bootstrap old date; ordinary target date',
        failures=[(str(t),detail) for t,detail in result.failures+result.errors])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(folder/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
