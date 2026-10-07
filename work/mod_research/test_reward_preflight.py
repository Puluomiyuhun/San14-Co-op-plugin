"""Authorization and resource/scope adversarial checks using synthetic context."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs'/'san14-link'))
from reward_preflight import (SUPPORTED_SHA256,PLANNING_STACK,PreflightError,context_hash,
                              make_command,validate_reward)

def fixture():
    def person(identity,district=9,force=12,rank=4,eligible=True,reason=None):
        return {'id':identity,'name':str(identity),'district_id':district,'force_id':force,
                'rank_raw':rank,'native_valid':True,'loyalty':90,'predicate_eligible':eligible,
                'rejection_reason':reason}
    def district(identity,force,leader,actions):
        return {'id':identity,'force_id':force,'kind_raw':1 if identity==11 else 2,
                'leader_id':leader,'action_points':actions,'valid':True}
    def funding(identity,city_id,leader):
        return {'supported':True,'leader_id':leader,'leader_force_id':12,'leader_location_id':city_id,
                'city':{'id':city_id,'name':str(city_id),'district_id':identity,'force_id':12,
                        'foothold_id':city_id,'gold':1000}}
    c={'schema':'san14.reward-preflight-context.v1','game_sha256':SUPPORTED_SHA256,
       'date':{'year':203,'month':8,'day':11,'period':'中旬'},'current_player_force_id':12,'ruler_id':666,
       'state_stack':PLANNING_STACK.copy(),'strategy_mode':2,'main_district_id':11,
       'districts':[district(9,12,179,22),district(11,12,666,18),district(2,2,952,20)],
       'funding':{'11':funding(11,19,666),'9':funding(9,18,179)},'native_action_cost':1,
       'persons':[person(97),person(759),person(904),person(38,11),person(952,2,2),
                  person(166,11,eligible=False,reason='army_order_nonzero'),person(999,9,rank=8)]}
    c['context_sha256']=context_hash(c);return c

class PreflightTests(unittest.TestCase):
    def setUp(self):self.context=fixture();self.command=make_command(self.context,11,[97,759,904])
    def reject(self,code,command=None,context=None,authority=12):
        with self.assertRaises(PreflightError) as caught:
            validate_reward(command or self.command,context or self.context,authority)
        self.assertEqual(caught.exception.code,code)
    def refresh(self):
        self.context['context_sha256']=context_hash(self.context)
        self.command['context_sha256']=self.context['context_sha256']
    def test_main_district_can_select_other_own_district(self):
        r=validate_reward(self.command,self.context,12)
        self.assertEqual(r['expected_costs']['gold'],300)
        self.assertEqual(r['expected_costs']['charged_district_id'],11)
        self.assertEqual(r['expected_costs']['action_points'],1)
        self.assertFalse(r['applied_to_game']);self.assertFalse(r['replay_supported'])
    def test_nonmain_district_local_selection(self):
        r=validate_reward(make_command(self.context,9,[97]),self.context,12)
        self.assertEqual(r['expected_costs']['funding_city_id'],18)
        self.assertEqual(r['expected_costs']['charged_district_id'],9)
    def test_nonmain_district_cannot_select_other_own_district(self):
        self.reject('menu_scope',make_command(self.context,9,[38]))
    def test_other_force_officer(self):self.command['officer_ids']=[952];self.reject('officer_owner')
    def test_declared_force_does_not_grant_authority(self):self.command['force_id']=2;self.reject('authorization')
    def test_authority_does_not_change_local_player_context(self):self.reject('authorization',authority=2)
    def test_other_force_context_district(self):self.command['district_id']=2;self.reject('district_owner')
    def test_wrong_funding_city(self):self.command['funding_city_id']=18;self.reject('funding_city')
    def test_wrong_funding_owner(self):
        self.context['funding']['11']['city']['force_id']=2;self.refresh();self.reject('funding_owner')
    def test_charged_district_derived_from_city(self):
        self.context['funding']['11']['city']['district_id']=9;self.refresh()
        r=validate_reward(self.command,self.context,12)
        self.assertEqual(r['expected_costs']['charged_district_id'],9)
        self.assertEqual(r['expected_costs']['actions_before'],22)
    def test_no_actions_in_actual_charged_district(self):
        self.context['funding']['11']['city']['district_id']=9
        self.context['districts'][0]['action_points']=0;self.refresh();self.reject('insufficient_actions')
    def test_wrong_leader_location(self):
        self.context['funding']['11']['leader_location_id']=18;self.refresh();self.reject('funding_origin')
    def test_non_city_funding_rejected(self):
        self.context['funding']['11']={'supported':False};self.refresh();self.reject('unsupported_funding')
    def test_empty_list(self):self.command['officer_ids']=[];self.reject('officer_ids')
    def test_duplicate_id(self):self.command['officer_ids']=[97,97];self.reject('duplicate_officer')
    def test_boolean_id(self):self.command['officer_ids']=[True];self.reject('officer_ids')
    def test_unknown_id(self):self.command['officer_ids']=[5000];self.reject('officer_identity')
    def test_rank_outside_menu(self):self.command['officer_ids']=[999];self.reject('menu_scope')
    def test_army_predicate_denial(self):self.command['officer_ids']=[166];self.reject('officer_ineligible')
    def test_gold_short_by_one(self):
        self.context['funding']['11']['city']['gold']=299;self.refresh();self.reject('insufficient_gold')
    def test_exact_cost_is_sufficient(self):
        self.context['funding']['11']['city']['gold']=300
        self.context['districts'][1]['action_points']=1;self.refresh()
        r=validate_reward(self.command,self.context,12)
        self.assertEqual(r['expected_costs']['gold_if_executed'],0)
        self.assertEqual(r['expected_costs']['actions_if_executed'],0)
    def test_changed_cost_constant(self):self.context['native_action_cost']=2;self.refresh();self.reject('action_cost')
    def test_resource_change_invalidates_old_command(self):
        self.context['funding']['11']['city']['gold']=999
        self.context['context_sha256']=context_hash(self.context);self.reject('stale_context')
    def test_context_tampering(self):self.context['funding']['11']['city']['gold']=999;self.reject('context_integrity')
    def test_wrong_turn(self):self.command['date']={'year':203,'month':8,'day':21};self.reject('wrong_turn')
    def test_dialog_open(self):self.context['state_stack'].append('CStrategyRewardState');self.refresh();self.reject('wrong_phase')
    def test_wrong_strategy_mode(self):self.context['strategy_mode']=1;self.refresh();self.reject('wrong_phase')
    def test_extra_command_key(self):self.command['execute']=True;self.reject('command_shape')
    def test_boolean_force(self):self.command['force_id']=True;self.reject('identity')
    def test_wrong_game_version(self):self.command['game_sha256']='0'*64;self.reject('game_version')

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PreflightTests)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'mode':'offline-synthetic-preflight',
            'opened_game_process':False,'game_orders_executed':0}
    (ROOT/'reward-preflight-fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
