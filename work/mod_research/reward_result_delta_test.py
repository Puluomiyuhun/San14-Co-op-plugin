"""Pure result validation over the existing owned byte-memory reward fixture.

The unchanged GameReader/authority samplers read the owned layout. World.execute
is its explicit business double; no native reward/game/process/network calls.
"""
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
import reward_result_delta as delta
from reward_observed_fixture import World
from reward_observed_context import projection
import authority_reward as reward
from reward_eligibility import predicate_reason

OUTPUT=None;ROWS=[]


def contexts(w):return {f:reward.capture_context(w.reader,f) for f in (12,2)}


def signed(c):
    for context in c.values():context['context_sha256']=reward.context_hash(context)
    return c


def pair(actor=12,viewer=12,fault=None):
    w=World(viewer);before=contexts(w)
    command=reward.make_command(before[actor],11 if actor==12 else 2,[97] if actor==12 else [101])
    reward.validate_reward(command,before[actor],actor);w.failure=fault;w.execute(command)
    return w,before,contexts(w)


class Tests(unittest.TestCase):
    def test_both_actors_real_sampler_and_pure_reapply(self):
        for actor in (12,2):
            with self.subTest(actor=actor):
                w,b,a=pair(actor);d=delta.infer_delta(b,a)
                self.assertEqual(d['actor']['force_id'],actor)
                self.assertEqual(delta.validate_delta(d,b,a),d)
                original=deepcopy(projection(b));self.assertEqual(delta.reapply(original,d),projection(a))
                self.assertEqual(original,projection(b));self.assertEqual(w.calls,1)
                self.assertEqual(len(d['changes']),4);self.assertTrue(d['candidate_only'])
                self.assertFalse(d['native_completion_verified']);self.assertFalse(d['execution_permission'])
                self.assertTrue(d['limited_projection_only']);self.assertTrue(d['unobserved_side_effects_possible'])
                self.assertIsNot(d['command']['date'],b[actor]['date'])
                ROWS.append(dict(actor=actor,before=b,after=a,delta=d))

    def test_other_viewer_matches_projection_without_using_source_context_as_authority(self):
        _,ba,aa=pair(12,12);_,bb,ab=pair(12,2)
        da=delta.infer_delta(ba,aa);db=delta.infer_delta(bb,ab)
        self.assertEqual((da['before_sha256'],da['after_sha256'],da['changes']),
                         (db['before_sha256'],db['after_sha256'],db['changes']))
        self.assertNotEqual(da['command']['context_sha256'],db['command']['context_sha256'])
        self.assertEqual(delta.reapply(projection(bb),da),projection(ab))

    def test_actual_increase_is_observed_not_assumed_plus_four(self):
        w,b,a=pair();w.memory.pack(w.people[97]+0x120,'<B',91);a=contexts(w)
        d=delta.infer_delta(b,a);self.assertEqual(d['effects']['officers'][0]['loyalty_after'],91)
        self.assertFalse(d['effects']['loyalty_formula_verified'])

    def test_no_change_wrong_cost_and_unselected_field_refuse(self):
        for fault in ('none','wrong-cost','unselected','food','mixed-actors'):
            with self.subTest(fault=fault):
                w,b,a=pair(fault=fault if fault in ('wrong-cost','unselected') else None)
                if fault=='none':a=deepcopy(b)
                if fault=='food':w.memory.pack(w.cities[19]+0x38,'<I',49999);a=contexts(w)
                if fault=='mixed-actors':
                    cmd=reward.make_command(a[2],2,[101]);w.execute(cmd);a=contexts(w)
                with self.assertRaises(ValueError):delta.infer_delta(b,a)

    def test_date_identity_phase_and_membership_refuse(self):
        for fault in ('date','viewer','phase','new-person','duplicate-person','duplicate-district','force-set'):
            with self.subTest(fault=fault):
                _,b,a=pair();a=deepcopy(a)
                for c in a.values():
                    if fault=='date':c['date']['day']=21
                    elif fault=='viewer':c['viewer_force_id']=2
                    elif fault=='phase':c['strategy_mode']=3
                    elif fault=='new-person':
                        p=deepcopy(c['persons'][-1]);p['id']=202;c['persons'].append(p)
                    elif fault=='duplicate-person':c['persons'].append(deepcopy(c['persons'][0]))
                    elif fault=='duplicate-district':c['districts'].append(deepcopy(c['districts'][0]))
                if fault=='force-set':a[3]=a.pop(2)
                signed(a)
                with self.assertRaises(ValueError):delta.infer_delta(b,a)

    def test_flags_predicate_tampering_and_actor_constraint_refuse(self):
        for fault in ('extra-flag','missing-flag','predicate','actor'):
            with self.subTest(fault=fault):
                w,b,a=pair()
                if fault in ('extra-flag','missing-flag'):
                    w.memory.pack(w.people[97]+0x196,'<H',6 if fault=='extra-flag' else 0);a=contexts(w)
                if fault=='predicate':
                    for c in b.values():
                        p=next(p for p in c['persons'] if p['id']==97);p['predicate_eligible']=False
                    signed(b)
                with self.assertRaises(ValueError):delta.infer_delta(b,a,actor_force_id=2 if fault=='actor' else None)

    def test_delta_duplicate_field_tamper_cost_and_replay_refuse(self):
        _,b,a=pair();d=delta.infer_delta(b,a);p=projection(b)
        for fault in ('duplicate','unknown-field','cost','permission','hash','selected','coverage'):
            with self.subTest(fault=fault):
                bad=deepcopy(d)
                if fault=='duplicate':bad['changes'].append(deepcopy(bad['changes'][0]))
                elif fault=='unknown-field':bad['changes'][0]['field']='pointer'
                elif fault=='cost':bad['effects']['costs']['gold']=99
                elif fault=='permission':bad['native_completion_verified']=True
                elif fault=='hash':bad['after_sha256']='0'*64
                elif fault=='selected':bad['command']['officer_ids']=[97,97]
                elif fault=='coverage':bad['unobserved_side_effects_possible']=False
                with self.assertRaises(ValueError):delta.reapply(p,bad)
                with self.assertRaises(ValueError):delta.validate_delta(bad,b,a)
        with self.assertRaisesRegex(ValueError,'before state'):delta.reapply(projection(a),d)

    def test_ambiguous_menu_origin_needs_explicit_observed_district(self):
        _,b,a=pair()
        # Both menus fund from the same proven city. The result alone cannot
        # distinguish the main menu from a selected officer's district menu.
        for group in (b,a):
            for c in group.values():
                row=deepcopy(next(d for d in c['districts'] if d['id']==11));row['id']=17;row['action_points']=10
                c['districts'].append(row)
                for p in c['persons']:
                    if p['id']==97:p['district_id']=17
                if c['command_force_id']==12:c['funding']['17']=deepcopy(c['funding']['11'])
            signed(group)
        with self.assertRaisesRegex(ValueError,'unique'):delta.infer_delta(b,a)
        d=delta.infer_delta(b,a,district_id=17);self.assertEqual(d['actor']['district_id'],17)
        self.assertEqual(delta.reapply(projection(b),d),projection(a))

    def test_seventeen_officers_refuse(self):
        _,b,a=pair()
        for group,is_after in ((b,False),(a,True)):
            for c in group.values():
                original=next(p for p in c['persons'] if p['id']==97)
                for i in range(200,216):
                    row=deepcopy(original);row['id']=i;c['persons'].append(row)
            signed(group)
        with self.assertRaisesRegex(ValueError,'sixteen'):delta.infer_delta(b,a)


if __name__=='__main__':
    OUTPUT=PRIVATE/'reward_result_delta_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    paths={Path(m.__file__).resolve() for m in sys.modules.values() if getattr(m,'__file__',None) and
           Path(m.__file__).resolve().is_relative_to(ROOT)}|{Path(__file__).resolve()}
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    stable=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    (OUTPUT/'owned-results.json').write_text(json.dumps(ROWS,indent=2)+'\n',encoding='utf-8')
    result=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=before,sources_unchanged=stable,
        game_access=False,native_calls=0,business_double=True,real_existing_capture_algorithm=True,
        full_world_verified=False,failures=[(str(t),s) for t,s in r.errors+r.failures],
        artifacts={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.iterdir() if p.is_file()})
    (OUTPUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(OUTPUT/'result.json');raise SystemExit(result['result']!='PASS')
