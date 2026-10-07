"""Pure-Python synthetic acceptance/negative tests. Never a live-load claim."""
from __future__ import annotations
import copy
import ctypes as C
import datetime
import hashlib
import json
from pathlib import Path
import struct
from checkpoint_complete_live_acceptance import validate_report, GAME_SHA, SLOTS, ORIGINALS
import checkpoint_complete_live_owner_contract as wire
from checkpoint_live_prefetch_contract import HardwareReceipt

ROOT = Path(__file__).resolve().parent
SEED = ROOT / 'checkpoint_complete_live_owner_smoke/20261007-152554-825501/success-new/report.bin'
SEED_REFUSAL = ROOT / 'checkpoint_complete_live_owner_smoke/20261007-152525-850869/report.bin'
TYPES = {'bytes': (wire.BytesReceipt, 'bytesReceipt'), 'lifecycle': (wire.LifecycleReceipt, 'lifecycleReceipt'),
         'identity': (wire.IdentityReceipt, 'identityReceipt'), 'hardware': (HardwareReceipt, 'hardwareReceipt')}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def pack_object(typ, data):
    obj = typ()
    for key, field in obj._fields_:
        value = data[key]
        if issubclass(field, C.Structure):
            setattr(obj, key, pack_object(field, value))
        elif issubclass(field, C.Array):
            if field._type_ is C.c_char:
                setattr(obj, key, value.encode('ascii'))
            else:
                getattr(obj, key)[:] = bytes.fromhex(value) if field._type_ is C.c_uint8 else value
        else:
            setattr(obj, key, value)
    return obj

def sync_pods(data):
    for name, (typ, field) in TYPES.items():
        data['receipts'][field] = bytes(pack_object(typ, data[name])).hex()

def report_bytes(data):
    obj = wire.Report()
    obj.magic, obj.size, obj.version = wire.MAGIC, C.sizeof(wire.Report), wire.VERSION
    obj.sequence, obj.attempt, obj.epoch = data['sequence'], data['attempt'], data['epoch']
    for n, key in enumerate(wire.VALUE_NAMES): obj.value[n] = data[key]
    for n, h in enumerate(data['hooks']): obj.hooks[n] = pack_object(wire.HookReceipt, h)
    for n, h in enumerate(data['bridges']): obj.bridges[n] = pack_object(wire.BridgeReceipt, h)
    for name, (_, field) in TYPES.items(): getattr(obj, field)[:] = bytes.fromhex(data['receipts'][field])
    obj.requestReadSha[:] = bytes.fromhex(data['requestReadSha'])
    for key in ('requestStage', 'planningFailure'): setattr(obj, key, data[key].encode('ascii'))
    for key in ('planningAttempt', 'planningEpoch', 'planningUserCall', 'planningIdentityCall', 'planningCompletedCall', 'planningUser'):
        setattr(obj, key, data[key])
    for key in ('planningBeforeSample', 'planningAfterSample'):
        row = data[key]
        values = row['states'] + [row[n] for n in ('stack', 'root', 'world', 'force', 'ruler', 'district', 'cache', 'worker', 'toolbar', 'panel', 'uiForceContext')]
        getattr(obj, key)[:] = struct.pack('<15QI4x', *values)
    return bytes(obj)

def synthetic():
    # Reuse a real owned fixture's POD shape, then explicitly synthesize the
    # production environment and installation facts. This is classifier data,
    # never evidence that these facts happened together in a running process.
    r = wire.decode_report(SEED.read_bytes())
    base, attempt, epoch, generation = 0x140000000, r['attempt'], r['epoch'], 17
    r.update(OwnerState=2, SessionState=8, StopRequested=0, RestoreCalls=0, QueueStopped=0, ControllerStopped=0,
             InstallCalls=1, InstallIntentCreated=1, InstallIntentDurable=1, ModulePinned=1, Installed=1,
             StorageValidations=40, StorageOpened=1, GuardChecks=42)
    owner_base = 0x180000000
    description = dict(module=owner_base, dispatchBridge=[owner_base + 0x1000 + n * 0x100 for n in range(4)],
                       workerBridge=owner_base + 0x2000, readBridge=owner_base + 0x3000, authorizedForward=owner_base + 0x4000)
    modules = [dict(base=0x700000000, sizeOfImage=0x100000), dict(base=0x710000000, sizeOfImage=0x100000), dict(base=owner_base, sizeOfImage=0x100000)]
    storage = dict(storageModules=modules, storageModuleCount=3, storageVtable=modules[1]['base'] + 0x6000,
                   read=dict(address=modules[1]['base'] + 0x3000, moduleIndex=1),
                   ownedReadBridge=dict(address=description['readBridge'], moduleIndex=2))
    bridges = description['dispatchBridge'] + [description['workerBridge'], description['readBridge']]
    for n, h in enumerate(r['hooks']):
        h.update(slot=base + SLOTS[n] if n < 5 else storage['storageVtable'] + 8,
                 original=base + ORIGINALS[n] if n < 5 else storage['read']['address'], hook=bridges[n], observed=bridges[n])
    for b in (r['bytes'], r['lifecycle']['frozenBytes']):
        b.update(workerCaller=base + 0x834D9B, readCaller=base + 0x3A9227, parentCaller=base + 0x2F77CF)
    r['identity']['caller'] = base + 0x834D9B
    r['hardware']['site_rip'] = base + 0x3F9DAF
    initial = r['planningBeforeSample']['states'][:2] + [0x780010000, 0x780020000, r['hardware']['user']]
    planning = dict(base=base, gameSha256=GAME_SHA, queue=0, queueCapacity=0, expectedMode=0, states=initial,
                    context=dict(snapshot=dict(date=dict(year=203, month=8, day=11, period='中旬'), player=dict(force_id=12, ruler_id=666))))
    kw = dict(base=base, attempt=attempt, epoch=epoch, generation=generation,
              attachment_hex='a1' * 16 + 'b2' * 16, description=description, planning=planning, storage=storage)
    sync_pods(r)
    raw = report_bytes(r)
    return wire.decode_report(raw), kw, raw

def change(path, value):
    def mutate(r, _):
        at = r
        for key in path[:-1]: at = at[key]
        at[path[-1]] = value
    return mutate

def worker_reversed(r, _):
    r['identity']['workerCall'] = r['bytes']['workerCall'] - 1
    r['planningIdentityCall'] = r['identity']['workerCall']

def read_past_bridge(r, _):
    for b in (r['bytes'], r['lifecycle']['frozenBytes']): b['readCall'] = 2**50

def load_past_bridge(r, _):
    r['lifecycle']['completedCall'] = r['lifecycle']['lastCall'] = 2**50
    r['identity']['completionCall'] = r['planningCompletedCall'] = 2**50

def worker_past_bridge(r, _):
    r['identity']['workerCall'] = r['planningIdentityCall'] = 2**50

def main():
    r, kw, raw = synthetic()
    rows = []
    passed = validate_report(r, **kw)
    assert passed['result'] == 'PASS_NATIVE_LOAD_IDENTITY_PLANNING' and not passed['ready_authorized']
    rows.append(dict(case='synthetic_pod_positive', passed=True, synthetic=True))
    later = copy.deepcopy(r)
    later['sequence'] += 5
    later['ControllerOriginalCalls'] += 4
    later['StorageValidations'] += 4
    later['GuardChecks'] += 4
    later['bridges'][0]['started'] += 4
    later['bridges'][0]['returned'] += 4
    later['planningAfterSample']['uiForceContext'] = 15
    later['PlanningUiForceMatches'] = 0
    assert validate_report(later, **kw) == passed
    rows.append(dict(case='later_balanced_frames_ui_telemetry_same_frozen_key', passed=True, synthetic=True))
    other = copy.deepcopy(r)
    other['hardware']['thread'] += 1
    sync_pods(other)
    assert validate_report(other, **kw)['receipt_key'] != passed['receipt_key']
    rows.append(dict(case='different_frozen_call_thread_changes_key', passed=True, synthetic=True))
    negatives = {
        'uninstalled': change(['Installed'], 0), 'stopped': change(['StopRequested'], 1),
        'request_not_applied': change(['RequestCasApplied'], 0),
        'request_wrong_buffer_sha': change(['requestReadSha'], '00' * 32),
        'queue_called_twice': change(['QueueNativeCalls'], 2),
        'admission_blocked': change(['ControllerBlocked'], 1),
        'inflight_dispatch': change(['ActiveDispatch'], 1),
        'unbalanced_native_bridge': change(['bridges', 4, 'returned'], r['bridges'][4]['returned'] - 1),
        'foreign_hook': change(['hooks', 1, 'observed'], r['hooks'][1]['original']),
        'dirty_hook_page': change(['hooks', 1, 'dirty'], 1),
        'wrong_protection': change(['hooks', 1, 'lastProtection'], 4),
        'wrong_actual_byte_sha': change(['bytes', 'sha256'], '00' * 32),
        'short_actual_read': change(['bytes', 'returned'], 100),
        'wrong_read_caller': change(['bytes', 'readCaller'], kw['base'] + 0x10),
        'wrong_frozen_read_call': change(['lifecycle', 'frozenBytes', 'readCall'], 900),
        'not_joined': change(['lifecycle', 'joinReturned'], 0),
        'unordered_completion': change(['lifecycle', 'joinedCall'], r['lifecycle']['completedCall']),
        'identity_not_applied': change(['identity', 'casApplied'], 0),
        'identity_still_source': change(['identity', 'observedPair'], r['identity']['source']),
        'wrong_target_view': change(['identity', 'worldForceAfter'], 12),
        'planning_changed': change(['planningAfterSample', 'world'], 0x1230000),
        'planning_wrong_receipt': change(['planningIdentityCall'], 901),
        'planning_call_past_bridge': change(['planningUserCall'], 2**50),
        'identity_worker_reversed_same_slot': worker_reversed,
        'identity_worker_past_bridge': worker_past_bridge,
        'byte_read_past_bridge': read_past_bridge,
        'load_completion_past_bridge': load_past_bridge,
        'hardware_wrong_generation': change(['hardware', 'binding', 'owner_generation'], 999),
        'hardware_wrong_site': change(['hardware', 'site_rip'], kw['base'] + 0x3F9DBF),
        'hardware_call_after_planning': change(['hardware', 'call_id'], r['planningUserCall']),
        'hardware_restore_uncertain': change(['hardware', 'restore_uncertain'], 1),
        'hardware_DR_changed': change(['hardware', 'restored_dr', 0], 1),
        'pending_player_menu': change(['hardware', 'pending', 'menu_command'], 6),
        'overclaimed_READY': change(['ReadyAuthorized'], 1),
        'overclaimed_world': change(['identity', 'fullWorldVerified'], 1),
        'overclaimed_input': change(['hardware', 'full_input_hold'], True),
        'overclaimed_pixels': change(['PixelPresentationProven'], 1),
        'missing_storage': lambda d, k: k['storage'].pop('read'),
        'wrong_attempt': lambda d, k: k.update(attempt=k['attempt'] + 1),
        'bool_instead_integer': change(['Installed'], True),
        'missing_field': lambda d, k: d.pop('ControllerCommit'),
    }
    for name, mutate in negatives.items():
        data, args = copy.deepcopy(r), copy.deepcopy(kw)
        mutate(data, args)
        sync_pods(data)
        try: validate_report(data, **args)
        except ValueError as exc: rows.append(dict(case=name, passed=True, rejection=str(exc)))
        else: raise AssertionError('accepted invalid case ' + name)
    mismatch = copy.deepcopy(r)
    mismatch['bytes']['readCall'] += 10
    try: validate_report(mismatch, **kw)
    except ValueError as exc: rows.append(dict(case='raw_decoded_mismatch', passed=True, rejection=str(exc)))
    else: raise AssertionError('raw POD mismatch was accepted')
    oversized = copy.deepcopy(r)
    oversized['receipts']['bytesReceipt'] += '00'
    try: validate_report(oversized, **kw)
    except ValueError as exc: rows.append(dict(case='oversized_raw_receipt', passed=True, rejection=str(exc)))
    else: raise AssertionError('oversized nested receipt accepted')
    for name, path in (('actual_fixture_chain_is_not_production_success', SEED), ('actual_factory_pending_refusal_is_not_success', SEED_REFUSAL)):
        try: validate_report(wire.decode_report(path.read_bytes()), **kw)
        except ValueError as exc: rows.append(dict(case=name, passed=True, rejection=str(exc), actual_owned_report=str(path), sha256=sha(path)))
        else: raise AssertionError('owned partial fixture report misclassified')
    folder = ROOT / 'checkpoint_complete_live_acceptance_runs' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    (folder / 'SYNTHETIC-positive.bin').write_bytes(raw)
    (folder / 'SYNTHETIC-bindings.json').write_text(json.dumps(kw, indent=2), encoding='utf-8')
    result = dict(schema='checkpoint-complete-live-acceptance-tests-v1', passed=True, cases=rows,
                  classifier_success_proven_only_on_synthetic_data=True, real_game_success=False, game_access=False,
                  positive_sha256=hashlib.sha256(raw).hexdigest(),
                  source_sha256={n:sha(ROOT/n) for n in ('checkpoint_complete_live_acceptance.py', 'checkpoint_complete_live_acceptance_test.py', 'checkpoint_complete_live_owner_contract.py', 'checkpoint_live_prefetch_contract.py')})
    (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, cases=len(rows), result=str(folder / 'result.json'), sha256=sha(folder / 'result.json'))))
    return 0

if __name__ == '__main__': raise SystemExit(main())
