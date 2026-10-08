"""Bounded CApp parent audit from existing private archives; no live entry.

The native parent runs, but ALL descendants (including the scheduler) are
explicit doubles. This locates a host boundary; it cannot establish a thread
identity, completion, input exclusion or a production save permission.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import struct
import sys
import traceback

import a_save_writer_scope_audit as prior

P = Path(__file__).resolve().parent
CORE_SHA = '36885d10878f9ad5f80a3e8946c8895e020a50130b192c7fc46d20e5d4e56c05'
PDATA_SHA = '74e018f15ec009af5fd0e0d91ce981b82d7d970150b3dce5861f17d11eea2e9f'
ARCHIVE_BASE = 0x7FF749440000
SPAN = (0x13D9C0, 0x13DD03)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_source(raw, pdata):
    rows = [struct.unpack_from('<III', pdata, i) for i in range(0, len(pdata)-11, 12)]
    owner = [r for r in rows if r[0] <= 0x13DC09 < r[1]]
    prior.need(owner == [(SPAN[0], SPAN[1], 0x183CC90)], 'exact parent pdata')
    q = lambda at: struct.unpack_from('<Q', raw, at)[0]
    # MSVC RTTI complete-object locator and vtable, relative to pinned archive.
    prior.need(q(0x1282650) == ARCHIVE_BASE+0x16AD198, 'vtable locator')
    locator = struct.unpack_from('<6I', raw, 0x16AD198)
    prior.need(locator == (1, 0, 0, 0x194F660, 0x16AD1C0, 0x16AD198), 'locator layout')
    prior.need(raw[0x194F670:].split(b'\0', 1)[0] == b'.?AVCApp@@', 'CApp RTTI name')
    prior.need(q(0x1282658+0x10) == ARCHIVE_BASE+SPAN[0], 'CApp virtual +10 target')
    prior.need(raw[0x13DC09] == 0xE8 and
               0x13DC0E+struct.unpack_from('<i', raw, 0x13DC0A)[0] == 0x509FE0,
               'exact native scheduler call')
    return {'case': 'source-and-rtti', 'result': 'PASS', 'class': 'CApp',
            'virtual_slot': 16, 'same_thread_across_frames_proved': False}


def parent_case(raw, mode):
    prior.RANGES['app_parent'] = SPAN  # isolated interpreter; no file mutation
    v = prior.VM(raw)
    v.allow = {'app_parent'}
    b, a = prior.BASE, prior.ARENA
    app, dummy, table = a+0x160000, a+0x161000, a+0x162000
    v.put(dummy, table)
    v.put(app+0x2C8, 1, 4)  # exercise paired parent lock services, still doubles
    v.put(app+0x14, int(mode == 'input-before-scheduler'), 4)
    v.put(app+0xC8+0x20, 1)  # bounded timer branch avoids unneeded division service
    v.put(b+0x13DB8D+7+0x1EDF934, dummy)
    v.put(dummy+0x78, 0)
    v.put(b+0x13DBD7+7+0x18FB352, 0)
    v.put(b+0x13DC14+7+0x18FB315, 0)
    events = []

    def service(name, value=0):
        def run():
            events.append(name)
            v.ret(value)
        return run

    getters = {0xF570, 0xF720, 0xD470, 0xF8D0, 0x1458D0, 0x780EF0}
    for rva in getters:
        v.model(rva, 'singleton double', service('singleton', dummy))
    v.model(0xF690, 'scheduler manager double', service('manager', v.manager))
    v.model(0x83A550, 'timer double', service('timer', 100))
    v.model(0x13C100, 'pre-dispatch decision double',
            service('pre-dispatch-decision', int(mode == 'scheduler-bypassed')))
    v.model(0x509FE0, 'entire scheduler double', service('scheduler'))
    for rva, name in ((0x13900, 'pre-scheduler-13900'), (0x10860, 'pre-scheduler-10860'),
                      (0x3B5560, 'post-scheduler-3B5560'), (0x77F440, 'common-tail-77F440')):
        v.model(rva, name+' business double', service(name))
    for rva in (0xA3C9D0, 0xA3CC50, 0x13EFB0, 0x12E3C0, 0x78EBF0,
                0x338520, 0x337A90, 0x17C8C0, 0x17DF30, 0x77C950,
                0x7879E0, 0x78E5C0, 0x78D610, 0x7B8E60, 0x788B80,
                0x78E8A0, 0x788D90):
        v.model(rva, 'peripheral parent callee double', service('peripheral'))
    for index, (slot, name) in enumerate(((0x123C328, 'parent-lock-enter'),
                                        (0x123C120, 'os-service'),
                                        (0x123CB38, 'post-scheduler-os'),
                                        (0x123C0D8, 'parent-lock-leave'))):
        stub = b+0x2210800+index*0x10
        v.put(b+slot, stub)
        v.handlers[stub] = (name+' double', service(name))
    virtual_stub = b+0x2210900
    v.put(table+0x18, virtual_stub)
    v.handlers[virtual_stub] = ('post scheduler virtual double', service('post-scheduler-virtual'))
    v.run(SPAN[0], (app, dummy, dummy))
    visited = set(v.visits)
    skipped = mode == 'scheduler-bypassed'
    prior.need(events.count('scheduler') == int(not skipped), 'native conditional scheduler dispatch')
    prior.need((0x13DC09 in visited) == (not skipped), 'actual call-site branch')
    prior.need((0x13DC0E in visited) == (not skipped), 'matching actual return site')
    prior.need(0x13DD02 in visited and events[-1] == 'parent-lock-leave', 'normal parent epilogue')
    prior.need(events.count('parent-lock-enter') == events.count('parent-lock-leave') == 1,
               'parent lock service pairing')
    prior.need(events.count('common-tail-77F440') == 1, 'common tail executes after either branch')
    if skipped:
        prior.need('post-scheduler-3B5560' not in events, 'bypass skips scheduler-dependent post work')
    else:
        prior.need(events.index('scheduler') < events.index('post-scheduler-3B5560') <
                   events.index('common-tail-77F440'), 'scheduler return is before parent tail')
    if mode == 'input-before-scheduler':
        prior.need(events.index('pre-scheduler-13900') < events.index('pre-scheduler-10860') <
                   events.index('scheduler'), 'native preprocessing precedes scheduler hook')
    return {'case': mode, 'result': 'PASS', 'native_instruction_count': len(v.visits),
            'events': events, 'scheduler_descendant_is_double': True,
            'actual_os_threads': False, 'production_permit': False}


def main():
    run = P/'a_save_dispatch_parent_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    paths = [Path(__file__), P/'a_save_writer_scope_audit.py']
    pins = {p.name: digest(p) for p in paths}
    result = {'schema': 'san14.a-save-dispatch-parent.v1', 'result': 'FAIL', 'cases': [],
              'source_sha256': pins, 'game_access': False, 'production_permit': False,
              'stable_control_thread_proved': False, 'scheduler_completion_proved': False}
    try:
        private = Path(os.environ['SAN14_PRIVATE_FIXTURE_ROOT']).resolve()
        sys.path.insert(0, str(private/'python_deps'))
        image, pdata = private/'game-runtime-image.bin', private/'runtime-pdata.bin'
        prior.need(pins['a_save_writer_scope_audit.py'] == CORE_SHA, 'frozen VM source')
        prior.need(digest(image) == prior.IMAGE_SHA and digest(pdata) == PDATA_SHA, 'archive identity')
        raw, pd = image.read_bytes(), pdata.read_bytes()
        result['cases'].append(inspect_source(raw, pd))
        for case in ('normal-scheduler', 'scheduler-bypassed', 'input-before-scheduler'):
            result['cases'].append(parent_case(raw, case))
        prior.need({p.name: digest(p) for p in paths} == pins, 'source identity unchanged')
        prior.need(digest(image) == prior.IMAGE_SHA and digest(pdata) == PDATA_SHA, 'archive unchanged')
        result.update(result='PASS', source_unchanged=True, archive_unchanged=True,
                      archive_sha256=prior.IMAGE_SHA, pdata_sha256=PDATA_SHA)
    except Exception as exc:
        result.update(error=repr(exc), traceback=traceback.format_exc())
    (run/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result': result['result'], 'cases': len(result['cases']),
                      'path': str(run/'result.json'), 'error': result.get('error')}))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
