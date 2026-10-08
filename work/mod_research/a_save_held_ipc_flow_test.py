"""Observed native Ready remains held through actual pipe Save/Copy and TLS.

The native current-date primitive is tested separately from post-simulation
phase admission. Linked Room planning/save dates expose that remaining gap.
"""
import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import re
import secrets
import threading
import unittest

import a_save_ipc_flow_test as flow
import a_save_ipc_client as ipc
from checkpoint_planning_save_link import PlanningSaveLink
from checkpoint_fresh_save_binding_test import select_direct,run_model,CONTRACT
from authoritative_sync import PeriodCoordinator

HERE=Path(__file__).resolve().parent
EVIDENCE=[]


def validate_build(folder):
    raw=(folder/'result.json').read_bytes();r=flow.strict_json(raw)
    ipc.require(r.get('schema')=='san14.a-save-held-ipc-build.v1' and r.get('result')=='PASS'
        and r.get('sources_unchanged') is True and r.get('game_access') is False,'Invalid held-save build')
    names=r.get('sources');required={'a_save_held_ipc.cpp','a_save_held_ipc.h','a_save_held_ipc_fixture.cpp',
        'planning_checkpoint_save.cpp','planning_checkpoint_save_owner.cpp','planning_checkpoint_save_gate.cpp',
        'planning_checkpoint_save_interlock.cpp'}
    ipc.require(type(names) is dict and required<=set(names) and len(names)<=128,'Missing held-save sources')
    ipc.require(not {'planning_period_owner.cpp','planning_input_interlock_gate.cpp','a_save_ipc.cpp'}&set(names),
        'Frozen implementations cannot substitute held-save replacements')
    for n,h in names.items():
        ipc.require(type(n) is str and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*',n) is not None
            and Path(n).suffix in ('.h','.cpp','.asm','.inc','.py') and type(h) is str
            and re.fullmatch('[0-9a-f]{64}',h) is not None,'Malformed source pin')
        ipc.require(flow.sha((HERE/n).read_bytes())==h,'Held-save source changed: '+n)
    for n,k in (('fixture.exe','fixture_sha256'),('a_save_held_ipc.lib','production_sha256')):
        ipc.require(flow.sha((folder/n).read_bytes())==r[k],'Held-save native artifact changed')
    ipc.require(set(r['runtime_sha256'])=={'reward.dll','checkpoint_planning_hold.dll'},'Missing owned runtime')
    for n,h in r['runtime_sha256'].items():ipc.require(flow.sha((folder/n).read_bytes())==h,'Owned runtime changed')
    return dict(result_sha256=flow.sha(raw),fixture_sha256=r['fixture_sha256'],sources=names,
        sources_match_current=True,game_access=False)


def initial_coordinator(room):
    c=PeriodCoordinator(flow.scope_from_room(room),CONTRACT,'d'*64,{'A':'a'*32,'B':'b'*32},
        dict(year=203,month=8,day=1,phase='PLANNING_BOUNDARY'))
    room.bind_coordinator(c);return c


def model_link():
    room=flow.CheckpointRoom(flow.manifest());select_direct(room);c=initial_coordinator(room)
    binding=flow.FreshSaveBinding(room,c,native_room_id=b'\x01'+bytes(31),native_room_epoch=7,
        artifact_reader=lambda _:None,source_kind='FIXTURE_ONLY')
    return room,c,binding,PlanningSaveLink(binding)


class PhaseTests(unittest.TestCase):
    def test_initial_scope_cannot_be_recaptured_during_run(self):
        room,c,b,link=model_link()
        try:
            run_model(c)
            with self.assertRaises(ValueError):PlanningSaveLink(b)
            linked=link.reserve(1,'mp00000001.s14',flow.model_world(c));x=linked.context()
            self.assertEqual((x['planning']['date']['day'],x['saved_node']['day']),(1,11))
            self.assertEqual(x['planning']['timeline_epoch'],c.epoch)
            self.assertFalse(x['next_planning_epoch_available']);self.assertFalse(x['save_authorized'])
            x['planning']['timeline_epoch']='0'*32
            self.assertNotEqual(x,linked.context())
            with self.assertRaises(ValueError):link.reserve(2,'mp00000002.s14',flow.model_world(c))
        finally:room.close_checkpoints()

    def test_changed_initial_identity_or_pending_event_refuses(self):
        for change in ('epoch','attachment','event'):
            room,c,b,link=model_link()
            try:
                run_model(c)
                if change=='epoch':c.epoch=secrets.token_hex(16)
                elif change=='attachment':c.attachments['A']=secrets.token_hex(16)
                else:c.host_event('A',secrets.token_hex(16),'B',('yes','no'))
                with self.assertRaises(ValueError):link.reserve(1,'mp00000001.s14',flow.model_world(c))
                self.assertEqual(b.status()['reservations'],[])
            finally:room.close_checkpoints()

    def test_failed_reservation_is_not_retried(self):
        room,c,b,link=model_link()
        try:
            run_model(c)
            with self.assertRaises(ValueError):link.reserve(1,'mp00000001.s14',replace(flow.model_world(c),day=1))
            with self.assertRaises(ValueError):link.reserve(1,'mp00000001.s14',flow.model_world(c))
            self.assertEqual(b.status()['reservations'],[])
        finally:room.close_checkpoints()


class HeldFlowTests(unittest.TestCase):
    def test_real_held_save_pipe_tls_journal_and_explicit_phase_gap(self):
        folder=flow.OUTPUT/'held-save';folder.mkdir();room=flow.CheckpointRoom(flow.manifest())
        servers=[];clients=[];fixture=channel=None;holder={};cert,key,fp=flow.make_certificate(folder/'tls')
        def serve(owner):
            server=flow.OwnedServer(('127.0.0.1',0),owner,cert,key)
            t=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True)
            servers.append((server,t));t.start();return server.server_address[1]
        def connect(port,method,credential):
            cls=flow.Client if method=='checkpoint_download' else flow.RoomConnection
            c=cls('127.0.0.1',port,fp,dict(method=method,credential=credential,profile=room.manifest['profile']))
            clients.append(c);return c
        try:
            port=serve(room);download=serve(room.download_endpoint)
            a=connect(port,'host',room.host_token);b=connect(port,'join',room.invite)
            for cl,force in ((a,12),(b,2)):
                self.assertTrue(cl.request(dict(action='select_force',force_id=force,request_id=secrets.token_hex(16),expected_revision=room.revision))['ok'])
            for cl in (a,b):self.assertTrue(cl.request(dict(action='confirm_force',request_id=secrets.token_hex(16),expected_revision=room.revision))['ok'])
            c=initial_coordinator(room);native_id=bytes.fromhex(flow.digest(flow.scope_from_room(room)));native_epoch=secrets.randbits(64) or 1
            binding=flow.FreshSaveBinding(room,c,native_room_id=native_id,native_room_epoch=native_epoch,
                artifact_reader=lambda generation:holder['channel'].wait_artifact(generation),source_kind='FIXTURE_ONLY')
            link=PlanningSaveLink(binding)
            fixture=flow.OwnedFixture(folder/'native',native_id,native_epoch)
            channel=ipc.ASaveClient(fixture.endpoint,on_fault=binding.hold);holder['channel']=channel
            for cl in (a,b):self.assertTrue(cl.request(dict(action='period_ready',epoch=c.epoch,ready=True))['ok'])
            c.begin_simulation(c.seal_inputs());world=flow.model_world(c)
            linked=link.reserve(1,'mp00000001.s14',world);context=linked.context()
            self.assertEqual(context['planning']['date']['day'],1);self.assertEqual(context['saved_node']['day'],11)
            channel.submit(linked.reservation);package=binding.publish(1,lambda:world)
            actual=fixture.message();self.assertEqual(actual['event'],'HELD_SAVE_COPIED')
            self.assertTrue(actual['ready_held'] and actual['gate_held']);self.assertEqual(actual['ready_revision'],1)
            ticket=b.request(dict(action='checkpoint_download_offer',checkpoint_id=package.checkpoint_id));self.assertTrue(ticket['ok'])
            receiver=flow.CheckpointReceiver(ticket['manifest'],package.checkpoint_id,c.scope,c.epoch,c.period,package.manifest['cut'])
            transfer=flow.receive_checkpoint(connect(download,'checkpoint_download',ticket['download_token']),receiver,action='checkpoint_chunk')
            journal_path=folder/'guest.sqlite';args=(journal_path,c.scope,package.manifest,package.checkpoint_id,c.epoch,c.period,package.manifest['cut'],c.attachments)
            flow.CheckpointJournal(*args,create=True).stage(receiver);reopened=flow.CheckpointJournal(*args)
            self.assertEqual(reopened.status()['status'],'STAGED');self.assertEqual(reopened.verified_parts(),transfer['parts'])
            old_epoch=c.epoch;self.assertEqual(context['planning']['timeline_epoch'],old_epoch)
            self.assertEqual(c.phase,'RECONCILING');self.assertEqual(c.period,1)
            flow.complete_model(c,package,receiver)
            self.assertEqual(c.period,2);self.assertNotEqual(c.epoch,old_epoch)
            self.assertTrue(a.request({'action':'status'})['ok'] and b.request({'action':'status'})['ok'])
            channel.stop()
        finally:
            if channel:channel.close()
            if fixture:fixture.close()
            room.close_checkpoints()
            for cl in reversed(clients):cl.close()
            for server,t in reversed(servers):
                server.shutdown();t.join(timeout=5);self.assertFalse(t.is_alive());self.assertTrue(server.wait_handlers());server.server_close()
        flow.NativeFlowTests().closed_owner(fixture,1,1)
        self.assertTrue(fixture.final['ready_held'] and fixture.final['gate_held'])
        EVIDENCE.append(dict(case='ACTUAL_HELD_SAVE_PIPE_TLS',owner_final=fixture.final,resources_closed=True,
            planning_day=1,checkpoint_day=11,native_primitive_current_day=11,native_post_simulation_phase_composed=False,
            linked_context_sha256=linked.context_sha256,diagnostic_save_bytes=len(transfer['parts']['world.s14']),
            guest_journal='STAGED_REOPEN_VERIFIED',guest_load_receipt='MODEL_ONLY',production_permit=False))

    def test_wrong_native_cut_fails_before_actual_save(self):
        model=flow.Fixture();reservation=model.reserve();fixture=channel=None
        try:
            # Frozen fixture's cut9 is deliberately not the native held cut0.
            fixture=flow.OwnedFixture(flow.OUTPUT/'wrong-cut',reservation.request['room_id'],reservation.request['room_epoch'])
            channel=ipc.ASaveClient(fixture.endpoint,on_fault=model.binding.hold)
            with self.assertRaises(ipc.ASaveChannelError):channel.submit(reservation)
            self.assertTrue(model.room.checkpoint_status()['closed'])
        finally:
            if channel:channel.close()
            if fixture:fixture.close()
        flow.NativeFlowTests().closed_owner(fixture,0,0)
        self.assertEqual(fixture.final['backend_submit_calls'],1);self.assertEqual(fixture.final['backend_copy_calls'],0)
        self.assertTrue(fixture.final['ready_held'] and fixture.final['gate_held'])
        EVIDENCE.append(dict(case='ACTUAL_NATIVE_CUT_REFUSAL',owner_final=fixture.final,resources_closed=True))

    def test_shutdown_before_execution_port(self):
        flow.NativeFlowTests().test_shutdown_during_native_permit_prevents_submit()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build-run',required=True,type=Path)
    args=parser.parse_args();flow.BUILD=args.build_run.resolve();flow.BUILD_EVIDENCE=validate_build(flow.BUILD)
    flow.OUTPUT=HERE/'a_save_held_ipc_flow_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');flow.OUTPUT.mkdir(parents=True)
    import sys
    root=HERE.parents[1];paths={Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,'__file__',None)
        and Path(m.__file__).suffix=='.py' and Path(m.__file__).resolve().is_relative_to(root)};paths.add(Path(__file__).resolve())
    before={p.relative_to(root).as_posix():flow.sha(p.read_bytes()) for p in paths}
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (PhaseTests,HeldFlowTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged=all(flow.sha((root/n).read_bytes())==h for n,h in before.items())
    try:validate_build(flow.BUILD)
    except (OSError,ValueError,RuntimeError):unchanged=False
    passed=result.wasSuccessful() and not result.skipped and unchanged
    report=dict(schema='san14.a-save-held-ipc-flow.v1',result='PASS' if passed else 'FAIL',tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),sources_unchanged=unchanged,
        source_sha256=before,build_evidence=flow.BUILD_EVIDENCE,cases=EVIDENCE+flow.EVIDENCE,
        game_access=False,steam_access=False,actual_two_games=False,full_input_held=False,production_permit=False,
        native_post_simulation_phase_composed=False,actual_game_save_load=False,network='REAL_LOOPBACK_TLS',
        native_business='TEST_DOUBLES',guest_load_receipt='MODEL_ONLY')
    path=flow.OUTPUT/'result.json';path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=report['result'],path=str(path))))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
