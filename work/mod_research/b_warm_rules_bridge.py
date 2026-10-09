"""Local bridge: restore human rules, stage/load a checkpoint, bind new rules.

This is not a launcher or network permission endpoint. The caller must retain
the WorldLifecycle execution/input fence throughout replacement. Warm Resident
owns native load completion; the lifecycle owns actual six-entry publication.
Neither a JSON receipt nor a successful file transfer grants Ready here.
"""
from contextlib import ExitStack
from pathlib import Path
import secrets
import threading
import time

import b_warm_staging as files
from b_warm_profile_contract import Profile, validate_profile
from human_rules_world_lifecycle import Config, NextWorldRequest, WorldLifecycle


class WarmRulesBridge:
    def __init__(self, lifecycle, warm_port, *, target, records):
        files.need(type(lifecycle) is WorldLifecycle, 'Actual local rule lifecycle required')
        files.need(all(callable(getattr(warm_port, n, None)) for n in
                       ('open_bank', 'authorize_second', 'load', 'abort')), 'Missing retained warm port')
        self.lifecycle, self.warm = lifecycle, warm_port
        self.target, self.records = files.clean_path(target), files.clean_path(records)
        files.need(self.target.name == files.NAME and self.records.is_dir() and
                   self.records != self.target.parent, 'Existing independent records and CC03 target required')
        self.completed = []
        self.phase = 'ACTIVE'
        self._lock = threading.RLock()

    def replace(self, request, profile, source, *, observe_loaded, prepare_rules):
        with self._lock:
            files.need(self.phase == 'ACTIVE' and len(self.completed) < 2,
                       'Bridge consumed/held; no automatic retry or DLL reset')
            self.phase = 'REPLACING'
            result = None
            try:
                # Validation deliberately runs inside lifecycle.load so any
                # refusal after entering replacement retains the real fence.
                def load(actual_request):
                    nonlocal result
                    files.need(actual_request is request and type(request) is NextWorldRequest and
                               type(profile) is Profile, 'Typed local request/profile required')
                    validate_profile(profile)
                    config = Config.from_buffer_copy(self.lifecycle.current.world.config)
                    files.need((profile.loaded.year, profile.loaded.month, profile.loaded.day) ==
                               (request.year, request.month, request.day), 'Requested loaded date differs')
                    files.need(profile.currentForce == config.viewer == profile.target.force and
                               set(config.force) == {profile.source.force, profile.target.force},
                               'Warm profile changes human factions/viewer')
                    index = len(self.completed)
                    folder = self.records / ('generation-' + str(request.generation))
                    folder.mkdir()
                    bank = self.warm.open_bank(index)
                    if index:
                        self.warm.authorize_second(bank, profile)
                    proposed = files.plan(source, self.target.parent,
                                          bytes(profile.file.sha256).hex(), profile.file.size)
                    if index:
                        files.need(proposed['previous_identity'] == self.completed[-1]['file_identity'],
                                   'Previous retired checkpoint file changed')
                    # This reference is only a pinned audit record. Authority is
                    # the still-held lifecycle guard and native warm handover.
                    evidence = folder / 'rules-restored.json'
                    files.save_new(evidence, files.canonical(dict(
                        history=self.lifecycle.history, generation=request.generation,
                        checkpoint=request.checkpoint, permission=False)))
                    permit = folder / 'file-authorization.json'
                    files.save_new(permit, files.canonical(dict(
                        schema='san14.local-file-overwrite-authorization.v1',
                        nonce=secrets.token_hex(16), expires_unix=int(time.time()) + 120,
                        plan_sha256=files.digest(files.canonical(proposed)),
                        retirement_reference=str(evidence),
                        retirement_sha256=files.digest(evidence.read_bytes()))))
                    staged = files.apply(proposed, permit, files.digest(permit.read_bytes()), folder)
                    files.need(staged['result'] == 'STAGED', 'Checkpoint staging incomplete; retain hold')
                    with ExitStack() as held:
                        files.pin_parents(held, self.target)
                        handle = held.enter_context(files.Handle(self.target))
                        identity, raw = handle.snapshot()
                        files.need((identity['size'], identity['sha256']) ==
                                   (profile.file.size, bytes(profile.file.sha256).hex()), 'Staged file differs')
                        try:
                            completion = self.warm.load(bank, profile, raw)
                            files.need(type(completion) is dict, 'Missing local warm completion')
                            files.need(handle.snapshot()[0] == identity, 'File changed during native load')
                        except BaseException:
                            self.warm.abort()  # lease remains held during bounded Stop
                            raise
                    result = dict(file_identity=identity, completion=completion, staging=staged)
                    return None

                rebound = self.lifecycle.replace(request, load=load,
                    observe_loaded=observe_loaded, prepare=prepare_rules)
                files.need(result is not None, 'Missing replacement result')
                result['rules'] = rebound
                self.completed.append(result)
                self.phase = 'ACTIVE'
                return dict(result='WARM_LOAD_AND_RULES_REBOUND', generation=request.generation,
                            checkpoint=request.checkpoint, details=result, ready=False,
                            fence_released=False, full_world_verified=False)
            except BaseException:
                self.phase = 'HELD'
                raise
