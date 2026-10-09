"""Explicit authority successor for B already at the target planning date.

Bootstrap keeps its old-date source view. Ordinary correction requires a
truthful target-date Profile.before, enabling protocol reconciliation after
independent simulations. This does not implement simulation, native waiting,
or rules rebinding across that simulation. No permissive date autodetection.
The frozen remote completion keeps its old-date diagnostic semantics.
"""
from copy import deepcopy
from authoritative_sync import CheckpointReceiver, hexid
from b_warm_remote_completion import RemoteCompletionRoom, profile_from, need


class SettledRemoteCompletionRoom(RemoteCompletionRoom):
    """Chosen by A's local launcher, never selected by an untrusted packet.

    Same key enrollment, authenticated wire, one-shot journal, duplicate and
    completion validation as predecessor. Only the begin date contract differs.
    """
    def _begin(self, b):
        need(set(b) == {'kind', 'context', 'profile', 'guest_before', 'bootstrap'}, 'Wrong begin fields')
        c = self._coordinator; r = self._remote; context = b['context']; m = context['manifest']
        need(type(b['bootstrap']) is bool, 'Explicit journal kind required')
        need(context == dict(scope=c.scope, manifest=c.manifest, checkpoint_id=c.checkpoint_id, attachments=c.attachments)
             and c.phase == 'RECONCILING' and c.load_intent is None and self.artifacts is not None and
             not self.artifacts.closed, 'Offered context no longer current')
        need(c.checkpoint_id not in r['rows'] and len(r['rows']) < 16, 'Once-only adapter window exhausted')
        p = profile_from(b['profile'])
        need((p.file.size, bytes(p.file.sha256).hex()) ==
             (m['parts']['world.s14']['size'], m['parts']['world.s14']['sha256']), 'Profile file differs')
        # Bootstrap still starts at A's old planning date. Ordinary corrections
        # require B's truthful settled target date, never a fabricated old date.
        before_node = c.node if b['bootstrap'] else m['node']
        need(tuple(before_node[k] for k in ('year', 'month', 'day')) ==
             (p.before.year, p.before.month, p.before.day) and
             tuple(m['node'][k] for k in ('year', 'month', 'day')) ==
             (p.loaded.year, p.loaded.month, p.loaded.day),
             'Settled correction profile dates differ')
        for side, ident in (('A', p.source), ('B', p.target)):
            need(c.scope['bindings'][side] == dict(force_id=ident.force, main_district_id=ident.district), 'Profile faction differs')
        if b['bootstrap']:
            need(c.period == 1 and not c.applied_receipts and p.currentForce == p.source.force,
                 'Bootstrap is initial truthful source view only')
        else: need(p.currentForce == p.target.force, 'Ordinary load requires target view')
        viewer = p.source.force if b['bootstrap'] else p.target.force
        need(b['guest_before'] == dict(attachment=c.attachments['B'], viewer_force=viewer, safe_boundary=True),
             'Authenticated pre-load boundary differs')
        sc = dict(scope=c.scope, epoch=c.epoch, period=c.period, node=m['node'])
        host_key = r['host_key']()
        need(hexid(host_key) and int(host_key, 16), 'Current A receipt identity required')
        a = r['helper']._sample('A', p, host_key, sc)
        need(a['partial_sha256'] == m['world_sha256'], 'A projection changed before remote load')
        # Reconstruct A's immutable transmitted bytes; B's separately signed
        # begin is the retained adapter's assertion that its Journal is STAGED.
        receiver = CheckpointReceiver(m, c.checkpoint_id, c.scope, c.epoch, c.period, m['cut'])
        for chunk in self.artifacts.chunks.values(): receiver.accept(chunk)
        c.received('B', c.epoch, receiver)
        intent = c.begin_guest_load('B', c.epoch)
        row = dict(context=deepcopy(context), profile=b['profile'], intent=intent, a=a, host_key=host_key,
                   begin=deepcopy(b), reply=None, complete=None)
        r['rows'][c.checkpoint_id] = row
        return dict(ok=True, checkpoint_id=c.checkpoint_id, intent=intent, host_observation=dict(attachment=c.attachments['A'],
                    world_sha256=m['world_sha256'], node=m['node']), native_gameplay_enabled=False)
