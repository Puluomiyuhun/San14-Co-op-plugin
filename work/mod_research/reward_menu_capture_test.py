"""Owned-memory/pure capture checks; optional bounded private archive audit."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'outputs'/'san14-link'))
import reward_menu_capture as m


def context():
    return dict(room_id='1'*32,binding_epoch='2'*32,epoch='3'*32,player_id='A',
                bound_force_id=12, main_district_id=11, viewer_force_id=12,
                attachment_id='4'*32,menu_instance_id='5'*32,world_revision=0,
                draft_revision=1,phase='PLANNING',observed_tick=100,expires_tick=200)


def preview():
    return dict(kind='reward',force_id=12,district_id=11,funding_city_id=19,officer_ids=[620,666])


class Tests(unittest.TestCase):
    def setUp(self):
        self.c=context();self.p=preview();self.s=m.CaptureSession();self.id='a'*32

    def capture(self):
        return self.s.capture(self.p,self.c,capture_id=self.id,now_tick=100)

    def confirm(self):
        return self.s.confirm(self.id,self.p,self.c,now_tick=100)

    def test_wire_has_only_allowed_ids(self):
        self.capture();v=self.confirm();q=v.packet()
        self.assertEqual(q,dict(action='reward_submit',room_id='1'*32,binding_epoch='2'*32,
            epoch='3'*32,request_id=v.request_id,district_id=11,officer_ids=[620,666]))
        self.assertFalse(v.native_interception or v.native_execution or v.legality_verified)

    def test_duplicate_confirm_same_proposal(self):
        self.capture();one=self.confirm()
        self.assertIs(one,self.confirm())

    def test_concurrent_confirms_share_request(self):
        self.capture()
        with ThreadPoolExecutor(max_workers=4) as pool:
            values=list(pool.map(lambda _:self.confirm(),range(16)))
        self.assertEqual(len({v.request_id for v in values}),1)

    def test_same_menu_cannot_bypass_with_another_capture_id(self):
        self.capture();self.confirm()
        self.c['draft_revision']=2
        with self.assertRaisesRegex(m.CaptureError,'MENU_ALREADY_CAPTURED'):
            self.s.capture(self.p,self.c,capture_id='b'*32,now_tick=100)

    def test_cancel_before_confirmation(self):
        self.capture()
        self.assertEqual(self.s.cancel(self.id,self.c,now_tick=100),'CANCELLED')
        self.assertEqual(self.s.cancel(self.id,self.c,now_tick=100),'CANCELLED')
        with self.assertRaisesRegex(m.CaptureError,'CANCELLED'):self.confirm()

    def test_cancel_after_confirmation_not_revocation(self):
        self.capture();one=self.confirm()
        with self.assertRaisesRegex(m.CaptureError,'ALREADY_CONFIRMED'):
            self.s.cancel(self.id,self.c,now_tick=100)
        self.assertIs(one,self.confirm())

    def test_cancel_then_new_revision(self):
        self.capture();self.s.cancel(self.id,self.c,now_tick=100)
        self.c['draft_revision']=2
        self.s.capture(self.p,self.c,capture_id='b'*32,now_tick=100)
        self.assertEqual(self.s.confirm('b'*32,self.p,self.c,now_tick=100).officer_ids,(620,666))

    def test_cancel_same_revision_cannot_reopen(self):
        self.capture();self.s.cancel(self.id,self.c,now_tick=100)
        with self.assertRaisesRegex(m.CaptureError,'MENU_ALREADY_CAPTURED'):
            self.s.capture(self.p,self.c,capture_id='b'*32,now_tick=100)

    def test_unknown_capture(self):
        with self.assertRaisesRegex(m.CaptureError,'UNKNOWN_CAPTURE'):self.confirm()

    def test_duplicate_capture_id(self):
        self.capture()
        with self.assertRaisesRegex(m.CaptureError,'CAPTURE_ID_REUSED'):self.capture()

    def test_expiry_cannot_be_extended_after_capture(self):
        self.capture();self.c.update(observed_tick=200,expires_tick=300)
        with self.assertRaisesRegex(m.CaptureError,'STALE_DRAFT'):
            self.s.confirm(self.id,self.p,self.c,now_tick=200)

    def test_fresh_observation_same_identity(self):
        self.capture();self.c.update(observed_tick=110,expires_tick=220)
        self.assertIsNotNone(self.s.confirm(self.id,self.p,self.c,now_tick=110))

    def test_old_observation_at_confirm(self):
        self.capture();self.c['observed_tick']=99
        with self.assertRaisesRegex(m.CaptureError,'STALE_DRAFT'):self.confirm()

    def test_changed_preview_is_terminal_even_if_reverted(self):
        self.capture();original=deepcopy(self.p);self.p['officer_ids']=[620]
        with self.assertRaisesRegex(m.CaptureError,'DRAFT_CHANGED'):self.confirm()
        self.p=original
        with self.assertRaisesRegex(m.CaptureError,'INVALIDATED'):self.confirm()

    def test_changed_context_is_terminal_even_if_reverted(self):
        self.capture();self.c['world_revision']=1
        with self.assertRaisesRegex(m.CaptureError,'CONTEXT_CHANGED'):self.confirm()
        self.c['world_revision']=0
        with self.assertRaisesRegex(m.CaptureError,'INVALIDATED'):self.confirm()

    def test_defensive_input_and_output_copy(self):
        original=deepcopy(self.p);ctx=deepcopy(self.c);self.capture()
        self.p['officer_ids'].append(1);self.c['epoch']='9'*32
        result=self.s.confirm(self.id,original,ctx,now_tick=100)
        wire=result.packet();wire['officer_ids'].append(2)
        self.assertEqual(result.packet()['officer_ids'],[620,666])

    def test_result_frozen(self):
        self.capture();result=self.confirm()
        with self.assertRaises(FrozenInstanceError):result.native_execution=True
        with self.assertRaises(TypeError):m.CAPABILITIES['native_execution']=True

    def test_b_viewer_is_independent(self):
        self.c.update(player_id='B',bound_force_id=2,viewer_force_id=2,main_district_id=4)
        self.p.update(force_id=2,district_id=4)
        self.capture();self.assertEqual(self.confirm().player_id,'B')

    def test_capacity_holds_tombstones(self):
        self.s=m.CaptureSession(capacity=1);self.capture();self.s.cancel(self.id,self.c,now_tick=100)
        self.c['menu_instance_id']='6'*32
        with self.assertRaisesRegex(m.CaptureError,'CAPACITY_EXHAUSTED'):
            self.s.capture(self.p,self.c,capture_id='b'*32,now_tick=100)

    def test_actual_decoder_owned_memory(self):
        from test_domestic_reader import Fixture
        with patch('game_reader.GameReader.__init__',side_effect=AssertionError('live reader forbidden')) as a, \
             patch('game_reader.find_game_pid',side_effect=AssertionError('discovery forbidden')) as b, \
             patch('readonly_probe.find_game_pid',side_effect=AssertionError('discovery forbidden')) as c, \
             patch('readonly_probe.Memory.__init__',side_effect=AssertionError('live memory forbidden')) as d:
            fixture=Fixture('reward');decoded=fixture.capture()
            self.p=decoded['command_preview'];self.capture();first=self.confirm()
            self.assertEqual(first.officer_ids,(620,666))
            # Raw UI event 0 did not auto-submit; confirm is an explicit semantic call.
            self.assertEqual(decoded['ui_event_code_raw'],0)
            relocated=Fixture('reward',0x1000000).capture()
            self.assertEqual(relocated['command_preview'],decoded['command_preview'])
            for guarded in (a,b,c,d):guarded.assert_not_called()

    def test_actual_decoder_changed_selection(self):
        from test_domestic_reader import Fixture
        f=Fixture('reward');self.p=f.capture()['command_preview'];self.capture()
        f.memory.number(f.node1+8,0);f.memory.number(f.counts+8,1)
        changed=f.capture()['command_preview']
        with self.assertRaisesRegex(m.CaptureError,'DRAFT_CHANGED'):
            self.s.confirm(self.id,changed,self.c,now_tick=100)


def rejection_test(target,key,value):
    def test(self):
        (self.c if target=='context' else self.p)[key]=value
        with self.assertRaises(m.CaptureError):self.capture()
    return test


for name,target,key,value in [
    ('unknown_context','context','pointer',0x12345678),
    ('unknown_preview','preview','args_pointer',0x12345678),
    ('wrong_viewer','context','viewer_force_id',2),
    ('foreign_force','preview','force_id',2),
    ('foreign_district','preview','district_id',4),
    ('bad_room_id','context','room_id','address'),
    ('bad_epoch','context','epoch',False),
    ('bad_player','context','player_id','C'),
    ('not_planning','context','phase','RESOLVING'),
    ('future_observation','context','observed_tick',101),
    ('expired_context','context','expires_tick',100),
    ('negative_tick','context','observed_tick',-1),
    ('bool_revision','context','world_revision',True),
    ('float_revision','context','draft_revision',1.0),
    ('bool_force','preview','force_id',True),
    ('bool_district','preview','district_id',True),
    ('pointer_city','preview','funding_city_id',0x100000),
    ('empty_officers','preview','officer_ids',[]),
    ('too_many','preview','officer_ids',list(range(1,18))),
    ('duplicate_officers','preview','officer_ids',[620,620]),
    ('bool_officer','preview','officer_ids',[True]),
    ('float_officer','preview','officer_ids',[620.0]),
    ('pointer_officer','preview','officer_ids',[0x300000000]),
    ('invalid_officer','preview','officer_ids',[6000]),
    ('tuple_officers','preview','officer_ids',(620,666)),
    ('wrong_kind','preview','kind','merchant'),
]:
    setattr(Tests,'test_reject_'+name,rejection_test(target,key,value))


def scope_change_test(key,value):
    def test(self):
        self.capture();self.c[key]=value
        with self.assertRaisesRegex(m.CaptureError,'CONTEXT_CHANGED'):self.confirm()
    return test


for key,value in [('room_id','9'*32),('binding_epoch','9'*32),('epoch','9'*32),
                  ('attachment_id','9'*32),('menu_instance_id','9'*32),('draft_revision',2)]:
    setattr(Tests,'test_invalidate_'+key,scope_change_test(key,value))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root',type=Path)
    args=parser.parse_args()
    folder=HERE/'reward_menu_capture_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    sources=[Path(m.__file__),Path(__file__),HERE/'reward_menu_capture_audit.py']
    dependencies=[ROOT/'outputs'/'san14-link'/n for n in
                  ('domestic_reader.py','game_reader.py','readonly_probe.py','sortie_reader.py','reward_room_flow.py')]
    dependencies.append(HERE/'test_domestic_reader.py')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={str(p.relative_to(ROOT)):digest(p) for p in sources+dependencies}
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (folder/'unittest.txt').write_text(output.getvalue(),encoding='utf-8')
    audit=None
    if args.archive_root:
        try:
            from reward_menu_capture_audit import run
            audit=run(args.archive_root)
        except Exception as error:
            import traceback
            audit=dict(passed=False,error=repr(error),traceback=traceback.format_exc())
        (folder/'audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    after={str(p.relative_to(ROOT)):digest(p) for p in sources+dependencies}
    record=dict(schema='san14.reward-menu-capture-test.v1',passed=result.wasSuccessful() and before==after
                and (audit is None or audit['passed']),tests=result.testsRun,
                failures=len(result.failures),errors=len(result.errors),
                audit_checks=len(audit.get('checks',[])) if audit else 0,
                archive_audit_passed=audit['passed'] if audit else None,
                source_sha256=before,source_end_sha256=after,sources_unchanged=before==after,
                game_access=False,native_interception=False,native_execution=False)
    (folder/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=record['passed'],tests=result.testsRun,failures=len(result.failures),
                         errors=len(result.errors),audit_checks=record['audit_checks'],output=str(folder))))
    if not result.wasSuccessful():print(output.getvalue())
    if audit and not audit['passed']:print(json.dumps(audit,indent=2))
    return 0 if record['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
