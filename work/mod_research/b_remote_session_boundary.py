"""Repeated planning observations for an explicit no-new-command diagnostic.

This is NOT execution/input exclusion. Each successful observation comprises
the unchanged native sampler's two equal complete samples; the game can run
between observations. There is no verify_held or boolean permission adapter.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
import threading

from b_warm_profile_contract import Profile, Date, validate_profile
from b_warm_stable_capture import capture_planning


def need(ok, message):
    if not ok: raise ValueError(message)


@dataclass(frozen=True)
class Observation:
    sequence: int
    pid: int
    birth: int
    profile_sha256: str
    sample_sha256: str
    human_no_new_commands: bool = True
    input_exclusion_proven: bool = False
    scheduler_fence_proven: bool = False
    atomic_snapshot: bool = False


class DiagnosticBoundary:
    def __init__(self, reader, profile, *, pid, birth, no_new_commands):
        need(no_new_commands is True, 'Explicit human no-new-command condition required')
        validate_profile(profile)
        need(type(pid) is int and 0 < pid < 2**32 and type(birth) is int and 0 < birth < 2**64,
             'Pinned process incarnation required')
        self.reader, self.pid, self.birth = reader, pid, birth
        self.image = reader.memory.base
        self.profile = Profile.from_buffer_copy(bytes(profile))
        self.records = []; self.failed = None; self._lock = threading.RLock()

    def observe(self):
        with self._lock:
            need(self.failed is None, 'Diagnostic boundary terminal; no replay')
            p = self.profile
            ruler = p.source.ruler if p.currentForce == p.source.force else p.target.ruler
            evidence = {}
            try:
                need(self.reader.pid==self.pid and self.reader.memory.base==self.image,
                     'Diagnostic reader/image changed')
                sample = capture_planning(self.reader, p, ruler, expected_pid=self.pid,
                                          expected_birth=self.birth, evidence=evidence)
                need(sample.get('atomic_snapshot') is False, 'Sampler coverage differs')
                result = Observation(len(self.records)+1, self.pid, self.birth,
                    hashlib.sha256(bytes(p)).hexdigest(),
                    hashlib.sha256(json.dumps(sample, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
                self.records.append(dict(observation=asdict(result), evidence=evidence))
                return result
            except BaseException as exc:
                self.failed = type(exc).__name__ + ': ' + str(exc)
                self.records.append(dict(error=self.failed, evidence=evidence))
                raise

    def check(self):
        # Legacy transition predicates require an exception-or-None callback.
        # The new lifecycle explicitly interprets it as an observation only.
        self.observe()

    def begin(self, profile):
        with self._lock:
            validate_profile(profile); old = self.profile
            need(bytes(old.before) == bytes(profile.before) and old.currentForce == profile.currentForce and
                 bytes(old.source) == bytes(profile.source) and bytes(old.target) == bytes(profile.target),
                 'Next diagnostic profile changes the retained planning boundary')
            self.profile = Profile.from_buffer_copy(bytes(profile))
            return self.observe()

    def loaded(self, profile):
        """Only the bridge calls this after its full native retirement acceptance."""
        with self._lock:
            need(bytes(self.profile) == bytes(profile), 'Completed profile changed')
            next_profile = Profile.from_buffer_copy(bytes(profile))
            next_profile.before = Date(profile.loaded.year, profile.loaded.month, profile.loaded.day)
            next_profile.currentForce = profile.target.force
            self.profile = next_profile
            return self.observe()

    def hold(self, reason):
        with self._lock:
            if self.failed is None: self.failed = str(reason)
        # Local terminal state only. It neither stops native execution nor
        # releases/unloads native resources or silently restores any patches.
