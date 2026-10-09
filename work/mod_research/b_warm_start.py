"""One profile-bound warm diagnostic load. No arguments: help, no game access.

This first-bank successor requires an already staged exact file. It never replaces
Steam saves and never retries a PID/birth claim. A second bank needs the native
handover coordinator, not another invocation of this single-bank entry point.
"""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import time

import b_warm_profile_contract as wire
from b_warm_profile_capture import capture_planning, profile_from_dict, wrap_owner_config, integer

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2]/'mod_research'
EXPORTS = ('DescribeBWarmProfileOwner', 'InstallBWarmProfileOwner', 'GetBWarmProfileReport',
           'GetBWarmRetireReport', 'GetCheckpointCompleteLiveOwnerReport', 'StopCheckpointCompleteLiveOwner')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())


def approved_build(path, expected_sha):
    path = Path(path).resolve(strict=True)
    require(sha(path) == expected_sha, 'Build result identity differs')
    result = json.loads(path.read_text(encoding='utf-8'))
    require(result.get('family') == 'san14.b-warm-factory.v1' and result.get('result') == 'PASS'
            and result.get('factory_complete_passed') is True and result.get('inputs_unchanged') is True,
            'Full factory/guard execution evidence required')
    for field in ('sources', 'private', 'generated', 'binaries'):
        rows = result.get(field)
        require(type(rows) is dict and rows, 'Missing build identity closure: '+field)
        for name, digest in rows.items():
            require(sha(name) == digest, 'Build input changed: '+name)
    dll = Path(result['production_dll']['path']).resolve(strict=True)
    require(dll.is_relative_to(path.parent) and result['binaries'].get(str(dll)) == result['production_dll']['sha256']
            and sha(dll) == result['production_dll']['sha256'], 'Production DLL is not the verified build output')
    return dll, result['production_dll']['sha256']


def refuse_prior_attempt(pid, birth):
    # These archives are terminal process lifetimes. Never delete/reset claims.
    paths = list((PRIVATE/'b_warm_start_claims').glob('*.json'))
    paths += list((PRIVATE/'a_save_runtime_live_claims').glob('*.json'))
    for parent in (P, PRIVATE):
        for name in ('checkpoint_complete_live_once.json', 'checkpoint_complete_live_v2_once.json'):
            if (parent/name).exists():
                paths.append(parent/name)
    for path in paths:
        record = json.loads(path.read_text(encoding='utf-8'))
        if (record.get('pid'), record.get('birth')) == (pid, birth):
            raise ValueError('Existing process attempt requires its own recovery/handover: '+str(path))


class Calls:
    """Track uncertain control calls before considering any cleanup invocation."""
    def __init__(self, api, invoke):
        self.api, self.invoke, self.uncertain = api, invoke, False

    def call(self, address, data=None, output_size=0):
        try:
            return self.invoke(self.api, address, data, output_size)
        except BaseException as exc:
            # Unknown exception shape is conservatively uncertain; never overlap
            # a possible remote call with Stop or free its argument elsewhere.
            self.uncertain |= bool(getattr(exc, 'may_have_started', True) and not getattr(exc, 'completed', False))
            raise


def completion(calls, addresses, *, profile, planning, storage, description, config, deadline, record):
    from b_warm_start_acceptance import validate_report
    previous = None
    previous_sequence = None
    last = 'No complete report'
    while time.monotonic() < deadline:
        samples = {}
        for name, kind in (('GetCheckpointCompleteLiveOwnerReport', wire.old.Report),
                           ('GetBWarmProfileReport', wire.Report), ('GetBWarmRetireReport', wire.RetireReport)):
            code, raw = calls.call(addresses[name], output_size=C.sizeof(kind))
            require(code == 0 and raw is not None, 'Report export rejected: '+name)
            samples[name] = raw
        row = wire.old.decode_report(samples['GetCheckpointCompleteLiveOwnerReport'])
        record(samples, row)
        require(type(row['sequence']) is int and row['sequence'] > (previous_sequence or 0), 'Native report sequence did not advance')
        previous_sequence = row['sequence']
        require((row['attempt'], row['epoch']) == (config.owner.attempt, config.owner.epoch), 'Report belongs to another attempt')
        if any(row[k] for k in ('OwnerError', 'SessionError', 'ControllerError', 'QueueError', 'BytesError',
                               'LifecycleError', 'IdentityError', 'PlanningError', 'HardwareError', 'StorageError', 'GuardError')):
            raise ValueError('Native load reported an error; original reports retained')
        retired = wire.decode(wire.RetireReport, samples['GetBWarmRetireReport'])
        require(not retired.restoreFailed, 'Native source restoration uncertain')
        try:
            accepted = validate_report(row, base=planning['base'], attempt=config.owner.attempt,
                epoch=config.owner.epoch, generation=config.owner.generation,
                attachment_hex=bytes(config.owner.attachment).hex(), description=description,
                planning=planning, storage=storage, profile=profile,
                profile_report=samples['GetBWarmProfileReport'], retire_report=samples['GetBWarmRetireReport'])
        except ValueError as exc:
            previous, last = None, str(exc)
        else:
            if accepted == previous:
                return accepted
            previous = accepted
        time.sleep(.15)
    raise ValueError('Native completion remains incomplete: '+last)


def execute(reader, profile, expected_ruler, target, steam_paths, build, build_sha, folder, timeout):
    from b_warm_staging import Handle, pin_parents, clean_path
    from contextlib import ExitStack
    from b_warm_start_support import build_config, storage_bindings, live_hook_evidence, open_process_api
    from checkpoint_complete_live_capture import process_birth, readable, module_approval
    from checkpoint_live_prefetch_start import invoke
    from a_save_local_binding import source_hashes
    import b_warm_start_acceptance
    import run_autonomous_pilot  # Include the deferred API implementation in source pins.
    import pefile
    dll, dll_sha = approved_build(build, build_sha)
    before = capture_planning(reader, profile, expected_ruler)
    refuse_prior_attempt(reader.pid, before['birth'])
    target = clean_path(target)
    require(target.name == 'svdexccSC03.s14', 'Exact native filename required')
    pins = source_hashes()
    result = dict(result='INCOMPLETE', module_retained=True, automatic_retry_allowed=False,
                  full_world_verified=False, ready_authorized=False, input_exclusion_proven=False,
                  map_cover_tested=False, first_bank_only=True, tool_save_file_writes=0, source_sha256=pins,
                  staging_reuse_authorized=False, native_drained=False)
    api = calls = None
    install_completed = False
    addresses = {}
    trace = []
    held = ExitStack()
    try:
        pin_parents(held, target)
        file_handle = held.enter_context(Handle(target))
        file_identity, raw_file = file_handle.snapshot()
        require((file_identity['size'], file_identity['sha256']) == (profile.file.size, bytes(profile.file.sha256).hex()),
                'Already staged file differs; this entry never overwrites a slot')
        local_file = folder/target.name
        with local_file.open('xb') as out:
            out.write(raw_file)
        copied = folder/'warm_bank.dll'
        shutil.copyfile(dll, copied)
        require(sha(copied) == dll_sha, 'Copied DLL differs')
        pe = pefile.PE(str(copied))
        try:
            exports = {x.name.decode('ascii'): x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols if x.name}
            image_size = pe.OPTIONAL_HEADER.SizeOfImage
            require(all(n in exports and 0 < exports[n] < image_size for n in EXPORTS), 'Missing warm exports')
        finally:
            pe.close()
        attempt, epoch = secrets.randbits(64) or 1, secrets.randbits(64) or 1
        claim = dict(pid=reader.pid, birth=before['birth'], base=before['base'], attempt=attempt, epoch=epoch,
                     run=str(folder), dll_sha256=dll_sha, profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),
                     target=str(target), target_identity=file_identity, automatic_retry_allowed=False)
        claims = PRIVATE/'b_warm_start_claims'
        claims.mkdir(exist_ok=True)
        save_new(claims/f'{reader.pid}-{before["birth"]}.json', claim)
        save_new(folder/'claim.json', claim)
        result.update(claim)
        api = open_process_api(reader)
        calls = Calls(api, invoke)
        calls.call(api.load_library_address(), str(copied).encode('utf-16le')+b'\0\0')
        matches = [a for a, path in api.modules() if str(path).casefold() == str(copied).casefold()]
        require(len(matches) == 1, 'Loaded module differs')
        module = matches[0]
        module_approval(reader, module, copied, dll_sha)
        addresses = {n: module+exports[n] for n in EXPORTS}
        code, raw = calls.call(addresses['DescribeBWarmProfileOwner'], output_size=C.sizeof(wire.Description))
        require(code == 0, 'Warm description rejected')
        d = wire.decode(wire.Description, raw)
        description = wire.old.decode_description(bytes(d.bank))
        require(description['module'] == module, 'Description module differs')
        bridges = description['dispatchBridge']+[description['workerBridge'], description['readBridge'], description['authorizedForward']]
        require(len(set(bridges)) == 7, 'Aliased module bridges')
        pe = pefile.PE(str(copied), fast_load=True)
        try:
            for address in bridges+list(addresses.values()):
                require(module <= address and address+32 <= module+image_size, 'Code outside approved module')
                readable(reader, address, 32, allocation=module, execute=True)
                require(reader.memory.read(address, 32) == pe.get_data(address-module, 32), 'Loaded code differs')
        finally:
            pe.close()
        planning = capture_planning(reader, profile, expected_ruler)
        require(all(planning[k] == before[k] for k in ('pid', 'birth', 'base')), 'Attachment changed')
        storage = storage_bindings(reader, api.modules(), steam_paths=steam_paths, owner_module=module,
                                   owner_path=copied, owner_sha=dll_sha, read_bridge=description['readBridge'])
        hooks_before = live_hook_evidence(reader, planning, storage)
        owner = build_config(planning, storage, folder=folder, target=local_file, attempt=attempt, epoch=epoch,
                             attachment_hex=secrets.token_hex(32), owner_binding_hex=secrets.token_hex(32))
        config = wrap_owner_config(owner, profile, planning)
        require(file_handle.snapshot()[0] == file_identity, 'Staged file changed')
        save_new(folder/'bindings.json', dict(planning=planning, storage=storage, description=description,
                                            hooks_before=hooks_before, config_sha256=hashlib.sha256(bytes(config)).hexdigest()))
        (folder/'config.bin').write_bytes(bytes(config))
        try:
            code, _ = calls.call(addresses['InstallBWarmProfileOwner'], bytes(config))
            install_completed = True
        except BaseException as exc:
            install_completed = bool(getattr(exc, 'completed', False))
            raise
        require(code == 0, 'Installation rejected; never resubmit')
        def record(samples, row):
            index = len(trace)
            for name, raw in samples.items():
                (folder/f'{index:04}-{name}.bin').write_bytes(raw)
            trace.append(row)
        accepted = completion(calls, addresses, profile=profile, planning=planning, storage=storage,
                              description=description, config=config, deadline=time.monotonic()+timeout, record=record)
        # Retirement already restored sources. Do not Stop a successful bank:
        # its frozen successful completion is needed by future native handover.
        hooks_after = live_hook_evidence(reader, planning, storage, baseline=hooks_before)
        snap = reader.snapshot()
        require(reader.snapshot() == snap and process_birth(reader) == before['birth'], 'Post-load context changed')
        require(tuple(snap['date'][k] for k in ('year', 'month', 'day')) == (profile.loaded.year, profile.loaded.month, profile.loaded.day)
                and (snap['player']['force_id'], snap['player']['ruler_id']) == (profile.target.force, profile.target.ruler),
                'Post-load date/player differs')
        require(file_handle.snapshot()[0] == file_identity, 'Staged file identity changed during load')
        require(all(sha(P.parents[1]/name) == digest for name, digest in pins.items()), 'Launcher source changed')
        result.update(result='PASS_WARM_DIAGNOSTIC_LOAD_RETIRED', accepted=accepted,
                      native_slots_restored=True, hooks_after=hooks_after, snapshot=snap,
                      second_bank_authorized=False)
    except BaseException as exc:
        result['error'] = repr(exc)
        if calls and install_completed and not calls.uncertain and 'StopCheckpointCompleteLiveOwner' in addresses:
            try:
                code, _ = calls.call(addresses['StopCheckpointCompleteLiveOwner'])
                result['cleanup_stop_completed'] = code == 0
            except BaseException as cleanup:
                result['cleanup_error'] = repr(cleanup)
    finally:
        result['control_uncertain'] = calls.uncertain if calls else False
        result['install_call_completed'] = install_completed
        if api:
            api.close()
        # Close only after any known-completed Stop request. Stop alone does
        # not prove native drain; the terminal claim forbids reuse/restaging.
        held.close()
        result['local_file_lease_released'] = True
        save_new(folder/'trace.json', trace)
        save_new(folder/'result.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--pid', type=int)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--expected-ruler', type=int)
    parser.add_argument('--file', type=Path, help='Already staged native CC03 file; never overwritten')
    parser.add_argument('--steam-api', type=Path)
    parser.add_argument('--steam-client', type=Path)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--build-sha256')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args(argv)
    if not args.check and not args.execute:
        parser.print_help()
        return 0
    integer(args.pid, 1, 0xffffffff)
    integer(args.expected_ruler, 1, 5999)
    integer(args.timeout, 30, 1800)
    require(args.profile and args.file and args.steam_api and args.steam_client, 'Explicit profile/file and local Steam paths required')
    if args.execute:
        require(args.build and args.build_sha256, 'Approved full-factory build required')
    profile = profile_from_dict(json.loads(args.profile.read_text(encoding='utf-8-sig')))
    steam = {'steam_api64.dll': str(args.steam_api.resolve(strict=True)), 'steamclient64.dll': str(args.steam_client.resolve(strict=True))}
    sys.path[:0] = [str(PRIVATE/'python_deps'), str(P.parents[1]/'outputs/san14-link')]
    from game_reader import GameReader
    reader = GameReader(pid=args.pid)
    folder = PRIVATE/'b_warm_start_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    try:
        if args.execute:
            result = execute(reader, profile, args.expected_ruler, args.file, steam, args.build, args.build_sha256, folder, args.timeout)
        else:
            from b_warm_start_support import storage_bindings
            from b_warm_staging import clean_path, read_file
            from a_save_local_binding import modules
            planning = capture_planning(reader, profile, args.expected_ruler)
            storage = storage_bindings(reader, modules(reader.memory.handle), steam_paths=steam)
            identity, _ = read_file(clean_path(args.file))
            require(args.file.name == 'svdexccSC03.s14' and (identity['size'], identity['sha256']) ==
                    (profile.file.size, bytes(profile.file.sha256).hex()), 'Staged input differs')
            after = capture_planning(reader, profile, args.expected_ruler)
            require(after == planning, 'Planning changed during storage/file check')
            result = dict(result='PASS_READ_ONLY', planning=planning, storage=storage, file_identity=identity,
                          install_permitted=False, game_writes=0, native_calls=0)
            save_new(folder/'result.json', result)
    except BaseException as exc:
        if not (folder/'result.json').exists():
            save_new(folder/'result.json', dict(result='BLOCKED', error=repr(exc), automatic_retry_allowed=False))
        raise
    finally:
        reader.close()
    print(json.dumps(dict(result=result['result'], path=str(folder/'result.json')), ensure_ascii=False))
    return 0 if result['result'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
