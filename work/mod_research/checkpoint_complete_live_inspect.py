"""Inspect one retained owner. Default is files only; no process discovery.

--live-report is a separate, durable, single-use diagnostic reservation. It
permits only Describe and one GetReport, never Install/Stop/Restore/FreeLibrary.
The copied DLL is already loaded, or inspection refuses. This does not certify
full world equality, input exclusion, presentation, or multiplayer readiness.
"""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

P = Path(__file__).resolve().parent
APPROVED_DLL = '984e3fbf763557d70f6bdaecd1823acc2a6e46795a285162a36cdadd2c2c0c9c'
APPROVED_CONTRACT = '14579f196fb927e7e055735eeafccb4b11cd4e8688bb7105b1055fc29da67d5a'
GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
DESCRIBE = 'DescribeCheckpointCompleteLiveOwner'
GET_REPORT = 'GetCheckpointCompleteLiveOwnerReport'
BINDING = ('run', 'pid', 'birth', 'base', 'attempt', 'epoch', 'generation',
           'attachment', 'owner_binding', 'dll_sha256', 'target_sha256', 'target')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def beneath(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    require(path.is_relative_to(root), 'Evidence path escapes the configured workspace')
    return path


def read_stable(path, limit=16 * 1024 * 1024):
    a = path.stat()
    require(path.is_file() and 0 <= a.st_size <= limit, 'Evidence file size/type refused')
    raw = path.read_bytes()
    b = path.stat()
    require(a.st_size == b.st_size == len(raw) and a.st_mtime_ns == b.st_mtime_ns,
            'Evidence changed while reading')
    return raw


def save_new(path, value):
    with path.open('x', encoding='utf8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())


class Policy:
    def __init__(self, root=P, dll_sha=APPROVED_DLL, contract_sha=APPROVED_CONTRACT):
        self.root = Path(root).resolve()
        self.runs = self.root / 'checkpoint_complete_live_runs'
        self.inspections = self.root / 'checkpoint_complete_live_inspections'
        self.dll_sha = dll_sha
        self.contract_sha = contract_sha


def artifacts(claim_path, policy):
    claim_path = beneath(claim_path, policy.root)
    evidence, values = {}, {}
    def read(label, path, binary=False):
        path = beneath(path, policy.root)
        raw = read_stable(path)
        evidence[str(path)] = digest(raw)
        value = raw if binary else json.loads(raw)
        values[label] = value
        return value
    claim = read('claim', claim_path)
    require(isinstance(claim, dict), 'Claim is not an object')
    run = beneath(claim['run'], policy.runs)
    require(run != policy.runs, 'Claim must identify one run directory')
    for label, name in (('result', 'result.json'), ('trace', 'trace.json'),
                        ('description', 'description.json'), ('bindings', 'bindings.json'),
                        ('config', 'config.bin'), ('dll', 'checkpoint_complete_live_owner.dll')):
        path = run / name
        if path.exists():
            read(label, path, label in ('config', 'dll'))
    return values, evidence, run


def eligibility(values, policy):
    claim = values['claim']
    result = values.get('result')
    require(isinstance(result, dict), 'No finalized result.json; attempt may still be running')
    require(result.get('schema') == 'san14.complete-live-load.v1', 'Unknown result schema')
    require(result.get('install_completed') is True and type(result.get('install_exit')) is int,
            'Install completion/exit is not definite')
    require(result.get('control_lifetime_uncertain') is False,
            'Control lifetime must be explicitly known')
    def cleanup_known(item):
        if isinstance(item, dict):
            for key, value in item.items():
                if key == 'control_lifetime_uncertain':
                    require(value is False, 'Nested uncertain control lifetime')
                if 'cleanup' in key and ('error' in key or 'uncertain' in key):
                    require(value in (None, False, '', [], {}), 'Unknown/failed control cleanup')
                if key == 'cleanup_control_completed':
                    require(value is True, 'Cleanup control has not completed')
                cleanup_known(value)
        elif isinstance(item, list):
            for value in item:
                cleanup_known(value)
    cleanup_known(result)
    require(all(result.get(key) == claim.get(key) and key in claim for key in BINDING),
            'Claim/result attempt binding differs')
    for key in ('pid', 'birth', 'base', 'attempt', 'epoch', 'generation'):
        require(type(claim[key]) is int and claim[key] > 0, 'Invalid attempt numeric binding')
    for key in ('attachment', 'owner_binding', 'dll_sha256', 'target_sha256'):
        require(isinstance(claim[key], str) and len(claim[key]) == 64 and
                all(c in '0123456789abcdef' for c in claim[key]), 'Invalid attempt digest/token')
    require(claim['dll_sha256'] == policy.dll_sha and digest(values['dll']) == policy.dll_sha,
            'Copied DLL is not the independently approved binary')
    require(digest(values['config']) == values['bindings']['config_sha256'], 'Config evidence changed')
    require(isinstance(values.get('trace'), list) and isinstance(values.get('description'), dict),
            'Missing finalized trace or description')
    contract = policy.root / 'checkpoint_complete_live_owner_contract.py'
    require(digest(read_stable(contract)) == policy.contract_sha, 'ABI contract changed')


def validate_config(raw, claim, description):
    from checkpoint_complete_live_owner_contract import Config, MAGIC, VERSION, CONFIG_SIZE
    require(len(raw) == CONFIG_SIZE, 'Config ABI size differs')
    cfg = Config.from_buffer_copy(raw)
    require((cfg.magic, cfg.size, cfg.version) == (MAGIC, CONFIG_SIZE, VERSION), 'Config ABI differs')
    require(all(getattr(cfg, key) == claim[key] for key in ('pid', 'birth', 'base', 'attempt', 'epoch', 'generation')),
            'Config numeric binding differs')
    require(bytes(cfg.attachment).hex() == claim['attachment'] and
            bytes(cfg.ownerBinding).hex() == claim['owner_binding'] and
            bytes(cfg.gameSha256).hex() == GAME_SHA, 'Config identity differs')
    require(Path(cfg.localPath).resolve() == Path(claim['target']).resolve(), 'Config target differs')
    modules = [m for m in cfg.storageModules if m.base == description['module']]
    require(cfg.storageModuleCount == 3 and len(modules) == 1 and
            bytes(modules[0].fileSha256).hex() == claim['dll_sha256'], 'Configured owner module differs')
    require(cfg.ownedReadBridge.address == description['readBridge'], 'Configured read bridge differs')


def revalidate_evidence(evidence):
    for path, expected in evidence.items():
        require(digest(read_stable(Path(path))) == expected, 'Evidence changed since eligibility checks')


class LiveTransport:
    """Explicit PID only. No discovery, initialization, install, or cleanup calls."""
    def __init__(self, claim, copied, description):
        from game_reader import GameReader
        from run_autonomous_pilot import ProcessAPI, pefile
        from checkpoint_push_start import process_birth
        self.reader = self.api = None
        self.claim, self.copied, self.saved = claim, copied, description
        self.birth = process_birth
        try:
            self.reader = GameReader(pid=claim['pid'])
            require(self.reader.sha256 == GAME_SHA and self.birth(self.reader) == claim['birth'] and
                    self.reader.memory.base == claim['base'], 'PID/birth/base/build changed')
            self.api = ProcessAPI(self.reader)
            pe = pefile.PE(str(copied))
            try:
                exports = {s.name.decode('ascii'): s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
                self.rvas = {}
                self.size = pe.OPTIONAL_HEADER.SizeOfImage
                for name in (DESCRIBE, GET_REPORT):
                    symbol = exports[name]
                    require(not symbol.forwarder and 0 < symbol.address < self.size - 32,
                            'Export is forwarded or outside the approved image')
                    self.rvas[name] = symbol.address
                self.code = {rva: pe.get_data(rva, 32) for rva in self.rvas.values()}
                for address in description['dispatchBridge'] + [description[k] for k in
                        ('workerBridge', 'readBridge', 'authorizedForward')]:
                    rva = address - description['module']
                    require(0 < rva < self.size - 32, 'Bridge outside the approved owner image')
                    self.code[rva] = pe.get_data(rva, 32)
                header_size = pe.OPTIONAL_HEADER.SizeOfHeaders
                require(0 < header_size <= 4096, 'Unexpected approved PE header extent')
                self.header = pe.get_data(0, header_size)
                require(len(self.header) == header_size, 'Truncated approved PE header')
            finally:
                pe.close()
            self.verify()
        except BaseException:
            self.close()
            raise

    def verify(self):
        from checkpoint_complete_live_capture import readable
        require(self.birth(self.reader) == self.claim['birth'], 'PID lifetime changed')
        api_reader = SimpleNamespace(memory=SimpleNamespace(k=self.api.k, handle=self.api.handle))
        require(self.birth(api_reader) == self.claim['birth'], 'Control handle belongs to another PID lifetime')
        require(digest(read_stable(self.copied)) == self.claim['dll_sha256'], 'Copied DLL changed')
        matches = [base for base, path in self.api.modules()
                   if str(path.resolve()).casefold() == str(self.copied.resolve()).casefold()]
        require(matches == [self.saved['module']], 'Retained module/path/base changed or is absent')
        module = matches[0]
        readable(self.reader, module, len(self.header), allocation=module)
        require(self.reader.memory.read(module, len(self.header)) == self.header, 'Loaded PE header differs')
        for rva, expected in self.code.items():
            require(len(expected) == 32, 'Truncated approved code')
            readable(self.reader, module + rva, 32, allocation=module, execute=True)
            require(self.reader.memory.read(module + rva, 32) == expected, 'Retained owner code differs')

    def call(self, name, size):
        from checkpoint_live_prefetch_start import invoke
        require(name in (DESCRIBE, GET_REPORT), 'Unapproved diagnostic export')
        self.verify()
        return invoke(self.api, self.saved['module'] + self.rvas[name], output_size=size)

    def close(self):
        if self.api is not None:
            self.api.close(); self.api = None
        if self.reader is not None:
            self.reader.close(); self.reader = None


def inspect(claim_path, *, live=False, policy=None, transport_factory=None):
    policy = policy or Policy()
    output = policy.inspections / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True)
    report = dict(schema='san14.complete-live-inspection.v1', mode='live-report' if live else 'files-only',
        result='INCOMPLETE', process_accessed=False, native_calls=[], new_load_requested=False,
        stop_requested=False, restore_requested=False, unload_requested=False, module_retained=True,
        full_world_verified=False, ready_authorized=False, automatic_retry_allowed=False,
        control_lifetime_uncertain=False)
    transport = None
    try:
        values, evidence, run = artifacts(claim_path, policy)
        report.update(run=str(run), evidence_sha256=evidence, binding=values['claim'],
            saved_result=values.get('result', {}).get('result'),
            trace_samples=len(values.get('trace', [])), saved_report=values.get('result', {}).get('post_stop_report',
                values.get('result', {}).get('report')))
        try:
            eligibility(values, policy)
            validate_config(values['config'], values['claim'], values['description'])
            report['eligible_for_live_report'] = True
        except Exception as exc:
            report.update(eligible_for_live_report=False, eligibility_error=str(exc))
        if not live:
            report['result'] = 'FILES_ONLY_SUMMARY'
            return report, output
        require(report['eligible_for_live_report'], report.get('eligibility_error', 'Live report refused'))
        revalidate_evidence(evidence)
        claim = values['claim']
        # Separate inspection reservation; never refresh or modify the load claim.
        once = policy.inspections / ('live-%d-%d.once.json' % (claim['attempt'], claim['epoch']))
        save_new(once, dict(run=str(run), inspection=str(output), binding=claim,
                            evidence_sha256=evidence, automatic_retry_allowed=False))
        report['inspection_once'] = str(once)
        report['process_accessed'] = True
        factory = transport_factory or LiveTransport
        transport = factory(claim, run / 'checkpoint_complete_live_owner.dll', values['description'])
        from checkpoint_complete_live_owner_contract import DESCRIPTION_SIZE, REPORT_SIZE, decode_description, decode_report
        for name, size in ((DESCRIBE, DESCRIPTION_SIZE), (GET_REPORT, REPORT_SIZE)):
            revalidate_evidence(evidence)
            call = dict(export=name, completed=False, may_have_started=False)
            report['native_calls'].append(call)
            try:
                code, raw = transport.call(name, size)
            except BaseException as exc:
                if hasattr(exc, 'completed') and hasattr(exc, 'may_have_started'):
                    call.update(completed=exc.completed, may_have_started=exc.may_have_started,
                                cleanup_errors=exc.cleanup_errors)
                    report['control_lifetime_uncertain'] = bool(not exc.completed and exc.may_have_started)
                else:
                    # Conservatively unknown: never attempt a subsequent export.
                    call['may_have_started'] = True
                    report['control_lifetime_uncertain'] = True
                raise
            call.update(completed=True, may_have_started=True, exit=code)
            require(code == 0, 'Diagnostic export rejected')
            if name == DESCRIBE:
                require(decode_description(raw) == values['description'], 'Live description differs from finalized run')
            else:
                observed = decode_report(raw)
                require(observed['attempt'] == claim['attempt'] and observed['epoch'] == claim['epoch'],
                        'Report belongs to another attempt')
                with (output / 'report.bin').open('xb') as f:
                    f.write(raw); f.flush(); os.fsync(f.fileno())
                report['report'] = observed
        report['result'] = 'REPORT_OBSERVED_NO_READINESS_AUTHORITY'
    except BaseException as exc:
        report['error'] = repr(exc)
        report['result'] = 'REFUSED_OR_UNCERTAIN'
    finally:
        if transport is not None:
            try:
                transport.close()
            except BaseException as exc:
                report['local_handle_cleanup_error'] = repr(exc)
        save_new(output / 'inspection.json', report)
    return report, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--claim', type=Path, default=P / 'checkpoint_complete_live_once.json')
    parser.add_argument('--live-report', action='store_true')
    args = parser.parse_args()
    # Paths for lazy, explicitly requested transport imports. No reader is created here.
    sys.path[:0] = [str(P), str(P / 'python_deps'), str(P.parents[1] / 'outputs' / 'san14-link')]
    report, output = inspect(args.claim, live=args.live_report)
    print(json.dumps(dict(result=report['result'], inspection=str(output / 'inspection.json'),
                          eligible_for_live_report=report.get('eligible_for_live_report', False),
                          error=report.get('error')), ensure_ascii=False))
    return 0 if report['result'] in ('FILES_ONLY_SUMMARY', 'REPORT_OBSERVED_NO_READINESS_AUTHORITY') else 2


if __name__ == '__main__':
    raise SystemExit(main())
