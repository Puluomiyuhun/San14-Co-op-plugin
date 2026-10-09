"""Read-only current-world Config adapter for retained native rules owners.

No discovery, process opening, DLL load, Prepare, Seal or publication. A caller
retains its actual process reader, room and native execution/input fence.
"""
from copy import deepcopy
import ctypes as C
import struct

from room_session import Room, digest
from authoritative_sync import scope_from_room
from checkpoint_room_lifecycle import CheckpointRoom
from b_warm_room import WarmRoom
from human_rules_activation_room import Config, GAME_SHA, rules
from human_rules_world_lifecycle import WorldGeneration, NextWorldRequest, check_port
import b_warm_world as memory


def need(ok, message):
    if not ok: raise ValueError(message)


class RulesWorldCapture:
    def __init__(self, reader, room, settings, *, pid, birth, read_birth, guard_check):
        need(type(room) in (Room, CheckpointRoom, WarmRoom), 'Actual supported local Room required')
        need(type(pid) is int and 0<pid<2**32 and type(birth) is int and 0<birth<2**64,
             'Explicit process incarnation required')
        need(callable(read_birth) and callable(guard_check), 'Retained identity/fence callbacks required')
        need(type(settings) is dict and settings==rules(settings.get('native_income_key5'),settings.get('native_world_option8')),
             'Unsupported settings')
        self.reader,self.room,self.settings=reader,room,deepcopy(settings)
        self.pid,self.birth,self.read_birth,self.guard_check=pid,birth,read_birth,guard_check
        self.image=reader.memory.base
        need(type(self.image) is int and 0x10000<=self.image<0x7fffffffffff-0x2238000,'Invalid image')
        with room.lock:
            self.scope=deepcopy(scope_from_room(room))
            self.connections={p:r['connection'] for p,r in room.players.items()}
        self._check()

    def _check(self):
        check_port(self.guard_check)
        r=self.reader
        need(r.pid==self.pid and r.memory.base==self.image and r.sha256==GAME_SHA and
             self.read_birth()==self.birth,'Pinned process/image incarnation changed')
        with self.room.lock:
            scope=scope_from_room(self.room)
            need(scope==self.scope and {p:r['connection'] for p,r in self.room.players.items()}==self.connections and
                 all(r['confirmed'] for r in self.room.players.values()),'Room scope/connection changed')
            need(scope['profile']['game_sha256']==GAME_SHA and
                 scope['profile']['rules_sha256']==digest(self.settings),'Room rules/build differ')
            need(not getattr(self.room,'_closed',False) and getattr(self.room,'_held',None) is None,
                 'Room closed or held')

    def _capture(self, generation, checkpoint, epoch, side, ruler, expected_date):
        self._check()
        need(side in ('A','B'),'Explicit local viewer side required')
        memory.integer(ruler,high=6000)
        need(type(epoch) is bytes and len(epoch)==16 and any(epoch),'Explicit native generation epoch required')
        viewer=self.scope['bindings'][side]['force_id']
        reads=memory.Reads(self.reader.memory.read)
        def value(at, fmt):
            return struct.unpack(fmt,reads.read(at,struct.calcsize(fmt)))[0]
        def once():
            snapshot=self.reader.snapshot()
            date=tuple(snapshot['date'][k] for k in ('year','month','day'))
            if expected_date is not None:need(date==expected_date,'Requested loaded date differs')
            context=memory.context(self.reader,reads,self.read_birth,(*date,viewer,ruler))
            need(context['pid']==self.pid and context['birth']==self.birth and context['base']==self.image,
                 'Native context belongs to another incarnation')
            need(value(self.image+0x1FD0C5C,'<i') not in (0,-1),'Settings singleton not initialized')
            income=value(self.image+0x18EB628,'<I')
            option=(value(context['world']+0x16A8,'<I')>>8)&1
            need((income,option)==(self.settings['native_income_key5'],self.settings['native_world_option8']),
                 'Actual native settings differ from authenticated rules')
            c=Config(version=1,size=C.sizeof(Config),image=self.image,root=context['root'],world=context['world'])
            c.room[:]=bytes.fromhex(self.scope['room_id']);c.epoch[:]=epoch
            c.rules_digest[:]=bytes.fromhex(digest(self.settings))
            for i,p in enumerate(('A','B')):
                c.force[i]=self.scope['bindings'][p]['force_id']
                c.main_district[i]=self.scope['bindings'][p]['main_district_id']
            c.viewer=viewer;c.year,c.month,c.day=date;c.income_key5=income;c.world_option8=option
            return bytes(c),context
        first=once();second=once()
        need(first==second,'Native rule configuration changed during capture')
        self._check()
        # Config.epoch is this native activation generation; the immutable room
        # binding_epoch is independently pinned above and must not be replaced.
        return WorldGeneration(generation,checkpoint,first[0])

    def capture_loaded(self, request, *, side, expected_ruler):
        """Actual local observer after accepted load; no load-completion claim.

        Explicit side permits the bootstrap observer to read target B after an
        old A-view binding. The caller owns that transition authorization.
        """
        need(type(request) is NextWorldRequest,'Typed local world request required')
        return self._capture(request.generation,request.checkpoint,request.epoch,side,expected_ruler,
                             (request.year,request.month,request.day))

    def export_current(self, world, *, expected_ruler):
        """Fresh bytes for ResidentPort; its own comparison handles date advance.

        This does not refresh or overwrite the old module's immutable binding.
        """
        need(type(world) is WorldGeneration,'Typed retained world binding required')
        c=Config.from_buffer_copy(world.config)
        sides=[p for p in ('A','B') if self.scope['bindings'][p]['force_id']==c.viewer]
        need(len(sides)==1 and c.image==self.image and bytes(c.room).hex()==self.scope['room_id'] and
             bytes(c.rules_digest).hex()==digest(self.settings) and
             list(c.force)==[self.scope['bindings'][p]['force_id'] for p in ('A','B')] and
             list(c.main_district)==[self.scope['bindings'][p]['main_district_id'] for p in ('A','B')] and
             (c.income_key5,c.world_option8)==(self.settings['native_income_key5'],self.settings['native_world_option8']),
             'Retained Config differs from actual room rules')
        return self._capture(world.generation,world.checkpoint,bytes(c.epoch),sides[0],expected_ruler,None).config
