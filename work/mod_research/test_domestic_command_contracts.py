"""Pure Python/owned-memory cases; no private archives or game instances."""
import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import traceback

P = Path(__file__).resolve().parent
PUBLIC = P.parents[1]/'outputs'/'san14-link'
sys.path.insert(0, str(PUBLIC))
import domestic_command_contracts as d


def merchant():
    return dict(kind='merchant', force_id=12, source_city_id=19,
                officer_ids=[666, 97], food_quantity=1200, direction='buy_food')


def move():
    return dict(kind='officer_move', force_id=12, source_city_id=19,
                officer_ids=[666, 97], origin_hex_id=13242, destination_city_id=18)


def context():
    return dict(schema=d.CONTEXT_SCHEMA, game_sha256=d.GAME_SHA256,
        context_id='1'*32, phase='PLANNING', date=dict(year=203, month=8, day=11),
        captured_at_tick=100, expires_at_tick=300, actor_force_id=12,
        districts=[dict(id=11, force_id=12, action_points=18), dict(id=2, force_id=2, action_points=10)],
        cities=[dict(id=19, force_id=12, district_id=11, gold=800, food=2400),
                dict(id=18, force_id=12, district_id=11, gold=900, food=3000),
                dict(id=13, force_id=2, district_id=2, gold=2000, food=5000)],
        officers=[dict(id=666, force_id=12, district_id=11), dict(id=97, force_id=12, district_id=11),
                  dict(id=952, force_id=2, district_id=2)], eligibility_observations=[], quotes=[])


def evidence(command, c):
    """Invented fixture observations only, never asserted as a game rule."""
    common=dict(context_id=c['context_id'], command_sha256=d.command_fingerprint(command),
                observed_at_tick=100, expires_at_tick=250)
    c['eligibility_observations']=[dict(common, evidence_sha256='2'*64,
        officer_ids=command['officer_ids'].copy(), decision='eligible')]
    c['quotes']=[dict(common, evidence_sha256='3'*64, funding_city_id=19, charged_district_id=11,
        gold_debit=137, gold_credit=0, food_debit=0, food_credit=1200,
        action_points=2, duration_days=7)]
    return c


def proposal(command, c):
    return d.proposal_from_preview(command, c, proposal_id='4'*32)


def check(p, c, **kwargs):
    r=d.validate_proposal(p, c, authorized_force_id=kwargs.get('authority', 12), now_tick=kwargs.get('now', 150))
    assert r.native_execution_supported is False and r.authorization_granted is False
    assert r.applied_to_game is False and r.native_recheck_required is True
    return r


def reject(fn, code=None):
    try:
        fn()
    except d.ContractError as error:
        assert code is None or error.code == code, (error.code, code, str(error))
        return
    raise AssertionError('Expected contract rejection')


def cases():
    yield 'missing-evidence-is-explicit', lambda: missing_case()
    yield 'merchant-quoted-precheck-only', lambda: quoted_case(merchant())
    yield 'move-quoted-precheck-only', lambda: quoted_case(move())
    yield 'sell-preview-retains-semantics', lambda: quoted_case(dict(merchant(), direction='sell_food'))
    yield 'actual-preview-kind-list-compatibility', preview_capabilities
    yield 'actual-decoder-owned-merchant-preview-composition', lambda:decoder_composition('merchant')
    yield 'actual-decoder-owned-move-preview-composition', lambda:decoder_composition('officer_move')
    yield 'capabilities-and-results-immutable', immutable_case
    yield 'proposal-does-not-alias-inputs', copied_case
    yield 'validator-does-not-change-inputs', unchanged_case
    yield 'context-digest-canonical-key-order', canonical_case
    for field,value in [('force_id',True), ('source_city_id',True), ('officer_ids',[True]),
                        ('food_quantity',True), ('food_quantity',0), ('food_quantity',2**31),
                        ('food_quantity',1.2), ('officer_ids',[97,97]), ('officer_ids',[]),
                        ('direction','unknown'), ('officer_ids',[6000]), ('source_city_id',0)]:
        yield 'invalid-merchant-'+field+'-'+repr(value), lambda f=field,v=value: reject(lambda:proposal(dict(merchant(), **{f:v}), context()))
    for field,value in [('origin_hex_id',True), ('origin_hex_id',None), ('origin_hex_id',48400),
                        ('destination_city_id',None), ('destination_city_id',52)]:
        yield 'invalid-move-'+field+'-'+repr(value), lambda f=field,v=value: reject(lambda:proposal(dict(move(), **{f:v}),context()))
    for kind in ('reward','government','employ','search','recruit','training'):
        yield 'unsupported-kind-'+kind, lambda k=kind: reject(lambda:proposal(dict(merchant(),kind=k),context()),'unsupported_kind')
    yield 'unknown-command-pointer-key', lambda:reject(lambda:proposal(dict(merchant(),native_address=0x140001000),context()),'shape')
    yield 'unknown-proposal-quote-key', extra_proposal_case
    yield 'unknown-context-pointer-key', extra_context_case
    yield 'context-resource-change-rejects-old-proposal', stale_case
    yield 'other-context-id-rejects-old-proposal', context_id_case
    yield 'wrong-date', date_case
    yield 'expired-context-boundary', lambda:clock_case(300)
    yield 'future-context', lambda:clock_case(99)
    yield 'boolean-clock', lambda:clock_case(True)
    yield 'wrong-build', build_case
    yield 'wrong-version', version_case
    yield 'wrong-phase', phase_case
    yield 'authenticated-force-cannot-be-overridden', authority_case
    yield 'context-actor-cannot-be-overridden', actor_case
    yield 'foreign-source-city', lambda:ownership_case(dict(merchant(),source_city_id=13),'city_owner')
    yield 'foreign-move-destination', lambda:ownership_case(dict(move(),destination_city_id=13),'city_owner')
    yield 'foreign-officer', lambda:ownership_case(dict(merchant(),officer_ids=[952]),'officer_owner')
    yield 'missing-officer', lambda:ownership_case(dict(merchant(),officer_ids=[222]),'officer_owner')
    yield 'inconsistent-object-district', relationship_case
    yield 'duplicate-context-officer', duplicate_context_case
    yield 'trusted-ineligible-selection', lambda:evidence_mutation('eligibility_observations','decision','ineligible','ineligible')
    yield 'boolean-eligibility-is-not-proof', lambda:evidence_mutation('eligibility_observations','decision',True,'eligibility')
    yield 'eligibility-order-binding', lambda:evidence_mutation('eligibility_observations','officer_ids',[97,666],'evidence_binding')
    yield 'quote-foreign-context', lambda:evidence_mutation('quotes','context_id','5'*32,'evidence_binding')
    yield 'unverified-quote-source', lambda:evidence_mutation('quotes','evidence_sha256','0'*64,'digest')
    yield 'boolean-action-cost', lambda:evidence_mutation('quotes','action_points',True,'integer')
    yield 'negative-duration', lambda:evidence_mutation('quotes','duration_days',-1,'integer')
    yield 'unaffordable-gold', lambda:evidence_mutation('quotes','gold_debit',801,'insufficient_resources')
    yield 'unaffordable-food', lambda:evidence_mutation('quotes','food_debit',2401,'insufficient_resources')
    yield 'unaffordable-actions', lambda:evidence_mutation('quotes','action_points',19,'insufficient_actions')
    yield 'resource-overflow', lambda:evidence_mutation('quotes','food_credit',d.MAX_RESOURCE,'resource_overflow')
    yield 'foreign-quoted-funding', lambda:evidence_mutation('quotes','funding_city_id',13,'quote_owner')
    yield 'foreign-quoted-action-district', lambda:evidence_mutation('quotes','charged_district_id',2,'quote_owner')
    yield 'ambiguous-quote', duplicate_quote_case
    yield 'changed-quantity-cannot-reuse-quote', different_command_case
    yield 'expired-evidence-explicit-missing', expired_evidence_case
    yield 'future-evidence-explicit-missing', future_evidence_case
    yield 'one-missing-evidence-does-not-mask-known-resource-rejection', missing_and_invalid_case
    yield 'quoted-costs-and-duration-are-not-hardcoded', quote_values_case
    yield 'shared-input-container-does-not-become-shared-output', shared_case
    yield 'cyclic-input-rejected', cyclic_case
    yield 'tuple-input-rejected', tuple_case


def missing_case():
    c=context();r=check(proposal(merchant(),c),c)
    assert r.status=='NEEDS_EVIDENCE' and r.missing_evidence==('eligibility_observation','cost_and_duration_quote')


def quoted_case(command):
    c=evidence(command,context());r=check(proposal(command,c),c)
    assert r.status=='PRECHECK_ONLY' and not r.missing_evidence
    assert r.eligibility_evidence_sha256=='2'*64 and r.quote_evidence_sha256=='3'*64


def preview_capabilities():
    tree=ast.parse((PUBLIC/'domestic_reader.py').read_text(encoding='utf-8'))
    states=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='SUPPORTED_STATES' for t in n.targets))
    assert set(d.CAPABILITIES)=={'merchant','officer_move'}
    for name,cap in d.CAPABILITIES.items():
        assert states[cap.ui_state]==name and not cap.native_execution_supported and not cap.room_routing_connected


def decoder_composition(kind):
    # Reuse the existing decoder's own bytearray fixture, not a copied decoder.
    # Imports only define the live-reader classes; guard their active APIs too.
    from unittest.mock import patch
    import test_domestic_reader as prior
    import game_reader
    import readonly_probe
    with patch.object(game_reader.GameReader,'__init__',side_effect=AssertionError('No live reader')) as live, \
         patch.object(game_reader,'find_game_pid',side_effect=AssertionError('No process discovery')) as lookup, \
         patch.object(readonly_probe,'find_game_pid',side_effect=AssertionError('No process discovery')) as other, \
         patch.object(readonly_probe.Memory,'__init__',side_effect=AssertionError('No process memory')) as memory:
        fixture=prior.Fixture(kind);captured=fixture.capture();command=captured['command_preview'];c=context()
        decoder=prior.DomesticDecoder(fixture)
        city_ids=[command['source_city_id']]+([command['destination_city_id']] if kind=='officer_move' else [])
        c['cities']=[{k:row[k] for k in ('id','force_id','district_id','gold','food')}
                     for row in (decoder.city_at(fixture.cities[i]) for i in city_ids)]
        c['districts']=[{k:captured['district'][k] for k in ('id','force_id','action_points')}]
        c['officers']=[{k:row[k] for k in ('id','force_id','district_id')} for row in captured['officers']]
        r=check(proposal(command,c),c)
        assert captured['basic_ownership_matches'] and not captured['replay_supported']
        assert r.status=='NEEDS_EVIDENCE' and len(r.missing_evidence)==2
        assert not any(mock.called for mock in (live,lookup,other,memory))


def immutable_case():
    try:d.CAPABILITIES['reward']=d.CAPABILITIES['merchant']
    except TypeError:pass
    else:raise AssertionError('Capabilities mutable')
    for obj,field,value in [(d.CAPABILITIES['merchant'],'native_execution_supported',True),
                            (check(proposal(merchant(),context()),context()),'authorization_granted',True)]:
        try:setattr(obj,field,value)
        except FrozenInstanceError:pass
        else:raise AssertionError('Frozen record mutable')


def copied_case():
    command=merchant();c=context();p=proposal(command,c);before=deepcopy(p)
    command['officer_ids'][0]=952;c['date']['year']=999
    assert p==before


def unchanged_case():
    c=evidence(move(),context());p=proposal(move(),c);cp,pp=deepcopy(c),deepcopy(p);r=check(p,c)
    assert c==cp and p==pp
    c['quotes'][0]['evidence_sha256']='8'*64;p['command']['officer_ids'][0]=952
    assert r.quote_evidence_sha256=='3'*64 and r.command_sha256==d.command_fingerprint(move())


def canonical_case():
    c=context();p=proposal(merchant(),c)
    assert check(p,dict(reversed(list(c.items())))).context_sha256==d.context_fingerprint(c)


def extra_proposal_case():
    c=context();p=proposal(merchant(),c);p['trusted_quote']={}
    reject(lambda:check(p,c),'shape')


def extra_context_case():
    c=context();c['cities'][0]['address']=0x140000000
    reject(lambda:proposal(merchant(),c),'shape')


def stale_case():
    c=context();p=proposal(merchant(),c);c['cities'][0]['gold']+=1
    reject(lambda:check(p,c),'stale_context')


def context_id_case():
    c=context();p=proposal(merchant(),c);c['context_id']='9'*32
    reject(lambda:check(p,c),'stale_context')


def date_case():
    c=context();p=proposal(merchant(),c);p['date']['day']=21
    reject(lambda:check(p,c),'stale_context')


def clock_case(now):
    c=context();reject(lambda:check(proposal(merchant(),c),c,now=now),'integer' if type(now) is bool else 'stale_context')


def build_case():
    c=context();p=proposal(merchant(),c);p['game_sha256']='8'*64
    reject(lambda:check(p,c),'version')


def version_case():
    c=context();p=proposal(merchant(),c);p['schema']='future'
    reject(lambda:check(p,c),'version')


def phase_case():
    c=context();c['phase']='SIMULATING';reject(lambda:proposal(merchant(),c),'phase')


def authority_case():
    c=context();reject(lambda:check(proposal(merchant(),c),c,authority=2),'authorization')


def actor_case():
    c=context();c['actor_force_id']=2;reject(lambda:check(proposal(merchant(),c),c),'authorization')


def ownership_case(command,code):
    c=context();reject(lambda:check(proposal(command,c),c),code)


def relationship_case():
    c=context();c['cities'][0]['district_id']=2;reject(lambda:proposal(merchant(),c),'context_relationship')


def duplicate_context_case():
    c=context();c['officers'].append(c['officers'][0].copy());reject(lambda:proposal(merchant(),c),'duplicate_identity')


def evidence_mutation(section,field,value,code):
    c=evidence(merchant(),context());c[section][0][field]=value
    reject(lambda:check(proposal(merchant(),c),c),code)


def duplicate_quote_case():
    c=evidence(merchant(),context());c['quotes'].append(c['quotes'][0].copy())
    reject(lambda:proposal(merchant(),c),'ambiguous_evidence')


def different_command_case():
    c=evidence(merchant(),context());r=check(proposal(dict(merchant(),food_quantity=1201),c),c)
    assert r.status=='NEEDS_EVIDENCE' and len(r.missing_evidence)==2


def expired_evidence_case():
    c=evidence(merchant(),context());r=check(proposal(merchant(),c),c,now=250)
    assert r.missing_evidence==('current_eligibility_observation','current_cost_and_duration_quote')


def future_evidence_case():
    c=evidence(merchant(),context())
    for section in ('quotes','eligibility_observations'):c[section][0]['observed_at_tick']=151
    r=check(proposal(merchant(),c),c)
    assert len(r.missing_evidence)==2


def missing_and_invalid_case():
    c=evidence(merchant(),context());c['eligibility_observations']=[];c['quotes'][0]['gold_debit']=801
    reject(lambda:check(proposal(merchant(),c),c),'insufficient_resources')


def quote_values_case():
    c=evidence(move(),context());c['quotes'][0].update(action_points=0,duration_days=5,gold_debit=0,food_credit=0)
    first=check(proposal(move(),c),c);c['quotes'][0].update(action_points=3,duration_days=9,gold_debit=800)
    second=check(proposal(move(),c),c)
    assert first.status==second.status=='PRECHECK_ONLY' and first.context_sha256!=second.context_sha256


def shared_case():
    c=context();command=merchant();p=proposal(command,c)
    assert p['command']['officer_ids'] is not command['officer_ids'] and p['date'] is not c['date']


def cyclic_case():
    command=merchant();command['officer_ids'].append(command)
    reject(lambda:proposal(command,context()),'shape')


def tuple_case():
    reject(lambda:proposal(dict(merchant(),officer_ids=(666,97)),context()),'shape')


def main():
    source_paths=[Path(__file__).resolve(), P/'test_domestic_reader.py']
    source_paths += [PUBLIC/name for name in ('domestic_command_contracts.py','domestic_reader.py',
                                            'game_reader.py','sortie_reader.py','readonly_probe.py')]
    hashes={str(p.relative_to(P.parents[1])).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    run=P/'domestic_command_contracts_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(schema='san14.domestic-command-contracts-tests.v1', result='FAIL', cases=[], sources=hashes,
        game_access=False, private_inputs=False, native_execution=False, network_execution=False,
        observations_are_models=True, production_permit=False)
    for name,fn in cases():
        try:fn();row=dict(case=name,result='PASS')
        except Exception as error:row=dict(case=name,result='FAIL',error=repr(error),traceback=traceback.format_exc())
        result['cases'].append(row)
    unchanged=all(hashlib.sha256((P.parents[1]/name).read_bytes()).hexdigest()==value for name,value in hashes.items())
    result.update(sources_unchanged=unchanged, count=len(result['cases']))
    if unchanged and all(row['result']=='PASS' for row in result['cases']):result['result']='PASS'
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'],cases=result['count'],path=str(run/'result.json'))))
    for row in result['cases']:
        if row['result']=='FAIL':print(json.dumps(row))
    return int(result['result']!='PASS')


if __name__=='__main__':raise SystemExit(main())
