"""Authenticated finite observations, deliberately separate from held-fence RPC.

These statements describe samples under an explicit human no-command condition.
Neither the signature nor the schema proves native execution or continuous pause.
"""
import base64
from dataclasses import asdict, is_dataclass
import hashlib
import hmac
import json
import zlib

from authoritative_sync import canonical, digest, hexid
from b_warm_profile_contract import Profile, Date, validate_profile
from b_warm_remote_completion import key_check, MAX_RAW

ACTION = 'observed_adapter_completion_v1'
DOMAIN = b'san14.observed-partial-completion.v1\0'
CONTRACT = 'san14.no-new-command-observed-boundary.v1'
RESULT = 'OBSERVED_REMOTE_PARTIAL_LOADED'
COVERAGE = dict(human_no_new_commands=True, input_exclusion_proven=False,
                scheduler_fence_proven=False, atomic_snapshot=False)


def need(ok, text):
    if not ok:
        raise ValueError(text)


def packet(key, value):
    key_check(key)
    raw = canonical(value)
    need(type(value) is dict and len(raw) <= MAX_RAW, 'Bounded observation packet required')
    packed = zlib.compress(raw)
    result = dict(action=ACTION, payload=base64.b64encode(packed).decode('ascii'),
                  mac=hmac.new(key, DOMAIN+packed, hashlib.sha256).hexdigest())
    need(len(canonical(result)) < 65000, 'Observation packet exceeds TLS frame')
    return result


def unpack(key, value):
    key_check(key)
    need(type(value) is dict and set(value) == {'action','payload','mac'} and value['action'] == ACTION,
         'Explicit observed-boundary action required')
    packed = base64.b64decode(value['payload'], validate=True)
    need(len(packed) < 48000 and type(value['mac']) is str and
         hmac.compare_digest(value['mac'], hmac.new(key, DOMAIN+packed, hashlib.sha256).hexdigest()),
         'Observed-boundary authentication failed')
    d = zlib.decompressobj()
    raw = d.decompress(packed, MAX_RAW+1)
    need(len(raw) <= MAX_RAW and d.eof and not d.unused_data and not d.unconsumed_tail,
         'Unbounded/noncanonical observation payload')
    result = json.loads(raw)
    need(type(result) is dict and canonical(result) == raw, 'Canonical observation body required')
    return result


def expected_profile(profile, kind, side):
    need(type(profile) is Profile, 'Typed original native profile required')
    validate_profile(profile)
    need(kind in ('begin','complete') and side in ('A','B'), 'Explicit boundary side/stage required')
    p = Profile.from_buffer_copy(bytes(profile))
    if side == 'B' and kind == 'complete':
        p.before = Date(p.loaded.year, p.loaded.month, p.loaded.day)
        p.currentForce = p.target.force
    return p


def _binding(context, profile, kind, side):
    p = expected_profile(profile, kind, side)
    m = context['manifest']
    need(digest(m) == context['checkpoint_id'] and m['scope_sha256'] == digest(context['scope']),
         'Boundary checkpoint/scope differs')
    need(m['node'] == dict(year=profile.loaded.year,month=profile.loaded.month,
                          day=profile.loaded.day,phase='PLANNING_BOUNDARY'), 'Manifest/profile date differs')
    if side == 'A':
        node, force, ruler = m['node'], profile.source.force, profile.source.ruler
    else:
        node = dict(year=p.before.year,month=p.before.month,day=p.before.day,phase='PLANNING_BOUNDARY')
        force = p.currentForce
        ruler = p.source.ruler if force == p.source.force else p.target.ruler
    return dict(schema=CONTRACT,side=side,kind=kind,scope_sha256=digest(context['scope']),
        epoch=m['epoch'],period=m['period'],checkpoint_id=context['checkpoint_id'],
        profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),
        observed_profile_sha256=hashlib.sha256(bytes(p)).hexdigest(),
        node=node,force=force,ruler=ruler,**COVERAGE)


def boundary_envelope(observation, context, profile, kind, *, side='B'):
    local = asdict(observation) if is_dataclass(observation) and not isinstance(observation,type) else observation
    need(type(local) is dict and all(type(local.get(k)) is bool and local[k] is v for k,v in COVERAGE.items()),
         'Finite typed observation cannot claim an execution fence')
    value = _binding(context, profile, kind, side)
    need(local.get('profile_sha256') == value['observed_profile_sha256'],
         'Actual observed profile differs from stage')
    # Optional explicit A date/viewer observations must agree with the context.
    for k in ('node','force','ruler'):
        if k in local:
            need(local[k] == value[k], 'Actual observed '+k+' differs')
    date_fields = ('year','month','day')
    if any(k in local for k in date_fields):
        need(all(type(local.get(k)) is int and local[k] == value['node'][k] for k in date_fields),
             'Actual observed date differs or is incomplete')
    value.update({k:local.get(k) for k in ('sequence','pid','birth','sample_sha256')})
    return validate_boundary(value,context,profile,kind,side=side)


def validate_boundary(value, context, profile, kind, *, side='B', native=None):
    binding = _binding(context,profile,kind,side)
    need(type(value) is dict and set(value) == set(binding)|{'sequence','pid','birth','sample_sha256'},
         'Exact observed-boundary fields required')
    need(canonical({k:value[k] for k in binding}) == canonical(binding), 'Observed boundary context/coverage differs')
    need(type(value['sequence']) is int and 0 < value['sequence'] < 2**53 and
         type(value['pid']) is int and 0 < value['pid'] < 2**32 and
         type(value['birth']) is int and 0 < value['birth'] < 2**64 and
         hexid(value['sample_sha256']) and int(value['sample_sha256'],16), 'Bad observation provenance')
    if native is not None:
        need((value['pid'],value['birth']) == (native['pid'],native['birth']),
             'Observation and native completion process differ')
    return json.loads(canonical(value))


def advances(previous, current):
    """A new sample of the same retained process, not a replay of a success flag."""
    if previous is not None:
        need((previous['pid'],previous['birth']) == (current['pid'],current['birth']) and
             current['sequence'] > previous['sequence'], 'Observed process changed or sample replayed')
    return current
