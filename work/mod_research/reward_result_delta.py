"""Pure candidate recognition for one already-observed native-menu reward.

No reader, writes, game calls, completion receipt, ownership or replay authority.
Hashes cover the existing declared two-force projection, not the full world.
An optional actor/district restricts inference; ambiguous menu origins refuse.
"""
from copy import deepcopy
from reward_observed_context import projection,validate_effect,CONTRACT,PERSON_FIELDS,CITY_FIELDS,DISTRICT_FIELDS
import authority_reward as reward
import execution_journal as journal
from reward_eligibility import predicate_reason

SCHEMA='san14.reward-result-delta.v1'
TABLES={'persons':PERSON_FIELDS,'cities':CITY_FIELDS,'districts':DISTRICT_FIELDS}
ALLOWED={'persons':{'loyalty','flags'},'cities':{'gold'},'districts':{'action_points'}}
FIELDS={'schema','contract','actor','date','before_sha256','after_sha256','changes','command','effects',
        'candidate_only','native_completion_verified','full_world_verified','execution_permission',
        'limited_projection_only','unobserved_side_effects_possible'}


def need(value,message):
    if not value:raise ValueError(message)


def integer(value,low,high):return type(value) is int and low<=value<=high


def _unique(rows,label):
    need(type(rows) is list and len(rows)<=6000,'Invalid '+label+' rows')
    ids=[r.get('id') for r in rows if type(r) is dict]
    need(len(ids)==len(rows) and all(integer(i,1,5999) for i in ids) and len(set(ids))==len(ids),
         'Duplicate or invalid '+label+' IDs')
    return {r['id']:r for r in rows}


def _contexts(contexts):
    need(type(contexts) is dict and len(contexts)==2 and all(integer(f,1,51) for f in contexts),
         'Exactly two force contexts required')
    viewers=set()
    for force,c in contexts.items():
        need(type(c) is dict and c.get('schema')=='san14.authority-reward-context.v1' and
             c.get('command_force_id')==force and c.get('game_sha256')==reward.SUPPORTED_SHA256 and
             c.get('state_stack')==reward.PLANNING_STACK and c.get('strategy_mode')==2,
             'Reward context identity/build/phase differs')
        need(integer(c.get('viewer_force_id'),1,51),'Invalid local viewer');viewers.add(c['viewer_force_id'])
        need(c.get('context_sha256')==reward.context_hash(c),'Context digest differs')
        for name in ('persons','districts'):_unique(c[name],name)
        for p in c['persons']:
            need(integer(p.get('loyalty'),0,100) and integer(p.get('flags'),0,65535) and
                 type(p.get('native_valid')) is bool and type(p.get('predicate_eligible')) is bool,
                 'Invalid person reward fields')
            reason=predicate_reason(p)
            need(p.get('rejection_reason')==reason and p['predicate_eligible']==(reason is None),
                 'Person predicate does not match observed fields')
        need(type(c['funding']) is dict and all(type(k) is str and k==str(int(k)) for k in c['funding']),
             'Invalid funding identities')
        city_rows={}
        for f in c['funding'].values():
            need(type(f) is dict and f.get('supported') is True,'Unsupported city funding')
            city=f['city'];need(integer(city['id'],1,51),'Invalid funding city')
            old=city_rows.setdefault(city['id'],city);need(old==city,'Conflicting repeated funding city')
    need(len(viewers)==1 and next(iter(viewers)) in contexts,'Two contexts disagree on local viewer')
    result=projection(contexts);_projection(result);return result


def _projection(p):
    need(type(p) is dict and set(p)=={'schema','date','forces','districts','cities','persons'} and
         p['schema']==CONTRACT,'Exact declared projection required')
    need(type(p['date']) is dict and all(integer(p['date'].get(k),lo,hi) for k,lo,hi in
         (('year',1,9999),('month',1,12),('day',1,30))),'Invalid projection date')
    forces=_unique(p['forces'],'forces');need(len(forces)==2,'Exactly two projected forces')
    for f in forces.values():need(set(f)=={'id','ruler','main_district'} and integer(f['id'],1,51) and
        integer(f['ruler'],1,5999) and integer(f['main_district'],1,51),'Invalid force identity')
    for table,keys in TABLES.items():
        for r in _unique(p[table],table).values():
            need(set(r)==set(keys),'Projection field set differs')
            for key,value in r.items():
                if key in ('task','army'):continue
                if key in ('valid','native_valid'):need(type(value) is bool,'Invalid boolean projection field')
                else:need(type(value) is int and 0<=value<2**32,'Invalid integer projection field')
            if table=='persons':need(r['loyalty']<=100 and r['flags']<=65535,'Invalid person bounds')
    journal.digest(p)


def _changes(before,after):
    need(before['schema']==after['schema'] and before['date']==after['date'] and before['forces']==after['forces'],
         'Date or force identity changed')
    changes=[]
    for table in sorted(TABLES):
        a,b=_unique(before[table],table),_unique(after[table],table)
        need(set(a)==set(b),'Projection object membership changed')
        for identity in sorted(a):
            for field in sorted(a[identity]):
                old,new=a[identity][field],b[identity][field]
                if journal.canonical(old)==journal.canonical(new):continue
                need(field in ALLOWED[table] and type(old) is int and type(new) is int,
                     'Unexpected projected field change: '+table+'.'+field)
                changes.append(dict(fieldtable=table,id=identity,field=field,before=old,after=new))
    return changes


def _context_stability(before,after,ids,costs):
    """Check nonprojected context metadata too, excluding opaque raw-person hashes.

    Predicate annotations legitimately change following flags|2. The original
    complete-person raw digest cannot be recomputed from this partial projection.
    """
    need(set(before)==set(after),'Bound force set changed')
    for force in before:
        a,b=deepcopy(before[force]),deepcopy(after[force])
        for c in (a,b):
            c.pop('context_sha256');c.pop('person_records_sha256')
        need(set(_unique(a['persons'],'persons'))==set(_unique(b['persons'],'persons')),
             'Context person membership changed')
        for p in a['persons']:
            if p['id'] in ids:
                actual=next(r for r in b['persons'] if r['id']==p['id'])
                p['loyalty']=actual['loyalty'];p['flags']|=2
                p['rejection_reason']=predicate_reason(p);p['predicate_eligible']=p['rejection_reason'] is None
        for d in a['districts']:
            if d['id']==costs['charged_district_id']:d['action_points']-=costs['action_points']
        for f in a['funding'].values():
            if f['city']['id']==costs['funding_city_id']:f['city']['gold']-=costs['gold']
        need(journal.canonical(a)==journal.canonical(b),'Other observed context fields changed')


def infer_delta(before_contexts,after_contexts,*,actor_force_id=None,district_id=None):
    before=_contexts(before_contexts);after=_contexts(after_contexts)
    need(set(before_contexts)==set(after_contexts),'Bound force set changed')
    changes=_changes(before,after);people=_unique(before['persons'],'persons');new=_unique(after['persons'],'persons')
    ids=sorted(i for i,p in people.items() if new[i]['loyalty']>p['loyalty'])
    need(1<=len(ids)<=16,'One through sixteen increased-loyalty officers required')
    actors={people[i]['force_id'] for i in ids};need(len(actors)==1,'Mixed actor rewards rejected')
    actor=next(iter(actors));need(actor in before_contexts,'Actor is not one of the two bound forces')
    need(actor_force_id is None or integer(actor_force_id,1,51) and actor_force_id==actor,'Observed actor differs')
    for i in ids:need(new[i]['flags']==(people[i]['flags']|2) and not(people[i]['flags']&2),
                      'Reward flags did not transition exactly once')
    c=before_contexts[actor]
    need(district_id is None or integer(district_id,1,51),'Invalid requested district')
    candidates=[district_id] if district_id is not None else sorted(d['id'] for d in c['districts'] if d['force_id']==actor)
    valid=[]
    for district in candidates:
        try:
            command=reward.make_command(c,district,ids)
            precheck=reward.validate_reward(command,c,actor)
            effects=validate_effect(before,after,command,precheck)
            _context_stability(before_contexts,after_contexts,ids,precheck['expected_costs'])
            valid.append((command,effects))
        except (ValueError,KeyError,StopIteration):continue
    need(len(valid)==1,'Reward effect has no unique validated menu origin')
    command,effects=valid[0]
    return dict(schema=SCHEMA,contract=CONTRACT,actor=dict(force_id=actor,district_id=command['district_id']),
        date=deepcopy(before['date']),before_sha256=journal.digest(before),after_sha256=journal.digest(after),
        changes=changes,command=deepcopy(command),effects=deepcopy(effects),candidate_only=True,native_completion_verified=False,
        full_world_verified=False,execution_permission=False,limited_projection_only=True,
        unobserved_side_effects_possible=True)


def validate_delta(delta,before_contexts,after_contexts):
    _envelope(delta)
    expected=infer_delta(before_contexts,after_contexts,actor_force_id=delta['actor']['force_id'],
                         district_id=delta['actor']['district_id'])
    need(journal.canonical(delta)==journal.canonical(expected),'Candidate differs from complete context verification')
    return deepcopy(expected)


def _envelope(delta):
    need(type(delta) is dict and set(delta)==FIELDS and delta['schema']==SCHEMA and delta['contract']==CONTRACT,
         'Exact reward candidate envelope required')
    need(all(delta[k] is True for k in ('candidate_only','limited_projection_only','unobserved_side_effects_possible')) and all(delta[k] is False for k in
         ('native_completion_verified','full_world_verified','execution_permission')),'Candidate must not grant authority')
    need(type(delta['actor']) is dict and set(delta['actor'])=={'force_id','district_id'} and
         all(integer(v,1,51) for v in delta['actor'].values()),'Invalid candidate actor')
    for name in ('before_sha256','after_sha256'):
        need(type(delta[name]) is str and len(delta[name])==64 and all(c in '0123456789abcdef' for c in delta[name]),
             'Invalid projection digest')


def reapply(before_projection,delta):
    """Pure projection replay for comparison; never authorizes native execution.

    A receiver must additionally validate local full contexts/authority. This
    helper does not infer a native menu event from a remotely supplied digest.
    """
    _envelope(delta);_projection(before_projection)
    need(journal.digest(before_projection)==delta['before_sha256'] and before_projection['date']==delta['date'],
         'Projection does not match candidate before state (including replay)')
    after=deepcopy(before_projection);need(type(delta['changes']) is list and 4<=len(delta['changes'])<=34,
                                         'Bounded reward changes required')
    seen=set()
    for change in delta['changes']:
        need(type(change) is dict and set(change)=={'fieldtable','id','field','before','after'},'Exact typed field change required')
        t,i,f=change['fieldtable'],change['id'],change['field']
        need(type(t) is str and t in ALLOWED and type(f) is str and f in ALLOWED[t] and integer(i,1,5999),
             'Unknown mutable field/identity')
        need((t,i,f) not in seen,'Duplicate delta field');seen.add((t,i,f))
        row=_unique(after[t],t).get(i)
        need(row is not None and type(change['before']) is int and type(change['after']) is int and
             row[f]==change['before'] and change['before']!=change['after'],'Stale or invalid field value')
        row[f]=change['after']
    _projection(after)
    need(_changes(before_projection,after)==delta['changes'] and journal.digest(after)==delta['after_sha256'],
         'Candidate ordering or after digest differs')
    command=delta['command'];actor=delta['actor'];effects=delta['effects'];cost=effects['costs']
    need(type(command) is dict and set(command)=={'schema','game_sha256','context_sha256','date','force_id',
         'district_id','funding_city_id','officer_ids'} and command.get('schema')=='san14.authority-reward-command.v1' and
         command.get('game_sha256')==reward.SUPPORTED_SHA256 and command.get('date')==delta['date'] and
         command.get('force_id')==actor['force_id'] and command.get('district_id')==actor['district_id'],
             'Command identity differs from candidate')
    need(type(command['context_sha256']) is str and len(command['context_sha256'])==64 and
         all(c in '0123456789abcdef' for c in command['context_sha256']) and integer(command['funding_city_id'],1,51),
         'Invalid source command context or city identity')
    ids=command['officer_ids'];need(type(ids) is list and 1<=len(ids)<=16 and
        all(integer(i,1,5999) for i in ids) and ids==sorted(set(ids)),'Exact unique selected officers required')
    people=_unique(before_projection['persons'],'persons');cities=_unique(before_projection['cities'],'cities')
    districts=_unique(before_projection['districts'],'districts')
    city=cities.get(command['funding_city_id']);menu=districts.get(actor['district_id'])
    need(city is not None and menu is not None and menu['valid'] is True and
         city['force_id']==menu['force_id']==actor['force_id'],'Projected command ownership differs')
    charged=districts.get(city['district_id']);need(charged is not None and charged['valid'] is True and
        charged['force_id']==actor['force_id'],'Charged district differs')
    for i in ids:need(i in people and people[i]['force_id']==actor['force_id'] and people[i]['native_valid'] and
        not people[i]['flags']&2 and 1<=people[i]['rank_raw']<=4,'Projected officer is not eligible for this actor')
    expected=dict(funding_city_id=city['id'],gold=100*len(ids),gold_before=city['gold'],gold_if_executed=city['gold']-100*len(ids),
        charged_district_id=charged['id'],action_points=1,actions_before=charged['action_points'],actions_if_executed=charged['action_points']-1)
    need(type(cost) is dict and set(cost)==set(expected)|{'funding_city_name'} and
         all(type(cost[k]) is int and cost[k]==v for k,v in expected.items()) and
         type(cost['funding_city_name']) is str and expected['gold_if_executed']>=0 and expected['actions_if_executed']>=0,
         'Candidate costs differ from exact reward cost')
    need(journal.canonical(validate_effect(before_projection,after,command,dict(expected_costs=cost)))==journal.canonical(effects),
         'Candidate effect differs from projected reward')
    return after
