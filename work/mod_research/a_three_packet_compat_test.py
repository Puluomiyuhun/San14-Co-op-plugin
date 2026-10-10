"""Read archived owned-native packets only; never publish/replay them in a room.

This checks the three-save decoder against actual native owner exports and
corruption. The archive is not current native source identity or an install permit.
"""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest

import checkpoint_three_save_packet as current
import checkpoint_fresh_save_packet as old

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'
ARCHIVE = PRIVATE / 'a_save_three_cycle_runs/20261010-164123-271568'
ARCHIVE_SHA = '36948587d5397cc1189a1e84e25e622e58bec2487b1be28a2b0dcc32fe1c9a62'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert sha(ARCHIVE/'result.json') == ARCHIVE_SHA
        cls.record = json.loads((ARCHIVE/'result.json').read_text())
        assert cls.record['result'] == 'PASS' and cls.record['game_access'] is False
        cls.raw = []
        for n in (1, 2, 3):
            path = ARCHIVE / f'native/case/normal/normal-{n}.packet'
            assert sha(path) == cls.record['artifacts'][str(path.relative_to(ARCHIVE))]
            cls.raw.append(path.read_bytes())

    def test_actual_three_native_exports_decode_without_authority(self):
        decoded = [current.decode_packet(raw) for raw in self.raw]
        self.assertEqual([x.report['completed_requests'] for x in decoded], [1, 2, 3])
        self.assertEqual([(x.request['month'],x.request['day']) for x in decoded], [(8,11),(8,21),(9,1)])
        self.assertTrue(all(not x.report['full_world'] and not x.report['room_ready'] for x in decoded))
        self.assertTrue(all(type(x) is old.DecodedArtifact for x in decoded))

    def test_predecessor_still_rejects_third_packet(self):
        old.decode_packet(self.raw[0]);old.decode_packet(self.raw[1])
        with self.assertRaises(old.PacketError):old.decode_packet(self.raw[2])

    def test_corruption_truncation_and_fourth_count_rejected(self):
        raw = bytearray(self.raw[2]);raw[-1] ^= 1
        with self.assertRaises(current.PacketError):current.decode_packet(bytes(raw))
        with self.assertRaises(current.PacketError):current.decode_packet(self.raw[2][:-1])
        fields = list(current.REPORT.unpack_from(self.raw[2],current.PREFIX.size+current.REQUEST.size))
        fields[current.REPORT_FIELDS.index('completed_requests')] = 4
        raw = bytearray(self.raw[2])
        current.REPORT.pack_into(raw,current.PREFIX.size+current.REQUEST.size,*fields)
        with self.assertRaises(current.PacketError):current.decode_packet(bytes(raw))


if __name__ == '__main__':
    run=PRIVATE/'a_three_packet_compat_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    sources={str(p):sha(p) for p in (Path(__file__),P/'checkpoint_three_save_packet.py',P/'checkpoint_fresh_save_packet.py')}
    log=io.StringIO()
    r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (run/'test.log').write_text(log.getvalue(),encoding='utf-8')
    private_inputs={str(ARCHIVE/'result.json'):ARCHIVE_SHA}
    private_inputs.update({str(p):sha(p) for p in (ARCHIVE/'native/case/normal').glob('normal-*.packet')})
    report=dict(result='PASS' if r.wasSuccessful() and r.testsRun==3 else 'FAIL',tests=r.testsRun,
        sources=sources,private_inputs=private_inputs,
        archived_owned_packets_only=True,active_room_publication=False,game_access=False,native_install_permit=False)
    report['artifacts']={'test.log':sha(run/'test.log')}
    (run/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue());print(run/'result.json')
    raise SystemExit(report['result']!='PASS')
