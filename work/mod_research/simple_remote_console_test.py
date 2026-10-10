"""Offline local operator parsing/lifetime tests, no game or network access."""
import io
import json
import threading
import unittest
from simple_remote_console import Console, parse


class Cases(unittest.TestCase):
    def setUp(self):
        self.calls, self.failures, self.output = [], [], []
        self.console = Console(on_reward=self.reward, on_ready=self.ready,
                               on_failure=self.failures.append, emit=self.output.append)

    def reward(self, identity, district, ids):
        self.calls.append((identity, district, ids))
        return dict(ok=True, status='QUEUED', request_id=identity)

    def ready(self, identity):
        self.calls.append(('ready', identity))
        return dict(ok=True)

    def packet(self, **kw):
        return json.dumps(dict(action='reward', request_id='a'*32, district_id=12, officer_ids=[97], **kw))

    def test_duplicate_preserves_identity_and_calls_once(self):
        first = self.console.submit_line(self.packet())
        first['result']['status'] = 'MUTATED'
        second = self.console.submit_line(self.packet())
        self.assertEqual(self.calls, [('a'*32, 12, [97])])
        self.assertTrue(second['duplicate'])
        self.assertEqual(second['result']['status'], 'QUEUED')

    def test_changed_payload_is_terminal(self):
        self.console.submit_line(self.packet())
        changed = json.loads(self.packet()); changed['officer_ids'] = [98]
        with self.assertRaises(RuntimeError): self.console.submit_line(json.dumps(changed))
        with self.assertRaises(RuntimeError): self.console.submit_line(self.packet())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.failures), 1)

    def test_unknown_outcome_is_not_retried(self):
        def lost(*args):
            self.reward(*args)
            raise TimeoutError('Reply lost after submission')
        self.console.on_reward = lost
        with self.assertRaises(TimeoutError): self.console.submit_line(self.packet())
        with self.assertRaises(RuntimeError): self.console.submit_line(self.packet())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.console.rows['a'*32]['state'], 'UNKNOWN')

    def test_ready_once_blocks_new_rewards(self):
        ready = json.dumps(dict(action='ready', request_id='b'*32))
        self.console.submit_line(ready)
        self.assertTrue(self.console.submit_line(ready)['duplicate'])
        with self.assertRaises(ValueError): self.console.submit_line(self.packet())
        self.assertEqual(self.calls, [('ready', 'b'*32)])

    def test_eof_never_ready(self):
        self.console.start(io.StringIO(''))
        self.console.thread.join(2)
        self.assertFalse(self.console.thread.is_alive())
        self.assertEqual(self.calls, [])
        self.assertFalse(self.output[0]['automatic_ready'])

    def test_bad_syntax_and_oversized_line_dont_become_commands(self):
        self.console.start(io.StringIO('bad\n'+'x'*5000+self.packet()+'\n'+self.packet()+'\n'))
        self.console.thread.join(2)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(sum(r['event']=='operator-rejected' for r in self.output), 2)

    def test_strict_fields_types_and_duplicate_keys(self):
        valid = json.loads(self.packet())
        for change in ({'district_id': True}, {'officer_ids': [97, 97]}, {'officer_ids': [True]},
                       {'officer_ids': [6000]}, {'address': 123}, {'action': 'execute'}):
            with self.subTest(change=change), self.assertRaises(ValueError): parse(json.dumps({**valid, **change}))
        with self.assertRaises(ValueError): parse('{"action":"ready","action":"ready","request_id":"'+'a'*32+'"}')

    def test_closed_console_never_dispatches(self):
        self.console.close()
        with self.assertRaises(RuntimeError): self.console.submit_line(self.packet())
        with self.assertRaises(RuntimeError): self.console.start(io.StringIO(self.packet()))
        self.assertEqual(self.calls, [])

    def test_close_drains_inflight_callback_before_cleanup(self):
        entered, release, closed = threading.Event(), threading.Event(), threading.Event()
        def waiting(*args):
            entered.set()
            if not release.wait(2): raise TimeoutError('Test callback was not released')
            return self.reward(*args)
        self.console.on_reward = waiting
        producer = threading.Thread(target=self.console.submit_line, args=(self.packet(),))
        producer.start()
        self.assertTrue(entered.wait(2))
        def close():
            self.console.close()
            closed.set()
        closer = threading.Thread(target=close)
        closer.start()
        self.assertFalse(closed.wait(.02))
        release.set()
        producer.join(2); closer.join(2)
        self.assertTrue(closed.is_set())
        self.assertFalse(producer.is_alive() or closer.is_alive())
        with self.assertRaises(RuntimeError): self.console.submit_line(self.packet())
        self.assertEqual(len(self.calls), 1)

    def test_output_failure_after_ack_is_terminal_not_resend(self):
        def broken(_): raise OSError('Console output closed')
        self.console.emit = broken
        self.console.start(io.StringIO(self.packet()+'\n'+self.packet()+'\n'))
        self.console.thread.join(2)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.failures), 1)
        self.assertTrue(self.console.failed)


if __name__ == '__main__':
    unittest.main()
