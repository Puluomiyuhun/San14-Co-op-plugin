"""Authenticated guest diagnostics visible through the persistent control room.

Progress is advisory: it cannot create a load/world receipt, readiness, a new
epoch or reveal/input permission. Fields are bounded and credentials excluded.
"""
from copy import deepcopy

from checkpoint_room_lifecycle import CheckpointRoom
from checkpoint_room_artifacts import RoomError, SyncError, require
from authoritative_sync import canonical, hexid, digest

NEXT={
    None:{'RECEIVING','HELD'},
    'RECEIVING':{'RECEIVING','STAGED','HELD'},
    'STAGED':{'LOAD_REQUESTED','HELD'},
    'LOAD_REQUESTED':{'IDENTITY_RESTORED','HELD'},
    'IDENTITY_RESTORED':{'WAITING_WORLD','HELD'},
    'WAITING_WORLD':{'WAITING_WORLD','HELD'},
    'HELD':set(),
}
REASONS={'NONE','TRANSFER_FAILED','LOAD_UNCERTAIN','WAITING_PLANNING','WORLD_PROVIDER_MISSING'}
FIELDS={'action','checkpoint_id','epoch','sequence','stage','received_bytes','intent','reason'}


class ProgressRoom(CheckpointRoom):
    def __init__(self,manifest):
        super().__init__(manifest)
        self._guest_progress=None
        self._last_progress_packet=None

    def install_offered_checkpoint(self,coordinator,package):
        with self.lock:
            old=self.artifacts.checkpoint_id if self.artifacts else None
            service=super().install_offered_checkpoint(coordinator,package)
            if old!=service.checkpoint_id:
                self._guest_progress=None
                self._last_progress_packet=None
            return service

    def view(self,player):
        with self.lock:
            state=super().view(player)
            state['checkpoint']=self.checkpoint_status()
            state['guest_progress']=deepcopy(self._guest_progress)
            return state

    def _record_progress(self,player,connection,packet):
        require(type(packet) is dict and set(packet)==FIELDS,'Invalid progress fields')
        require(player=='B' and self.players.get('B',{}).get('connection')==connection,
                'Only the authenticated guest may report guest progress')
        require(self._coordinator is not None and self.artifacts is not None,'No active checkpoint')
        c=self._coordinator
        with c.lock:
            self._bound(c)
            m=self.artifacts.manifest
            require(c.phase=='RECONCILING' and c.connected=={'A','B'} and
                c.scope==self._scope and c.period==m['period'] and c.manifest==m and digest(m)==self.artifacts.checkpoint_id and
                c.checkpoint_id==self.artifacts.checkpoint_id==packet['checkpoint_id'] and
                c.epoch==m['epoch']==packet['epoch'],'Progress belongs to an inactive checkpoint')
            require(type(packet['sequence']) is int and 1<=packet['sequence']<2**32 and
                type(packet['stage']) is str and packet['stage'] in NEXT and
                type(packet['reason']) is str and packet['reason'] in REASONS and
                type(packet['received_bytes']) is int,'Invalid progress values')
            require(packet['intent'] is None or hexid(packet['intent'],32),'Invalid progress intent')
            total=sum(row['size'] for row in m['parts'].values())
            require(0<=packet['received_bytes']<=total,'Invalid progress byte count')
            last=self._last_progress_packet
            if last is not None and packet['sequence']==last['sequence']:
                require(canonical(packet)==last['canonical'],'Conflicting progress replay')
                return {'ok':True,'duplicate':True,'guest_progress':deepcopy(self._guest_progress)}
            expected=1 if last is None else last['sequence']+1
            previous=self._guest_progress['stage'] if self._guest_progress else None
            require(packet['sequence']==expected and packet['stage'] in NEXT[previous],
                    'Skipped sequence or invalid progress transition')
            require(self._guest_progress is None or packet['received_bytes']>=self._guest_progress['received_bytes'],
                    'Download progress went backwards')
            stage=packet['stage'];reason=packet['reason']
            if stage in ('RECEIVING','STAGED'):
                require(packet['intent'] is None and c.load_intent is None and reason=='NONE',
                        'Transfer progress cannot claim a load attempt')
            elif stage=='HELD':
                require(reason in REASONS-{'NONE','WORLD_PROVIDER_MISSING'} and packet['intent']==c.load_intent,
                        'Invalid held diagnostic context')
            else:
                require(c.load_intent is not None and packet['intent']==c.load_intent,
                        'Load progress needs the existing local reservation')
                require(reason==('WORLD_PROVIDER_MISSING' if stage=='WAITING_WORLD' else 'NONE'),
                        'Unexpected progress reason')
            if stage not in ('RECEIVING','HELD'):
                require(packet['received_bytes']==total,'Incomplete transfer cannot report later stages')
            self._guest_progress=dict(checkpoint_id=packet['checkpoint_id'],epoch=packet['epoch'],
                sequence=packet['sequence'],stage=stage,reason=reason,received_bytes=packet['received_bytes'],
                total_bytes=total,source='GUEST_REPORTED_DIAGNOSTIC',grants_permission=False,
                native_gameplay_enabled=False,full_world_verified=False)
            self._last_progress_packet={'sequence':packet['sequence'],'canonical':canonical(packet)}
            return {'ok':True,'duplicate':False,'guest_progress':deepcopy(self._guest_progress)}

    def handle(self,player,connection_id,request):
        if type(request) is dict and request.get('action')=='checkpoint_progress':
            try:
                with self.lock:return self._record_progress(player,connection_id,request)
            except (RoomError,SyncError) as exc:
                return {'ok':False,'error':str(exc),'applied_to_game':False}
        return super().handle(player,connection_id,request)
