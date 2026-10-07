"""Adversarial lobby/ownership checks; no game process or simulated world."""
from copy import deepcopy
import json
from pathlib import Path
import secrets
import sys
import threading
import unittest
ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
sys.path.insert(0, str(OUT))
from room_session import Room, RoomError, PROTOCOL


def manifest():
    return {'profile': {'protocol': PROTOCOL, 'game_sha256': 'a'*64,
                        'adapter_contract': 'research-no-native-room-adapter.v1',
                        'checkpoint_sha256': 'b'*64, 'rules_sha256': 'c'*64},
            'forces': [{'id': 12, 'name': '张鲁', 'main_district_id': 11},
                       {'id': 2, 'name': '刘备', 'main_district_id': 2},
                       {'id': 1, 'name': '曹操', 'main_district_id': 1}], 'source': {'test': True}}


class RoomTests(unittest.TestCase):
    def setUp(self):
        self.r = Room(manifest())
        self.r.authenticate({'method': 'host', 'credential': self.r.host_token, 'profile': manifest()['profile']}, 'ca')
        self.b = self.r.authenticate({'method': 'join', 'credential': self.r.invite, 'profile': manifest()['profile']}, 'cb')

    def req(self, player, action, **fields):
        return self.r.handle(player, 'ca' if player == 'A' else 'cb', {'action': action, 'request_id': secrets.token_hex(16), **fields})

    def select(self, p, f):
        return self.req(p, 'select_force', force_id=f, expected_revision=self.r.revision)

    def confirm(self, p):
        return self.req(p, 'confirm_force', expected_revision=self.r.revision)

    def locked(self):
        self.assertTrue(self.select('A',12)['ok']);self.assertTrue(self.select('B',2)['ok'])
        self.assertTrue(self.confirm('A')['ok']);self.assertTrue(self.confirm('B')['ok'])

    def envelope(self, f=2):
        return {'room_id': self.r.room_id, 'binding_epoch': self.r.binding_epoch,
                'command': {'schema': 'san14.authority-reward-command.v1', 'force_id': f, 'game_sha256': 'a'*64}}

    def test_wrong_profile(self):
        p=manifest()['profile'];p['rules_sha256']='d'*64
        with self.assertRaises(RoomError):self.r.authenticate({'method':'resume','credential':self.b['resume_token'],'profile':p},'new')

    def test_bad_invite(self):
        with self.assertRaises(RoomError):self.r.authenticate({'method':'join','credential':'wrong','profile':manifest()['profile']},'new')

    def test_invite_cannot_take_reserved_seat(self):
        self.r.disconnect('B','cb')
        with self.assertRaises(RoomError):self.r.authenticate({'method':'join','credential':self.r.invite,'profile':manifest()['profile']},'new')

    def test_guest_cannot_authenticate_as_host(self):
        with self.assertRaises(RoomError):self.r.authenticate({'method':'host','credential':self.b['resume_token'],'profile':manifest()['profile']},'new')

    def test_cannot_duplicate_active_connection(self):
        with self.assertRaises(RoomError):self.r.authenticate({'method':'resume','credential':self.b['resume_token'],'profile':manifest()['profile']},'new')

    def test_bool_force_rejected(self):self.assertFalse(self.select('A',True)['ok'])
    def test_unknown_force_rejected(self):self.assertFalse(self.select('A',51)['ok'])
    def test_taken_force_rejected(self):self.select('A',12);self.assertFalse(self.select('B',12)['ok'])
    def test_stale_selection(self):self.assertFalse(self.req('A','select_force',force_id=12,expected_revision=0)['ok'])
    def test_no_selection_confirm(self):self.assertFalse(self.confirm('A')['ok'])

    def test_selection_clears_confirmations(self):
        self.select('A',12);self.select('B',2);self.confirm('A');self.select('B',1)
        self.assertFalse(any(x['confirmed'] for x in self.r.players.values()))

    def test_two_confirmations_required(self):
        self.select('A',12);self.select('B',2);self.confirm('A');self.assertIsNone(self.r.bindings)
        self.confirm('B');self.assertEqual(self.r.view('A')['phase'],'WAITING_NATIVE_ADAPTER')

    def test_locked_factions(self):self.locked();self.assertFalse(self.select('A',1)['ok'])

    def test_duplicate_is_idempotent(self):
        q={'action':'select_force','request_id':'1'*32,'force_id':12,'expected_revision':self.r.revision}
        first=self.r.handle('A','ca',q);v=self.r.revision;second=self.r.handle('A','ca',q)
        self.assertEqual(first['receipt'],second['receipt']);self.assertTrue(second['duplicate']);self.assertEqual(v,self.r.revision)
        self.assertFalse(self.r.handle('A','ca',{**q,'force_id':2})['ok'])

    def test_simultaneous_selection(self):
        q={'action':'select_force','force_id':12,'expected_revision':self.r.revision};out=[];gate=threading.Barrier(2)
        def choose(p,c):
            gate.wait();out.append(self.r.handle(p,c,{**q,'request_id':secrets.token_hex(16)}))
        a=threading.Thread(target=choose,args=('A','ca'));b=threading.Thread(target=choose,args=('B','cb'))
        a.start();b.start();a.join();b.join();self.assertEqual(sum(x['ok'] for x in out),1)

    def test_authorized_binding(self):
        self.locked();r=self.req('B','route_preview',envelope=self.envelope())
        self.assertTrue(r['ok']);self.assertEqual(r['receipt']['authorized_force_id'],2);self.assertFalse(r['receipt']['applied_to_game'])

    def test_wrong_faction_binding(self):self.locked();self.assertFalse(self.req('A','route_preview',envelope=self.envelope())['ok'])
    def test_bool_command_force(self):self.locked();self.assertFalse(self.req('B','route_preview',envelope=self.envelope(True))['ok'])

    def test_stale_binding(self):
        self.locked();e=self.envelope();e['binding_epoch']='old';self.assertFalse(self.req('B','route_preview',envelope=e)['ok'])

    def test_wrong_room(self):
        self.locked();e=self.envelope();e['room_id']='another';self.assertFalse(self.req('B','route_preview',envelope=e)['ok'])

    def test_unbound_command(self):self.assertFalse(self.req('B','route_preview',envelope=self.envelope())['ok'])

    def test_disconnect_reserves_binding_and_pauses(self):
        self.locked();old=deepcopy(self.r.bindings);epoch=self.r.binding_epoch;self.r.disconnect('B','cb')
        self.assertEqual(self.r.view('A')['phase'],'BOUND_PEER_OFFLINE')
        self.assertFalse(self.req('A','route_preview',envelope=self.envelope(12))['ok'])
        self.r.authenticate({'method':'resume','credential':self.b['resume_token'],'profile':manifest()['profile']},'new')
        self.r.disconnect('B','cb');self.assertEqual(self.r.bindings,old);self.assertEqual(self.r.binding_epoch,epoch)
        self.assertEqual(self.r.players['B']['connection'],'new')
        self.assertFalse(self.r.handle('B','cb',{'action':'status'})['ok'])

    def test_native_config_and_events_share_binding(self):
        self.locked();c=self.r.native_control_config();self.assertEqual(c['human_force_mask'],4100)
        self.assertEqual(c['main_districts'],{'12':11,'2':2});self.assertFalse(c['installed_in_game'])
        self.assertEqual(self.r.event_recipient(2),'B');self.assertEqual(self.r.event_recipient(12),'A');self.assertIsNone(self.r.event_recipient(1))

    def test_no_secrets_in_view(self):
        raw=json.dumps(self.r.view('A'));self.assertNotIn(self.r.invite,raw);self.assertNotIn(self.r.host_token,raw);self.assertNotIn(self.b['resume_token'],raw)

    def test_native_start_disabled(self):
        self.locked();self.assertFalse(self.req('A','start_game')['ok']);self.assertFalse(self.r.view('A')['world_synchronized'])

    def test_duplicate_main_rejected(self):
        m=manifest();m['forces'][1]['main_district_id']=11
        with self.assertRaises(RoomError):Room(m)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(RoomTests))
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'scope':'Room protocol only; no game execution'}
    (ROOT/'room-session-tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful() else 1)
