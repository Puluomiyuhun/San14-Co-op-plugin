"""Real Windows staging + ResidentPort/WorldLifecycle; native memory/publisher double."""
import ctypes as C
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path[:0] = [str(PRIVATE/'python_deps'), str(ROOT/'outputs/san14-link')]
import b_warm_staging as files
from b_warm_bootstrap import BootstrapRulesBridge, BootstrapReceivedApply
from b_warm_room import ReceivedCheckpoint
from checkpoint_journal import CheckpointJournal
from authoritative_sync import CheckpointPackage, CheckpointReceiver, canonical, POLICY
from b_warm_profile_contract import Profile, Date, Identity
from human_rules_world_lifecycle import (Config, Descriptor, ModuleIdentity, ResidentPort,
                                        WorldGeneration, WorldLifecycle, NextWorldRequest)

OUTPUT = None
EVIDENCE = []


def sha(raw): return hashlib.sha256(raw).hexdigest()


def writer_blocked(path):
    k = files.kernel(); h = k.CreateFileW(str(path), 0x40000000, 7, None, 3, 0, None)
    if h not in (None, C.c_void_p(-1).value): k.CloseHandle(h); return False
    return C.get_last_error() == 32


class NativeRulesDouble:
    """Supplies all read/publish bytes to the actual ResidentPort predicates."""
    def __init__(self):
        self.pid, self.birth = 123, 456789
        self.image = 0x140000000; self.spans = {}; self.events = []; self.ports = []
        self.current = self.config(1, 1, 12, b'\x11'*16)
        self.sources = [self.image+0x10000+i*0x100 for i in range(6)]
        for i, a in enumerate(self.sources): self.spans[a] = bytes([0x90+i])*16

    def config(self, generation, day, viewer, epoch):
        c = Config(version=1, size=C.sizeof(Config), image=self.image,
                   root=0x200000000+generation*0x100000, world=0x300000000+generation*0x100000)
        c.room[:] = b'\x31'*16; c.epoch[:] = epoch; c.rules_digest[:] = b'\x42'*32
        c.force[:] = [12, 2]; c.main_district[:] = [11, 2]; c.viewer = viewer
        c.year, c.month, c.day, c.income_key5, c.world_option8 = 203, 8, day, 1, 0
        return c

    def read(self, address, size):
        for start, raw in self.spans.items():
            if start <= address and address+size <= start+len(raw): return raw[address-start:address-start+size]
        raise ValueError('Missing explicit memory double span')

    def identity(self, module):
        assert (module.pid, module.birth) == (self.pid, self.birth)

    def scope(self, world):
        c = Config.from_buffer_copy(world.config)
        assert bytes(c.room) == bytes(self.current.room) and bytes(c.rules_digest) == bytes(self.current.rules_digest)

    def prepare(self, world):
        assert type(world) is WorldGeneration
        generation = world.generation; base = 0x600000000+generation*0x100000
        nonce = bytes([generation])*32
        m = ModuleIdentity(self.pid, self.birth, base, base+0x1000, nonce, 'a'*64,
            0x100, 0x200, ((0x400, b'\x48\x8b', 0x500), (0x410, b'\x48\x89', 0x510)), 'OWNED_FIXTURE')
        d = Descriptor(magic=0x31544753524C5548, version=1, size=C.sizeof(Descriptor),
            pid=self.pid, fixture=1, birth=self.birth, image=self.image, module=base,
            allocation=base+0x10000, site_count=6, policy_enabled=1, preparation_state=2)
        d.nonce[:] = nonce
        for i, s in enumerate(d.sites):
            s.address = self.sources[i]; s.destination = base+0x3000+i*0x100
            s.original_target = self.image+0x20000+i*0x100
            s.patch_size = 5; s.profile_size = 16; s.protection = 0x20
            s.expected[:16] = bytes([0x90+i])*16; s.replacement[:5] = bytes([0xcc-i])*5
        self.spans[m.descriptor] = bytes(d); self.spans[base+m.state_rva] = (4).to_bytes(4, 'little')
        self.spans[base+m.binding_rva] = world.config
        for instruction, expected, counter in m.counters:
            self.spans[base+instruction] = expected; self.spans[base+counter] = bytes(8)
        def publisher(operation):
            self.events.append([operation, generation, Config.from_buffer_copy(world.config).viewer])
            for s in d.sites:
                original = bytes(s.expected[:s.profile_size])
                self.spans[s.address] = (bytes(s.replacement[:s.patch_size])+original[s.patch_size:]
                                        if operation == 'install' else original)
            return 0, dict(status='INSTALLED_HUMAN_RULES' if operation=='install' else 'RESTORED',
                attached=True, detached=True, held_create_process_event=True, uncertain=False,
                written_mask=63, rolled_mask=0, threads_checked=1, fixture_build=True)
        port = ResidentPort(world, m, read=self.read, identity_check=self.identity, publisher=publisher,
                            export_current=lambda _: bytes(self.current), check_scope=self.scope)
        self.ports.append(port); return port

    def observe(self, request):
        self.events.append(['observe', request.generation, self.current.viewer])
        return WorldGeneration(request.generation, request.checkpoint, bytes(self.current))


class WarmDouble:
    def __init__(self, rules, target, case):
        self.rules, self.target, self.case = rules, target, case
        self.reader = SimpleNamespace(pid=rules.pid); self.events = []; self.abort_lease = None; self.request = None
    def open_bank(self, index): self.events.append(['open', index]); return index
    def authorize_second(self, bank, profile):
        self.events.append(['handover', bank])
        if self.case == 'handover-failed': raise ValueError('Explicit handover rejection')
    def load(self, bank, p, raw):
        assert writer_blocked(self.target) and self.target.read_bytes() == raw
        assert sha(raw) == bytes(p.file.sha256).hex()
        self.events.append(['load', bank, p.currentForce, p.target.force])
        req = self.request
        self.rules.current = self.rules.config(req.generation, req.day, p.target.force, req.epoch)
        if self.case == 'load-failed': raise RuntimeError('Explicit load failure after model viewer change')
        accepted = dict(result='PASS_WARM_LOAD_RETIRED', receipt_key=str(bank+1)*64,
            source_force=p.source.force, source_ruler=p.source.ruler,
            target_force=p.target.force, target_ruler=p.target.ruler,
            ready_authorized=False, full_world_verified=False, input_exclusion_proven=False)
        return dict(accepted=accepted, attempt=bank+1, pid=self.rules.pid, birth=self.rules.birth,
            profile_sha256=sha(bytes(p)), slots_restored=True,
            snapshot=dict(date=dict(year=p.loaded.year, month=p.loaded.month, day=p.loaded.day),
                          player=dict(force_id=p.target.force, ruler_id=p.target.ruler)))
    def abort(self):
        self.abort_lease = writer_blocked(self.target); assert self.abort_lease
        self.events.append(['abort'])


class Cases(unittest.TestCase):
    def fixture(self, case):
        folder = OUTPUT/case; folder.mkdir(); directory = folder/'slot'; directory.mkdir()
        target = directory/files.NAME; original = b'original owned slot'*40; target.write_bytes(original)
        sources = []
        for i in (1, 2):
            path = folder/f'received-{i}.s14'; path.write_bytes(bytes([i])* (800+i)); sources.append(path)
        records = folder/'records'; records.mkdir(); rules = NativeRulesDouble()
        old = rules.prepare(WorldGeneration(1, '1'*64, bytes(rules.current))); old.install()
        holds = []; life = WorldLifecycle(old, guard_check=lambda: None, on_hold=lambda reason: holds.append(reason))
        warm = WarmDouble(rules, target, case)
        bridge = BootstrapRulesBridge(life, warm, target=target, records=records)
        return folder, target, original, sources, records, rules, life, warm, bridge, holds

    def apply(self, all, step, *, wrong_current=False):
        folder, target, original, sources, records, rules, life, warm, bridge, holds = all
        req = NextWorldRequest(step+1, str(step+1)*64, bytes([0x50+step])*16, 203, 8, 1+step*10)
        p = Profile(); p.file.name = files.NAME.encode(); p.file.slot = 63
        raw = sources[step-1].read_bytes(); p.file.size = len(raw); p.file.sha256[:] = bytes.fromhex(sha(raw))
        p.before = Date(203, 8, 1+(step-1)*10); p.loaded = Date(203, 8, req.day)
        p.source = Identity(666, 12, 11); p.target = Identity(952, 2, 2)
        p.currentForce = (12 if step==2 else 2) if wrong_current else (2 if step==2 else 12)
        warm.request = req
        return bridge.replace(req, p, sources[step-1], observe_loaded=rules.observe, prepare_rules=rules.prepare)

    def test_bootstrap_viewer_then_same_warm_second_bank(self):
        f = self.fixture('success'); _, target, original, sources, records, rules, life, warm, bridge, holds = f
        results = [self.apply(f, 1), self.apply(f, 2)]
        self.assertEqual(warm.events, [['open', 0], ['load', 0, 12, 2], ['open', 1], ['handover', 1], ['load', 1, 2, 2]])
        self.assertEqual([x for x in rules.events if x[0] in ('install', 'restore')],
            [['install', 1, 12], ['restore', 1, 12], ['install', 2, 2], ['restore', 2, 2], ['install', 3, 2]])
        self.assertEqual(Config.from_buffer_copy(life.current.world.config).viewer, 2)
        self.assertEqual(len(life.retained), 3); self.assertEqual(len(bridge.completed), 2)
        self.assertTrue(life.retained[0].retired and life.retained[1].retired)
        backups = [p.read_bytes() for p in records.rglob('*.verified-old.s14')]
        self.assertCountEqual(backups, [original, sources[0].read_bytes()]); self.assertEqual(target.read_bytes(), sources[1].read_bytes())
        self.assertFalse(writer_blocked(target)); self.assertFalse(holds)
        for result in results:
            for field in ('ready', 'fence_released', 'full_world_verified'): self.assertIs(result[field], False)
        EVIDENCE.append(dict(case='source-to-target-then-bank1', warm=warm.events, rules=rules.events,
                             real_file_backup_count=2, same_lifecycle=True, native_memory_publisher='EXPLICIT_DOUBLE'))

    def test_first_load_failure_keeps_lease_through_abort_and_no_retry(self):
        f = self.fixture('load-failed'); _, target, original, sources, records, rules, life, warm, bridge, holds = f
        with self.assertRaisesRegex(RuntimeError, 'Explicit load failure'): self.apply(f, 1)
        self.assertIs(warm.abort_lease, True); self.assertTrue(holds)
        self.assertEqual(bridge.phase, 'HELD'); self.assertFalse(bridge.completed)
        self.assertEqual(len(rules.ports), 1); self.assertEqual(target.read_bytes(), sources[0].read_bytes())
        before = list(warm.events)
        with self.assertRaises(Exception): self.apply(f, 1)
        self.assertEqual(warm.events, before); self.assertFalse(writer_blocked(target))
        EVIDENCE.append(dict(case='first-failed-no-retry', warm=warm.events, abort_actual_writer_blocked=True,
                             file_release_is_native_drain=False))

    def test_first_profile_viewer_mismatch_never_stages(self):
        f = self.fixture('wrong-viewer'); _, target, original, sources, records, rules, life, warm, bridge, holds = f
        with self.assertRaises(Exception): self.apply(f, 1, wrong_current=True)
        self.assertEqual(target.read_bytes(), original); self.assertFalse(warm.events)
        self.assertFalse(list(records.rglob('*.verified-old.s14')))
        self.assertEqual(bridge.phase, 'HELD')
        EVIDENCE.append(dict(case='wrong-initial-viewer', warm=warm.events, staged=False))

    def test_second_handover_failure_preserves_first_file_and_no_retry(self):
        f = self.fixture('handover-failed'); _, target, original, sources, records, rules, life, warm, bridge, holds = f
        self.apply(f, 1)
        with self.assertRaisesRegex(ValueError, 'Explicit handover'): self.apply(f, 2)
        self.assertEqual(target.read_bytes(), sources[0].read_bytes()); self.assertTrue(holds)
        self.assertEqual(len(list(records.rglob('*.verified-old.s14'))), 1)
        self.assertEqual(len(bridge.completed), 1); self.assertEqual(bridge.phase, 'HELD')
        before = list(warm.events)
        with self.assertRaises(Exception): self.apply(f, 2)
        self.assertEqual(warm.events, before); self.assertEqual(len(rules.ports), 2)
        EVIDENCE.append(dict(case='second-handover-failed', warm=warm.events, retained_first=True))

    def test_second_invalid_profile_is_terminal_before_staging(self):
        f = self.fixture('second-invalid'); _, target, original, sources, records, rules, life, warm, bridge, holds = f
        self.apply(f, 1); before = list(warm.events)
        with self.assertRaises(Exception): self.apply(f, 2, wrong_current=True)
        self.assertEqual(bridge.phase, 'HELD'); self.assertEqual(life.phase, 'HELD'); self.assertTrue(holds)
        with self.assertRaises(Exception): self.apply(f, 2)
        self.assertEqual(warm.events, before); self.assertEqual(target.read_bytes(), sources[0].read_bytes())
        EVIDENCE.append(dict(case='second-invalid-profile-held', new_loads=0, retained_first=True))

    def test_received_bootstrap_uses_actual_journal_and_records_ack(self):
        f = self.fixture('received-bootstrap'); folder, target, original, sources, records, rules, life, warm, bridge, holds = f
        scope = dict(schema='san14.authoritative-sync-scope.v1', room_id='31'*16, binding_epoch='4'*32,
            profile=dict(protocol='san14.room.v1', game_sha256='a'*64, adapter_contract='research-no-native-room-adapter.v1',
                         checkpoint_sha256='b'*64, rules_sha256='c'*64),
            bindings={'A': dict(force_id=12, main_district_id=11), 'B': dict(force_id=2, main_district_id=2)},
            authority='A', policy=POLICY)
        epoch = '5'*32; attachments = {'A': '6'*32, 'B': '7'*32}; cut = dict(sequence=0, prefix_sha256='8'*64)
        node = dict(year=203, month=8, day=11, phase='PLANNING_BOUNDARY')
        raw = sources[0].read_bytes()
        package = CheckpointPackage(scope, epoch, 1, cut, node, 'EXPLICIT_BOOTSTRAP_DOUBLE', '9'*64,
                                    {'world.s14': raw, 'adapter.json': b'{}'}, source_player='A')
        receiver = CheckpointReceiver(package.manifest, package.checkpoint_id, scope, epoch, 1, cut)
        for chunk in package.chunks(): receiver.accept(chunk)
        download = folder/'received'; download.mkdir()
        journal = CheckpointJournal(download/'checkpoint.sqlite', scope, package.manifest,
            package.checkpoint_id, epoch, 1, cut, attachments, create=True); journal.stage(receiver)
        journal = CheckpointJournal(download/'checkpoint.sqlite', scope, package.manifest,
            package.checkpoint_id, epoch, 1, cut, attachments)
        (download/'world.s14').write_bytes(raw)
        context = dict(scope=scope, manifest=package.manifest, checkpoint_id=package.checkpoint_id, attachments=attachments)
        received = ReceivedCheckpoint(canonical(context), download, journal)
        req = NextWorldRequest(2, package.checkpoint_id, b'\x51'*16, 203, 8, 11); warm.request = req
        p = Profile(); p.file.name = files.NAME.encode(); p.file.slot = 63; p.file.size = len(raw)
        p.file.sha256[:] = bytes.fromhex(sha(raw)); p.before = Date(203, 8, 1); p.loaded = Date(203, 8, 11)
        p.source = Identity(666, 12, 11); p.target = Identity(952, 2, 2); p.currentForce = 12
        class ControlDouble:
            player_id = 'B'
            def __init__(self): self.packets = []
            def request(self, packet):
                self.packets.append(packet)
                return dict(ok=True, warm_completion=dict(packet=packet, source='EXPLICIT_CONTROL_DOUBLE',
                    full_world_verified=False, ready_authorized=False, next_period_authorized=False, native_gameplay_enabled=False))
        control = ControlDouble()
        rejected = BootstrapReceivedApply(bridge, control, scope=scope, epoch=epoch, period=1,
                                         attachments=attachments, on_hold=lambda reason: holds.append(reason))
        claimed_reservation = dict(checkpoint_id=package.checkpoint_id, intent='a'*32, native_load_permitted_once=True)
        with self.assertRaisesRegex(files.Refused, 'First source-view bootstrap needs its own formal journal boundary'):
            rejected.apply(received, req, p, observe_loaded=rules.observe, prepare_rules=rules.prepare,
                           reservation=claimed_reservation)
        self.assertFalse(warm.events); self.assertFalse(control.packets); self.assertEqual(len(holds), 1)
        self.assertFalse((download/'warm-local-load-intent.json').exists())
        adapter = BootstrapReceivedApply(bridge, control, scope=scope, epoch=epoch, period=1,
                                        attachments=attachments, on_hold=lambda reason: holds.append(reason))
        answer = adapter.apply(received, req, p, observe_loaded=rules.observe, prepare_rules=rules.prepare)
        self.assertEqual(len(control.packets), 1); self.assertEqual(control.packets[0]['viewer_force'], 2)
        self.assertEqual(journal.status()['status'], 'STAGED'); self.assertFalse(answer['ready'])
        self.assertTrue((download/'warm-local-load-intent.json').is_file())
        self.assertTrue((download/'warm-local-load-completion.json').is_file())
        self.assertTrue((download/'warm-ack-attempt.json').is_file()); self.assertEqual(len(holds), 1)
        self.assertEqual(Config.from_buffer_copy(life.current.world.config).viewer, 2)
        with self.assertRaises(Exception): adapter.apply(received, req, p, observe_loaded=rules.observe, prepare_rules=rules.prepare)
        self.assertEqual(len(control.packets), 1); self.assertEqual(len(warm.events), 2)
        EVIDENCE.append(dict(case='received-bootstrap-apply', real_receiver_journal=True,
                             transport='EXPLICIT_CONTROL_DOUBLE', diagnostic_ack=control.packets[0],
                             first_formal_reservation_rejected=True, ready=False))


def pins():
    paths = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    paths.add(Path(__file__).resolve())
    return {str(p): sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE/'b_warm_bootstrap_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); OUTPUT.mkdir(parents=True)
    before = pins(); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    sources = pins(); stable = all(sources.get(k)==v for k,v in before.items())
    report = dict(family='san14.b-warm-bootstrap-files.v1', result='PASS' if result.wasSuccessful() and result.testsRun==6 and stable else 'FAIL',
        tests=result.testsRun, sources=sources, inputs_unchanged=stable, cases=EVIDENCE, actual_windows_files=True,
        actual_resident_port_lifecycle=True, native_memory_publisher='EXPLICIT_DOUBLE', game_access=False,
        failures=[(str(t), d) for t,d in result.failures+result.errors])
    report['artifacts'] = {str(p): sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json'); print(stream.getvalue())
    raise SystemExit(0 if report['result']=='PASS' else 1)
