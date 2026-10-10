"""Explicit finite observer for an authenticated same-day reward planning window.
Original predicates remain; ready0 requires actual Op15 and quiet Op13 readback.
No Runtime field is rewritten or passed to the predecessor as fabricated ready1.
"""
from a_observed_boundary import *
from a_observed_boundary import AObservedBoundary as FrozenBoundary

class AObservedBoundary(FrozenBoundary):
    reward_mount=None
    def _runtime(self):
        self._identity()
        value=self.runtime_snapshot()
        need(type(value) is wire.Snapshot,'Exact typed Runtime Snapshot required')
        s=wire.decode(wire.Snapshot,'Snapshot',self.nonce,bytes(value))
        if s.header.result==10:raise NotReady('Runtime Snapshot is explicitly NotReady')
        need(s.header.result==0,'Runtime Snapshot failed')
        need(all(getattr(s,k)==1 for k in ('prepared','ownerArmed','sourcesArmed','hostInitialized','hostCacheValid')),
             'Runtime has not reached its controlled planning state')
        if s.ready==0 and self.reward_mount is not None:
            self.reward_mount.planning_quiet()
        else:need(s.ready==1,'Runtime is not ready outside authenticated open reward planning')
        need(all(getattr(s,k)==0 for k in ('error','stopped','ownerError','ownerStopped','saveLane','saveError',
            'saveActive','ownerActive','gateActive','parentActive','parentError','mailboxStopped','hostLease','hostFrame',
            'productionPermit','allWritersProven','restoreReady')),'Runtime failed, active, stopped or claims unsupported authority')
        need(s.hostThread and s.hostCacheAddress and s.hostCacheSequence%2==0 and s.hostState in (0,3),
             'Host cache is not an idle/completed observation')
        need(s.parentBefore==s.parentAfter==s.parentFinally and s.parentBefore>0,'Parent callback pair is incomplete')
        need(s.mailboxCount<=2 and list(s.mailboxStates)==[5]*s.mailboxCount+[0]*(2-s.mailboxCount),
             'Pending or unknown mailbox request')
        if s.saveStatus==0:
            need(s.saveGeneration==0 and not any(getattr(s,k) for k in
                ('binds','queues','phaseMask','workerJoined','originalReturned','fileVerified')) and s.mailboxCount==0,
                'Idle report contains a prior/pending save')
        else:
            need(s.saveStatus==5 and s.saveGeneration in (1,2) and s.mailboxCount==s.saveGeneration and
                 s.binds==s.queues==s.workerJoined==s.fileVerified==1 and s.phaseMask==31 and s.originalReturned>0,
                 'Prior Save lacks real Complete/Copy/drain evidence')
        for actual,plan in zip(s.counters,self.plans.counters):
            need((actual.startedAddress,actual.activeAddress)==(plan.startedAddress,plan.activeAddress) and
                 actual.startedAddress and actual.activeAddress and actual.active==0,'Foreign or active bridge counters')
        return s
