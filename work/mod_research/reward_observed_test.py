"""Actual GameReader/capture_context bytes + existing TLS/SQLite reward queue.

All process memory, RTTI and reward business writes are owned fixtures. No game,
menu, native submission ABI or observed save/load Room is launched here.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import threading
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
from reward_observed_fixture import World
from reward_observed_context import reward,CONTRACT
from reward_observed_flow import ObservedRewardFlow,GuestConsumer,CAPABILITIES
from reward_room_flow import Replica,FlowServer,envelope
from room_session import Room
from room_transport import Client,make_certificate
import execution_journal as journal

OUTPUT=None;ROWS=[]


class Harness:
    def __init__(self,folder):
        self.folder=folder;folder.mkdir();self.worlds={p:World(f) for p,f in (('A',12),('B',2))}
        self.ports={p:w.port() for p,w in self.worlds.items()};self.key=secrets.token_bytes(32)
        manifest=dict(profile=dict(protocol='san14.room.v1',game_sha256=reward.SUPPORTED_SHA256,
            adapter_contract='research-no-native-room-adapter.v1',checkpoint_sha256='c'*64,rules_sha256='d'*64),
            forces=[dict(id=12,name='Owned A',main_district_id=11),dict(id=2,name='Owned B',main_district_id=2)],
            source=dict(kind='OWNED_BYTE_LAYOUT'))
        self.room=Room(manifest);cert,key,fp=make_certificate(folder/'tls')
        self.server=FlowServer(('127.0.0.1',0),self.room,cert,key)
        self.thread=threading.Thread(target=lambda:self.server.serve_forever(poll_interval=.02));self.thread.start()
        self.clients={p:Client('127.0.0.1',self.server.server_address[1],fp,
            dict(method=method,credential=token,profile=manifest['profile'])) for p,method,token in
            (('A','host',self.room.host_token),('B','join',self.room.invite))}
        for p,force in (('A',12),('B',2)):
            self.request(p,dict(action='select_force',force_id=force,request_id=secrets.token_hex(16),expected_revision=self.room.revision))
        for p in ('A','B'):
            self.request(p,dict(action='confirm_force',request_id=secrets.token_hex(16),expected_revision=self.room.revision))
        self.flow=ObservedRewardFlow(folder/'queue',self.room,self.ports['A'],self.ports['B'].attachment_id,
             dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY'),guest_report_key=self.key)
        self.server.flow=self.flow
        self.replica=Replica(folder/'guest.sqlite',self.flow.scope,'B',self.ports['B'])
        self.consumer=GuestConsumer(self.clients['B'],self.replica,self.key);self.consumer.report()

    def request(self,p,value):
        r=self.clients[p].request(value)
        if not r.get('ok'):raise ValueError(str(r))
        return r
    def packet(self,p):
        return envelope(self.flow.scope,'reward_submit',request_id=secrets.token_hex(16),
                        district_id=11 if p=='A' else 2,officer_ids=[97] if p=='A' else [101])
    def close(self):
        for c in self.clients.values():c.close()
        self.server.shutdown();self.thread.join(timeout=5);self.server.server_close()
        assert not self.thread.is_alive()


class Cases(unittest.TestCase):
    def setup_h(self,suffix=''):
        h=Harness(OUTPUT/(self._testMethodName+suffix));self.addCleanup(h.close);return h

    def test_both_players_same_queue_real_context_and_effect_projection(self):
        h=self.setup_h();packets={p:h.packet(p) for p in ('A','B')}
        with ThreadPoolExecutor(2) as pool:
            submitted=list(pool.map(lambda p:h.request(p,packets[p]),('A','B')))
        self.assertEqual(sorted(r['ordinal'] for r in submitted),[1,2])
        for n in (1,2):
            self.assertEqual(h.flow.pump_one()['sequence'],n)
            self.assertEqual(h.flow.pump_one()['status'],'WAITING_GUEST_APPLICATION')
            intent=h.request('B',envelope(h.flow.scope,'reward_next'))['intent']
            result=h.consumer.consume_one();self.assertEqual(result['receipt']['sequence'],n)
            duplicate=h.replica.apply(intent);self.assertTrue(duplicate['duplicate'])
            self.assertFalse(duplicate['native_invoked']);self.assertEqual(h.worlds['B'].calls,n)
        self.assertEqual(h.ports['A'].observe(),h.ports['B'].observe())
        self.assertEqual([w.calls for w in h.worlds.values()],[2,2])
        for p in ('A','B'):
            self.assertTrue(h.request(p,packets[p])['duplicate'])
            self.assertFalse(h.clients[p].request(envelope(h.flow.scope,'reward_ready',value=True))['ok'])
        with self.assertRaisesRegex(ValueError,'Ready'):h.flow.seal()
        state=h.ports['A'].sampler.capture()[1]
        self.assertEqual([p['loyalty'] for p in state['persons'] if p['id'] in (97,101)],[84,74])
        self.assertEqual([d['action_points'] for d in state['districts']],[9,9])
        self.assertEqual([c['gold'] for c in state['cities']],[20704,83208])
        ROWS.append(dict(case=self._testMethodName,state=state,host_receipts=h.ports['A'].receipts,
                         reports={'A':h.flow.host.report(),'B':h.replica.report()},duplicate_native_calls=0))

    def test_wrong_cost_or_unselected_mutation_hold_without_replay(self):
        for fault in ('wrong-cost','unselected','after-write'):
            with self.subTest(fault=fault):
                h=self.setup_h('-'+fault);h.worlds['A'].failure=fault;h.request('A',h.packet('A'))
                with self.assertRaises(journal.ExecutionHeld):h.flow.pump_one()
                self.assertEqual(h.worlds['A'].calls,1);self.assertEqual(h.worlds['B'].calls,0)
                with self.assertRaises(Exception):h.flow.pump_one()
                self.assertEqual(h.worlds['A'].calls,1);self.assertIsNotNone(h.ports['A'].sampler.failed)
                ROWS.append(dict(case=self._testMethodName,fault=fault,native_calls=1,
                                 journal=h.flow.host.journal.status()))

    def test_date_attachment_and_process_drift_retire_permanently(self):
        for fault in ('date','attachment','birth','world'):
            with self.subTest(fault=fault):
                w=World(12);port=w.port();before=port.observe()
                if fault=='date':w.memory.pack(w.world+0x37,'<B',21)
                elif fault=='attachment':w.attachment='c'*32
                elif fault=='birth':w.birth+=1
                else:w.memory.pack(w.root+0x85130,'<Q',w.world+0x100)
                with self.assertRaises(Exception):port.observe()
                w.memory.pack(w.world+0x37,'<B',11);w.attachment='a'*32;w.birth=70012
                w.memory.pack(w.root+0x85130,'<Q',w.world)
                with self.assertRaisesRegex(ValueError,'retired'):port.observe()
                self.assertEqual(w.calls,0)
                ROWS.append(dict(case=self._testMethodName,fault=fault,native_calls=0,old_projection=before))

    def test_ineligible_cap_and_resources_reject_before_native(self):
        for fault in ('loyalty100','gold','action'):
            with self.subTest(fault=fault):
                w=World(12)
                if fault=='loyalty100':w.memory.pack(w.people[97]+0x120,'<B',100)
                elif fault=='gold':w.memory.pack(w.cities[19]+0x34,'<I',99)
                else:w.memory.pack(w.districts[11]+0x14,'<B',0)
                p=w.port();context=p.context(12);command=reward.make_command(context,11,[97])
                with self.assertRaises(reward.PreflightError):p.execute(command)
                self.assertEqual(w.calls,0)
                ROWS.append(dict(case=self._testMethodName,fault=fault,native_calls=0))

    def test_lost_guest_ack_preserves_applied_journal_no_reexecute(self):
        h=self.setup_h();h.request('A',h.packet('A'));h.flow.pump_one();real=h.clients['B'].request
        def lost(value):
            r=real(value)
            if value.get('action')=='reward_report':raise EOFError('Owned report reply lost')
            return r
        h.clients['B'].request=lost
        with self.assertRaises(EOFError):h.consumer.consume_one()
        self.assertEqual(h.worlds['B'].calls,1);self.assertEqual(h.replica.journal.status()['sequence'],1)
        with self.assertRaisesRegex(ValueError,'terminal'):h.consumer.consume_one()
        self.assertEqual(h.worlds['B'].calls,1)
        ROWS.append(dict(case=self._testMethodName,guest_native_calls=1,journal=h.replica.journal.status()))

    def test_unknown_task_and_short_read_refuse_context(self):
        for fault in ('task','short-read'):
            w=World(12);port=w.port()
            if fault=='task':
                manager=w.reader.pointer(w.root+0x85128);w.memory.pack(manager+0x10,'<Q',w.memory.base+1)
            else:
                read=w.memory.read
                w.memory.read=lambda a,n:read(a,n)[:-1] if a==w.people[97]+0x10 and n==0x188 else read(a,n)
            with self.assertRaises(Exception):port.observe()
            self.assertEqual(w.calls,0)
        ROWS.append(dict(case=self._testMethodName,unknown_native_shape_rejected=True,native_calls=0))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'reward_observed_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();stream=io.StringIO();tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    report=dict(result='PASS' if tests.wasSuccessful() and sources==before else 'FAIL',tests=tests.testsRun,
        sources=sources,inputs_unchanged=sources==before,cases=ROWS,capabilities=dict(CAPABILITIES),
        actual_game_reader_and_reward_capture=True,actual_TLS_and_SQLite=True,native_business_RTTI_memory_doubles=True,
        game_access=False,observed_save_room_integrated=False,
        failures=[(str(t),d) for t,d in tests.errors+tests.failures])
    report['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
