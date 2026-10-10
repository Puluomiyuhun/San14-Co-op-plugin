"""Owned two-view byte-memory samples; pure planning, no native result sink."""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import reward_result_merge as merge
import reward_result_delta as delta
from reward_observed_fixture import World
from reward_observed_context import projection
import authority_reward as reward

OUTPUT=None;ROWS=[]


def capture(world):return {f:reward.capture_context(world.reader,f) for f in (12,2)}


def execute(world,actor):
    c=capture(world)[actor];command=reward.make_command(c,11 if actor==12 else 2,[97] if actor==12 else [101])
    reward.validate_reward(command,c,actor);world.execute(command)


def samples():
    a,b=World(12),World(2);before_a,before_b=capture(a),capture(b)
    execute(a,12);execute(b,2);after_a,after_b=capture(a),capture(b)
    return dict(baseline=projection(before_a),first_delta=delta.infer_delta(before_a,after_a),
        second_delta=delta.infer_delta(before_b,after_b),
        first_evidence=dict(before_contexts=before_a,after_contexts=after_a),
        second_evidence=dict(before_contexts=before_b,after_contexts=after_b))


class Tests(unittest.TestCase):
    def test_two_real_sampler_views_merge_matches_owned_both_execution_orders(self):
        args=samples();original=deepcopy(args);plan=merge.plan_merge(**args)
        self.assertEqual(args,original);self.assertTrue(plan['both_orders_equivalent'])
        self.assertEqual([r['final_sha256'] for r in plan['orders']],[plan['target_sha256']]*2)
        for order in ((12,2),(2,12)):
            w=World(12)
            for actor in order:execute(w,actor)
            self.assertEqual(projection(capture(w)),plan['target_projection'])
            self.assertEqual(w.calls,2)
        self.assertEqual(merge.validate_plan(plan,**args),plan)
        self.assertFalse(plan['current_supplied']);self.assertEqual(plan['pending_sources'],['first','second'])
        for key in ('native_apply','room_ready_permission','execution_permission','native_completion_verified','full_reward_effects_verified'):
            self.assertFalse(plan[key])
        self.assertTrue(plan['unobserved_side_effects_possible'])
        ROWS.append(dict(inputs=args,plan=plan,owned_business_double=True))

    def test_four_current_states_do_not_repeat_own_result(self):
        args=samples();initial=merge.plan_merge(**args)
        states=dict(baseline=args['baseline'],first_after=projection(args['first_evidence']['after_contexts']),
            second_after=projection(args['second_evidence']['after_contexts']),merged=initial['target_projection'])
        expected=dict(baseline=['first','second'],first_after=['second'],second_after=['first'],merged=[])
        for kind,current in states.items():
            with self.subTest(kind=kind):
                plan=merge.plan_merge(**args,current=current)
                self.assertTrue(plan['current_supplied']);self.assertEqual(plan['current_kind'],kind)
                self.assertEqual(plan['pending_sources'],expected[kind])
                self.assertEqual([s['source'] for s in plan['steps']],expected[kind])
                self.assertEqual(plan['target_projection'],initial['target_projection'])
                self.assertEqual(merge.validate_plan(plan,**args,current=current),plan)
                ROWS.append(dict(current_kind=kind,plan=plan))

    def test_original_context_and_delta_hashes_are_not_rebased(self):
        args=samples();saved=deepcopy(args);plan=merge.plan_merge(**args)
        for name in ('first','second'):
            d=args[name+'_delta'];row=plan['sources'][name]
            self.assertEqual(row['command_context_sha256'],d['command']['context_sha256'])
            self.assertEqual(row['delta_sha256'],merge.journal.digest(d))
        step=plan['orders'][0]['steps'][1]
        self.assertNotEqual(step['expected_before_sha256'],step['original_before_sha256'])
        self.assertFalse(step['original_delta_rebased']);self.assertNotIn('command',step)
        self.assertEqual(args,saved)
        # Old infer evidence still rejects the changed full baseline, as it must.
        with self.assertRaisesRegex(ValueError,'before state'):
            delta.reapply(projection(args['first_evidence']['after_contexts']),args['second_delta'])

    def test_no_common_baseline_and_missing_evidence_refuse(self):
        args=samples();b=World(2);b.memory.pack(b.cities[13]+0x38,'<I',49000)
        before=capture(b);execute(b,2);after=capture(b)
        args['second_delta']=delta.infer_delta(before,after)
        args['second_evidence']=dict(before_contexts=before,after_contexts=after)
        with self.assertRaisesRegex(ValueError,'common baseline'):merge.plan_merge(**args)
        args=samples();args['second_evidence']={}
        with self.assertRaisesRegex(ValueError,'Original before/after'):merge.plan_merge(**args)

    def test_same_actor_same_officer_and_field_conflicts_refuse(self):
        args=samples();args['second_delta']=deepcopy(args['first_delta'])
        args['second_evidence']=deepcopy(args['first_evidence'])
        with self.assertRaisesRegex(ValueError,'two baseline actors'):merge.plan_merge(**args)
        args=samples()
        # Independently exercise conflict predicates even though authentic
        # cross-force funding/ownership already excludes these malformed pairs.
        d=deepcopy(args['second_delta']);d['command']['officer_ids']=[97]
        with self.assertRaisesRegex(ValueError,'selections overlap'):merge._disjoint(args['first_delta'],d)
        d=deepcopy(args['second_delta']);d['changes'].append(deepcopy(args['first_delta']['changes'][0]))
        with self.assertRaisesRegex(ValueError,'same field'):merge._disjoint(args['first_delta'],d)
        with self.assertRaises(ValueError):merge.plan_merge(**dict(args,second_delta=d))

    def test_third_change_identity_replacement_and_wrong_old_value_refuse(self):
        args=samples();after=projection(args['first_evidence']['after_contexts'])
        for fault in ('food','ruler','new-person','partial-result','old-value'):
            with self.subTest(fault=fault):
                current=deepcopy(after);given=deepcopy(args)
                if fault=='food':current['cities'][0]['food']-=1
                elif fault=='ruler':current['forces'][0]['ruler']+=1
                elif fault=='new-person':
                    p=deepcopy(current['persons'][0]);p['id']=999;current['persons'].append(p)
                elif fault=='partial-result':
                    p=next(p for p in current['persons'] if p['id']==97);p['loyalty']-=1
                elif fault=='old-value':given['second_delta']['changes'][0]['before']+=1
                with self.assertRaises(ValueError):merge.plan_merge(**given,current=current)

    def test_unknown_side_effect_policy_and_native_or_ready_authority_refuse(self):
        args=samples()
        for policy in (None,'full_reward','skip_auxiliary_validation',True):
            with self.subTest(policy=policy),self.assertRaisesRegex(ValueError,'side-effect policy'):
                merge.plan_merge(**args,side_effect_policy=policy)
        plan=merge.plan_merge(**args)
        for key in ('native_apply','room_ready_permission','full_reward_effects_verified'):
            bad=deepcopy(plan);bad[key]=True
            with self.assertRaisesRegex(ValueError,'differs'):merge.validate_plan(bad,**args)

    def test_tampered_semantic_steps_and_unprovided_current_refuse(self):
        args=samples();current=projection(args['first_evidence']['after_contexts'])
        plan=merge.plan_merge(**args,current=current)
        for fault in ('reapply-own','hash','context','target'):
            with self.subTest(fault=fault):
                bad=deepcopy(plan)
                if fault=='reapply-own':bad['steps'].insert(0,bad['orders'][0]['steps'][0])
                elif fault=='hash':bad['steps'][0]['expected_before_sha256']='0'*64
                elif fault=='context':bad['sources']['first']['command_context_sha256']='0'*64
                elif fault=='target':bad['target_projection']['cities'][0]['gold']+=1
                with self.assertRaisesRegex(ValueError,'differs'):merge.validate_plan(bad,**args,current=current)
        with self.assertRaisesRegex(ValueError,'differs'):merge.validate_plan(plan,**args)


if __name__=='__main__':
    OUTPUT=PRIVATE/'reward_result_merge_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    paths={Path(m.__file__).resolve() for m in sys.modules.values() if getattr(m,'__file__',None) and
        Path(m.__file__).resolve().is_relative_to(ROOT)}|{Path(__file__).resolve()}
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    stable=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    (OUTPUT/'owned-plans.json').write_text(json.dumps(ROWS,indent=2)+'\n',encoding='utf-8')
    result=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=before,sources_unchanged=stable,
        game_access=False,native_calls=0,business_double=True,real_existing_capture_algorithm=True,
        production_sink_implemented=False,full_reward_effects_verified=False,
        failures=[(str(t),s) for t,s in r.errors+r.failures],
        artifacts={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.iterdir() if p.is_file()})
    (OUTPUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(OUTPUT/'result.json');raise SystemExit(result['result']!='PASS')
