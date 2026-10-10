"""Pure semantic merge planning for two independent observed reward candidates.

Requires both original before/after context pairs and an identical declared
projection baseline. No original command/context digest is rebased or replaced.
This tests commutativity only within the existing limited projection. Unknown
native side effects may interact; no production merge, writes, Ready or native
completion permission follows from a plan. This module opens no resources.
"""
from copy import deepcopy
import reward_result_delta as delta
from reward_observed_context import projection,CONTRACT
import execution_journal as journal

SCHEMA='san14.reward-result-merge-plan.v1'
POLICY='declared_projection_only_no_native_application'
NAMES=('first','second')
CAPABILITIES=dict(candidate_only=True,limited_projection_only=True,unobserved_side_effects_possible=True,
    full_reward_effects_verified=False,full_world_verified=False,native_completion_verified=False,
    native_apply=False,room_ready_permission=False,execution_permission=False,
    original_deltas_rebased=False,native_command_recomputed=False)


def need(value,message):
    if not value:raise ValueError(message)


def same(a,b):return journal.canonical(a)==journal.canonical(b)


def _evidence(value,candidate,baseline):
    need(type(value) is dict and set(value)=={'before_contexts','after_contexts'},
         'Original before/after context evidence is required')
    checked=delta.validate_delta(candidate,value['before_contexts'],value['after_contexts'])
    before=projection(value['before_contexts']);after=projection(value['after_contexts'])
    need(same(before,baseline) and journal.digest(before)==candidate['before_sha256'],
         'Reward candidates do not share the exact common baseline')
    need(same(delta.reapply(baseline,checked),after),'Original candidate replay differs from evidence')
    return checked,after,dict(before_contexts_sha256=journal.digest(value['before_contexts']),
        after_contexts_sha256=journal.digest(value['after_contexts']))


def _disjoint(first,second):
    need(first['actor']['force_id']!=second['actor']['force_id'],'Two distinct reward actors required')
    need(not(set(first['command']['officer_ids']) & set(second['command']['officer_ids'])),
         'Reward selections overlap')
    keys=lambda value:{(r['fieldtable'],r['id'],r['field']) for r in value['changes']}
    need(not(keys(first)&keys(second)),'Reward changes touch the same field')


def _step(current,candidate,name):
    """Semantic field comparison only; does not call/rewrite delta.reapply."""
    after=deepcopy(current)
    for c in candidate['changes']:
        rows={r['id']:r for r in after[c['fieldtable']]}
        need(c['id'] in rows and same(rows[c['id']][c['field']],c['before']),
             'Semantic step old value changed')
        rows[c['id']][c['field']]=deepcopy(c['after'])
    delta._projection(after)
    step=dict(kind='projection_field_comparison',source=name,actor=deepcopy(candidate['actor']),
        source_delta_sha256=journal.digest(candidate),original_before_sha256=candidate['before_sha256'],
        original_after_sha256=candidate['after_sha256'],expected_before_sha256=journal.digest(current),
        expected_after_sha256=journal.digest(after),changes=deepcopy(candidate['changes']),
        original_delta_rebased=False,native_command_recomputed=False,native_apply=False)
    return after,step


def plan_merge(baseline,first_delta,second_delta,*,first_evidence,second_evidence,
               current=None,side_effect_policy=POLICY):
    """Return a comparison plan, preserving the two original candidate receipts.

    current, when supplied, must equal baseline, first-only, second-only or the
    fully merged projection. No overlapping/third change is silently preserved.
    Omitted current means an unobserved baseline planning assumption, explicitly
    flagged in the output; it is never a fresh game-state observation.
    """
    need(side_effect_policy==POLICY and type(side_effect_policy) is str,
         'Unknown side-effect policy; only limited no-native planning is supported')
    delta._projection(baseline)
    candidates={};outcomes={};evidence={}
    for name,candidate,proof in (('first',first_delta,first_evidence),('second',second_delta,second_evidence)):
        candidates[name],outcomes[name],evidence[name]=_evidence(proof,candidate,baseline)
    a,b=(candidates[n] for n in NAMES)
    need(a['contract']==b['contract']==CONTRACT and same(a['date'],b['date']) and
         same(a['date'],baseline['date']),'Candidate contract/date differs')
    need({a['actor']['force_id'],b['actor']['force_id']}=={f['id'] for f in baseline['forces']},
         'Candidates are not the two baseline actors')
    _disjoint(a,b)
    orders=[];targets=[]
    for names in (NAMES,tuple(reversed(NAMES))):
        cursor=deepcopy(baseline);steps=[]
        for name in names:
            cursor,step=_step(cursor,candidates[name],name);steps.append(step)
        orders.append(dict(order=list(names),steps=steps,final_sha256=journal.digest(cursor)));targets.append(cursor)
    need(same(*targets),'Reward semantic order is not commutative')
    target=targets[0]
    states=dict(baseline=baseline,first_after=outcomes['first'],second_after=outcomes['second'],merged=target)
    source=baseline if current is None else current;delta._projection(source)
    matches=[k for k,v in states.items() if same(source,v)]
    need(len(matches)==1,'Current projection includes an unknown, stale or third change')
    kind=matches[0]
    pending=dict(baseline=NAMES,first_after=('second',),second_after=('first',),merged=())[kind]
    cursor=deepcopy(source);steps=[]
    for name in pending:
        cursor,step=_step(cursor,candidates[name],name);steps.append(step)
    need(same(cursor,target),'Remaining semantic steps do not reach the common target')
    sources={name:dict(actor=deepcopy(candidates[name]['actor']),delta_sha256=journal.digest(candidates[name]),
        before_sha256=candidates[name]['before_sha256'],after_sha256=candidates[name]['after_sha256'],
        command_context_sha256=candidates[name]['command']['context_sha256'],**evidence[name]) for name in NAMES}
    return dict(schema=SCHEMA,contract=CONTRACT,side_effect_policy=POLICY,date=deepcopy(baseline['date']),
        baseline_sha256=journal.digest(baseline),sources=sources,changes_disjoint=True,selections_disjoint=True,
        both_orders_equivalent=True,orders=orders,current_supplied=current is not None,current_kind=kind,
        current_sha256=journal.digest(source),pending_sources=list(pending),steps=steps,
        target_sha256=journal.digest(target),target_projection=deepcopy(target),**CAPABILITIES)


def validate_plan(plan,baseline,first_delta,second_delta,*,first_evidence,second_evidence,
                  current=None,side_effect_policy=POLICY):
    """Recompute the plan from original evidence; hashes alone are not proof."""
    expected=plan_merge(baseline,first_delta,second_delta,first_evidence=first_evidence,
        second_evidence=second_evidence,current=current,side_effect_policy=side_effect_policy)
    need(type(plan) is dict and same(plan,expected),'Merge plan differs from original evidence or current state')
    return deepcopy(expected)
