"""Three reservation successor for the dedicated three-save runtime only.
No constructor connects it to installed predecessor modules or native processes.
"""
import re
from types import MappingProxyType
from checkpoint_fresh_save_binding import (FreshSaveBinding as Previous,
    LocalWorldObservation, SaveReservation, require, _u64)
from authoritative_sync import digest

class ThreeFreshSaveBinding(Previous):
    def reserve(self, generation: int, filename: str,
                observation: LocalWorldObservation) -> SaveReservation:
        """Freeze full protocol context before the caller's native Submit.

        Reservation consumes this local generation even if a later native
        Submit fails. It never retries a native request or reuses its filename.
        """
        with self.room.lock, self.coordinator.lock:
            self._available()
            require(_u64(generation, nonzero=True) and generation not in self._records,
                    'Invalid or already reserved save generation')
            require(type(filename) is str and re.fullmatch(r'mp[0-9a-f]{8}\.s14', filename),
                    'Native save filename must be mp + eight lowercase hex digits + .s14')
            require(len(self._records) < 3, 'This retained native owner supports only three saves')
            require(all(r['stage'] == 'PUBLISHED' for r in self._records.values()),
                    'A previous export remains pending or uncertain')
            boundary = self._capture_boundary()
            world = self._observation(observation, boundary)
            if self._records:
                previous = next(reversed(self._records.values()))
                require(generation == previous['request']['generation'] + 1 and
                        all(filename != row['request']['filename'] for row in self._records.values()) and
                        boundary['period'] == previous['boundary']['period'] + 1 and
                        boundary['epoch'] != previous['boundary']['epoch'],
                        'Save generation, filename or period was reused/skipped')
            else:
                require(boundary['period'] == generation == 1, 'Initial save period was skipped')
            q = dict(generation=generation, room_epoch=self._native_room_epoch,
                period=boundary['period'], cut=boundary['cut']['sequence'], room_id=self._native_room_id,
                year=world['node']['year'], month=world['node']['month'], day=world['node']['day'],
                force=world['force'], ruler=world['ruler'], reserved=0, filename=filename)
            descriptor = dict(schema='san14.fresh-save-room-binding.v1', boundary=boundary,
                native_request={**q, 'room_id': q['room_id'].hex()},
                source_kind=self._source_kind, observation=world)
            binding_sha = digest(descriptor)
            self._records[generation] = dict(stage='RESERVED', request=q, boundary=boundary,
                observation=world, descriptor=descriptor, binding_sha256=binding_sha,
                ordinal=len(self._records) + 1, package=None)
            return SaveReservation(generation, binding_sha, MappingProxyType(dict(q)))

    def status(self):
        value = super().status()
        value['remaining_reservations'] = 3 - len(self._records)
        value['capacity'] = 3
        return value
