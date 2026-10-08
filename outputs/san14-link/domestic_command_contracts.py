"""Pure semantic proposals for two statically decoded domestic command kinds.

No game imports, process access, network endpoint, native call or execution
permission. Contexts and evidence are supplied separately by a trusted local
adapter, never accepted from the proposing client. Their provenance cannot be
proved by this parser. A successful result is only a precheck; real native
arguments, rules, lifetimes and execution still need independent verification.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from types import MappingProxyType

PROPOSAL_SCHEMA = 'san14.domestic-proposal.v1'
CONTEXT_SCHEMA = 'san14.domestic-observations.v1'
GAME_SHA256 = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
MAX_TICK = 2**63-1
MAX_RESOURCE = 2**32-1


@dataclass(frozen=True)
class Capability:
    kind: str
    ui_state: str
    semantic_fields: tuple
    required_evidence: tuple = ('eligibility_observation', 'cost_and_duration_quote')
    evidence_level: str = 'static_layout_and_owned_memory_fixtures'
    native_execution_supported: bool = False
    room_routing_connected: bool = False


COMMON_FIELDS = ('kind', 'force_id', 'source_city_id', 'officer_ids')
CAPABILITIES = MappingProxyType({
    'merchant': Capability('merchant', 'CStrategyMerchantState',
                          COMMON_FIELDS+('food_quantity', 'direction')),
    'officer_move': Capability('officer_move', 'CStrategyMoveState',
                              COMMON_FIELDS+('origin_hex_id', 'destination_city_id')),
})


class ContractError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class Precheck:
    status: str
    missing_evidence: tuple
    proposal_sha256: str
    context_sha256: str
    command_sha256: str
    eligibility_evidence_sha256: str = ''
    quote_evidence_sha256: str = ''
    native_execution_supported: bool = False
    authorization_granted: bool = False
    applied_to_game: bool = False
    native_recheck_required: bool = True


def _require(condition, code, message):
    if not condition:
        raise ContractError(code, message)


def _snapshot(value):
    """Copy only bounded plain JSON types, without invoking custom object hooks."""
    budget = [0]
    active = set()

    def copy(item, depth):
        budget[0] += 1
        _require(depth <= 16 and budget[0] <= 100000, 'shape', 'Input nesting or size exceeds the contract')
        if type(item) in (str, int, bool) or item is None:
            if type(item) is str:
                _require(len(item) <= 4096, 'shape', 'String exceeds contract limit')
            return item
        _require(type(item) in (dict, list), 'shape', 'Only plain JSON objects and arrays are accepted')
        identity = id(item)
        _require(identity not in active, 'shape', 'Cyclic input')
        active.add(identity)
        try:
            if type(item) is list:
                _require(len(item) <= 10000, 'shape', 'Array exceeds contract limit')
                return [copy(v, depth+1) for v in item]
            _require(len(item) <= 64 and all(type(k) is str for k in item), 'shape', 'Object keys differ from contract')
            return {k: copy(v, depth+1) for k, v in item.items()}
        finally:
            active.remove(identity)
    return copy(value, 0)


def _keys(value, fields, label):
    _require(type(value) is dict and set(value) == set(fields), 'shape', label+' fields differ from contract')


def _integer(value, low, high, label):
    _require(type(value) is int and low <= value <= high, 'integer', label+' is not a supported integer')
    return value


def _hex(value, size, label):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{'+str(size)+'}', value) is not None
             and value != '0'*size, 'digest', label+' must be a nonzero lowercase hex value')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def _date(value):
    _keys(value, ('year', 'month', 'day'), 'date')
    _integer(value['year'], 1, 9999, 'year')
    _integer(value['month'], 1, 12, 'month')
    _integer(value['day'], 1, 21, 'day')
    _require(value['day'] in (1, 11, 21), 'date', 'Only planning-period dates are represented')


def _officer_ids(value):
    _require(type(value) is list and 1 <= len(value) <= 5999, 'officers', 'A nonempty bounded officer list is required')
    for identity in value:
        _integer(identity, 1, 5999, 'officer ID')
    _require(len(set(value)) == len(value), 'duplicate_officer', 'An officer cannot occur twice')


def _command(value):
    _require(type(value) is dict and type(value.get('kind')) is str and value['kind'] in CAPABILITIES,
             'unsupported_kind', 'Only merchant and officer_move proposals are defined')
    _keys(value, CAPABILITIES[value['kind']].semantic_fields, 'command')
    _integer(value['force_id'], 1, 51, 'force ID')
    _integer(value['source_city_id'], 1, 51, 'source city ID')
    _officer_ids(value['officer_ids'])
    if value['kind'] == 'merchant':
        _integer(value['food_quantity'], 1, 2**31-1, 'food quantity')
        _require(type(value['direction']) is str and value['direction'] in ('buy_food', 'sell_food'),
                 'direction', 'Unknown merchant direction')
    else:
        _integer(value['origin_hex_id'], 0, 48399, 'origin hex ID')
        _integer(value['destination_city_id'], 1, 51, 'destination city ID')


def command_fingerprint(command_preview):
    """Address-free semantic identity. Officer ordering is deliberately retained."""
    command = _snapshot(command_preview)
    _command(command)
    return _digest({'schema': PROPOSAL_SCHEMA, 'command': command})


CONTEXT_FIELDS = ('schema', 'game_sha256', 'context_id', 'phase', 'date',
                  'captured_at_tick', 'expires_at_tick', 'actor_force_id',
                  'cities', 'districts', 'officers', 'eligibility_observations', 'quotes')
EVIDENCE_FIELDS = ('context_id', 'command_sha256', 'observed_at_tick',
                   'expires_at_tick', 'evidence_sha256')
QUOTE_FIELDS = EVIDENCE_FIELDS+('funding_city_id', 'charged_district_id',
    'gold_debit', 'gold_credit', 'food_debit', 'food_credit', 'action_points', 'duration_days')


def _records(values, fields, maximum, label):
    _require(type(values) is list and len(values) <= maximum, 'shape', label+' list exceeds contract')
    result = {}
    for row in values:
        _keys(row, fields, label)
        identity = _integer(row['id'], 1, maximum, label+' ID')
        _require(identity not in result, 'duplicate_identity', 'Duplicate '+label+' ID')
        result[identity] = row
    return result


def _evidence(row, context):
    _require(row['context_id'] == context['context_id'], 'evidence_binding', 'Evidence belongs to another context')
    _hex(row['command_sha256'], 64, 'evidence command digest')
    _hex(row['evidence_sha256'], 64, 'evidence source digest')
    _integer(row['observed_at_tick'], context['captured_at_tick'], context['expires_at_tick']-1, 'evidence observation tick')
    _integer(row['expires_at_tick'], row['observed_at_tick']+1, context['expires_at_tick'], 'evidence expiry tick')


def _context(context):
    _keys(context, CONTEXT_FIELDS, 'context')
    _require(context['schema'] == CONTEXT_SCHEMA and context['game_sha256'] == GAME_SHA256,
             'version', 'Context schema or supported game build differs')
    _hex(context['context_id'], 32, 'context ID')
    _require(context['phase'] == 'PLANNING', 'phase', 'Context must describe planning')
    _date(context['date'])
    _integer(context['captured_at_tick'], 0, MAX_TICK-1, 'context observation tick')
    _integer(context['expires_at_tick'], context['captured_at_tick']+1, MAX_TICK, 'context expiry tick')
    _integer(context['actor_force_id'], 1, 51, 'context actor force')
    districts = _records(context['districts'], ('id', 'force_id', 'action_points'), 51, 'district')
    cities = _records(context['cities'], ('id', 'force_id', 'district_id', 'gold', 'food'), 51, 'city')
    officers = _records(context['officers'], ('id', 'force_id', 'district_id'), 5999, 'officer')
    for row in districts.values():
        _integer(row['force_id'], 1, 51, 'district force')
        _integer(row['action_points'], 0, 255, 'district action points')
    for row in list(cities.values())+list(officers.values()):
        _integer(row['force_id'], 1, 51, 'object force')
        district = _integer(row['district_id'], 1, 51, 'object district')
        _require(district in districts and districts[district]['force_id'] == row['force_id'],
                 'context_relationship', 'Object district/force relationship is inconsistent')
    for row in cities.values():
        for field in ('gold', 'food'):
            _integer(row[field], 0, MAX_RESOURCE, 'city '+field)
    for field in ('eligibility_observations', 'quotes'):
        _require(type(context[field]) is list and len(context[field]) <= 128, 'shape', field+' list exceeds contract')
        seen = set()
        for row in context[field]:
            _keys(row, EVIDENCE_FIELDS+('officer_ids', 'decision') if field == 'eligibility_observations' else QUOTE_FIELDS, field)
            _evidence(row, context)
            _require(row['command_sha256'] not in seen, 'ambiguous_evidence', 'Multiple evidence records for one command')
            seen.add(row['command_sha256'])
            if field == 'eligibility_observations':
                _officer_ids(row['officer_ids'])
                _require(type(row['decision']) is str and row['decision'] in ('eligible', 'ineligible'),
                         'eligibility', 'Unverified eligibility must be omitted, not asserted')
            else:
                _integer(row['funding_city_id'], 1, 51, 'quoted funding city')
                _integer(row['charged_district_id'], 1, 51, 'quoted charged district')
                for cost in ('gold_debit', 'gold_credit', 'food_debit', 'food_credit'):
                    _integer(row[cost], 0, MAX_RESOURCE, 'quoted '+cost)
                _integer(row['action_points'], 0, 2**31-1, 'quoted action cost')
                _integer(row['duration_days'], 0, 2**31-1, 'quoted duration')
    return cities, districts, officers


def context_fingerprint(trusted_context):
    """Integrity binding only; a hash does not authenticate a context's author."""
    context = _snapshot(trusted_context)
    _context(context)
    return _digest(context)


def proposal_from_preview(command_preview, trusted_context, *, proposal_id):
    """Copy DomesticDecoder's command_preview into a versioned proposal.

    Does not capture menus, grant permission, or require evidence to already
    exist. Refreshing trusted observations requires constructing a new proposal.
    """
    command, context = _snapshot(command_preview), _snapshot(trusted_context)
    _command(command)
    _context(context)
    _hex(proposal_id, 32, 'proposal ID')
    return {'schema': PROPOSAL_SCHEMA, 'game_sha256': GAME_SHA256, 'proposal_id': proposal_id,
            'context_id': context['context_id'], 'context_sha256': _digest(context),
            'date': dict(context['date']), 'command': command}


def validate_proposal(proposal, trusted_context, *, authorized_force_id, now_tick):
    """Validate a proposal against a separate immutable-in-this-call snapshot.

    authorized_force_id comes from authenticated server binding. now_tick and
    all evidence ticks use the trusted adapter's same local monotonic clock;
    remote timestamps are not interchangeable. Missing/expired evidence returns
    NEEDS_EVIDENCE. Malformed, unauthorized, stale or known-ineligible inputs
    raise ContractError. PRECHECK_ONLY never permits a native call.
    """
    proposal, context = _snapshot(proposal), _snapshot(trusted_context)
    _keys(proposal, ('schema', 'game_sha256', 'proposal_id', 'context_id',
                     'context_sha256', 'date', 'command'), 'proposal')
    _require(proposal['schema'] == PROPOSAL_SCHEMA and proposal['game_sha256'] == GAME_SHA256,
             'version', 'Proposal schema or supported game build differs')
    _hex(proposal['proposal_id'], 32, 'proposal ID')
    _hex(proposal['context_id'], 32, 'proposal context ID')
    _hex(proposal['context_sha256'], 64, 'proposal context digest')
    _date(proposal['date'])
    command = proposal['command']
    _command(command)
    cities, districts, officers = _context(context)
    _integer(authorized_force_id, 1, 51, 'authenticated force')
    _integer(now_tick, 0, MAX_TICK, 'local monotonic tick')
    _require(context['captured_at_tick'] <= now_tick < context['expires_at_tick'],
             'stale_context', 'Context is expired or from the future')
    _require(proposal['context_id'] == context['context_id'] and proposal['context_sha256'] == _digest(context)
             and proposal['date'] == context['date'], 'stale_context', 'Proposal is based on another context')
    _require(command['force_id'] == authorized_force_id == context['actor_force_id'],
             'authorization', 'Command force is not the authenticated context actor')
    city_ids = [command['source_city_id']]
    if command['kind'] == 'officer_move':
        city_ids.append(command['destination_city_id'])
    for identity in city_ids:
        _require(identity in cities and cities[identity]['force_id'] == authorized_force_id,
                 'city_owner', 'Command city is missing or belongs to another force')
    for identity in command['officer_ids']:
        _require(identity in officers and officers[identity]['force_id'] == authorized_force_id,
                 'officer_owner', 'Command officer is missing or belongs to another force')
    semantic = command_fingerprint(command)
    missing = []
    eligibility_hash = quote_hash = ''
    observed = next((r for r in context['eligibility_observations'] if r['command_sha256'] == semantic), None)
    if observed is None:
        missing.append('eligibility_observation')
    elif not observed['observed_at_tick'] <= now_tick < observed['expires_at_tick']:
        missing.append('current_eligibility_observation')
    else:
        _require(observed['officer_ids'] == command['officer_ids'], 'evidence_binding', 'Eligibility officer ordering differs')
        _require(observed['decision'] == 'eligible', 'ineligible', 'Trusted observation rejects this selection')
        eligibility_hash = observed['evidence_sha256']
    quote = next((r for r in context['quotes'] if r['command_sha256'] == semantic), None)
    if quote is None:
        missing.append('cost_and_duration_quote')
    elif not quote['observed_at_tick'] <= now_tick < quote['expires_at_tick']:
        missing.append('current_cost_and_duration_quote')
    else:
        funding, charged = cities.get(quote['funding_city_id']), districts.get(quote['charged_district_id'])
        _require(funding is not None and funding['force_id'] == authorized_force_id and charged is not None
                 and charged['force_id'] == authorized_force_id, 'quote_owner', 'Quoted funding is not owned by the actor')
        for resource in ('gold', 'food'):
            debit, credit = quote[resource+'_debit'], quote[resource+'_credit']
            _require(funding[resource] >= debit, 'insufficient_resources', 'Insufficient quoted '+resource)
            _require(funding[resource]-debit+credit <= MAX_RESOURCE, 'resource_overflow', 'Quoted '+resource+' exceeds field capacity')
        _require(charged['action_points'] >= quote['action_points'], 'insufficient_actions', 'Insufficient quoted action points')
        quote_hash = quote['evidence_sha256']
    return Precheck('NEEDS_EVIDENCE' if missing else 'PRECHECK_ONLY', tuple(missing),
                    _digest(proposal), _digest(context), semantic, eligibility_hash, quote_hash)
