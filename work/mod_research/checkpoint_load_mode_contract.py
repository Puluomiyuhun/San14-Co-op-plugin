"""Pure report/ABI contract for the independent load-menu round trip."""
import ctypes as C
from native_file_identity_start import BridgeStats

MAGIC = 0x53414E144C4D4431


class Slot(C.Structure):
    _fields_ = [(k, C.c_uint64) for k in ('slot', 'original', 'hook', 'observed')]
    _fields_ += [(k, C.c_uint32) for k in ('initialProtection', 'observedProtection', 'restored', 'protectionRestored')]


class Report(C.Structure):
    _fields_ = [('magic', C.c_uint64), ('size', C.c_uint32), ('version', C.c_uint32), ('state', C.c_int32), ('error', C.c_int32)]
    _fields_ += [(k, C.c_uint32) for k in (
        'execute', 'stopRequested', 'exceptionCode', 'callbackFaults',
        'callbackActive', 'userBeforeCalls', 'userAfterCalls', 'menuBeforeCalls', 'menuAfterCalls',
        'installerThread', 'queueThread', 'menuThread', 'returnThread',
        'intentCreated', 'intentFlushed', 'queueCalls', 'queueReturned', 'queueVerified',
        'menuAssociation', 'menuOriginalReturned', 'menuGuardBefore', 'menuGuardAfter',
        'cancelCalls', 'cancelReturned', 'cancelQueueVerified', 'returnSeen', 'returnMatched',
        'initialRng', 'returnedRng', 'initialMode', 'returnedMode',
        'nativeLoadAuthorized', 'customMetadataWrites', 'fullWorldVerified', 'nativeCancellationSeen')]
    _fields_ += [(k, C.c_uint64) for k in ('base', 'user', 'game', 'world', 'cache', 'queuedState',
        'firstUserCallId', 'returnUserCallId', 'menuCallId', 'userCaller', 'menuCaller',
        'userRawRax', 'menuRawRax', 'queueBefore', 'queueAfter', 'cancelBefore', 'cancelAfter')]
    _fields_ += [('userSlot', Slot), ('menuSlot', Slot), ('userBridge', BridgeStats), ('menuBridge', BridgeStats), ('stage', C.c_char * 64)]


def decode(raw):
    if len(raw) != C.sizeof(Report):
        raise ValueError('report_size')
    report = Report.from_buffer_copy(raw)
    if report.magic != MAGIC or report.size != C.sizeof(Report) or report.version != 1:
        raise ValueError('report_header')
    value = {k: getattr(report, k) for k, _ in Report._fields_}
    for name in ('userSlot', 'menuSlot', 'userBridge', 'menuBridge'):
        item = getattr(report, name)
        value[name] = {k: getattr(item, k) for k, _ in item._fields_}
    value['stage'] = report.stage.decode('ascii')
    return value


def drained(r):
    return r['callbackActive'] == r['userBridge']['active'] == r['menuBridge']['active'] == 0


def report_ok(r, execute, before):
    base = int(before['base'], 0)
    expected = {'state': 7 if execute else 3, 'execute': int(execute),
        'error': 0, 'stopRequested': 0, 'exceptionCode': 0, 'callbackFaults': 0,
        'nativeLoadAuthorized': 0, 'customMetadataWrites': 0, 'fullWorldVerified': 0, 'nativeCancellationSeen': 0,
        'base': base, 'user': int(before['pinned_user'], 0), 'game': int(before['pinned_game'], 0),
        'world': int(before['pinned_world'], 0), 'cache': int(before['cache_graph']['cache'], 0),
        'initialRng': before['global_rng'], 'initialMode': before['cache_mode'], 'userCaller': base + 0x50B785}
    if any(r.get(k) != v for k, v in expected.items()) or not drained(r):
        return False
    for name, slot_rva, original_rva in [('userSlot', 0x12CC4A8 + 0x28, 0x3F9B00)] + ([('menuSlot', 0x12DB4C0 + 0x28, 0x4AA200)] if execute else []):
        s = r[name]
        source = before['mode_hook_pages']['user' if name == 'userSlot' else 'load_update']
        if s['slot'] != base + slot_rva or s['original'] != base + original_rva or s['observed'] != s['original']:
            return False
        if s['restored'] != 1 or s['protectionRestored'] != 1 or s['initialProtection'] != source['protect'] or s['observedProtection'] != source['protect']:
            return False
    for name, before_name, after_name in [('userBridge', 'userBeforeCalls', 'userAfterCalls'), ('menuBridge', 'menuBeforeCalls', 'menuAfterCalls')]:
        b = r[name]
        if not (b['started'] == b['native_started'] == b['native_returned'] == b['before_calls'] == b['after_calls'] == r[before_name] == r[after_name]):
            return False
        if b['abnormal_exits'] != 0:
            return False
    if r['userBridge']['configured'] != 1 or r['userBridge']['module_pinned'] != 1 or r['firstUserCallId'] == 0 or r['installerThread'] == 0:
        return False
    if not execute:
        return (r['userBridge']['started'] == 1 and r['menuBridge']['started'] == 0 and
                all(r[k] == 0 for k in ('intentCreated', 'intentFlushed', 'queueCalls', 'queueReturned', 'queueVerified',
                    'cancelCalls', 'cancelReturned', 'returnSeen', 'queuedState', 'menuAssociation', 'menuOriginalReturned')))
    required_one = ('intentCreated', 'intentFlushed', 'queueCalls', 'queueReturned', 'queueVerified', 'menuAssociation',
        'menuOriginalReturned', 'menuGuardBefore', 'menuGuardAfter', 'cancelCalls', 'cancelReturned',
        'cancelQueueVerified', 'returnSeen', 'returnMatched')
    return (all(r[k] == 1 for k in required_one) and r['menuBridge']['started'] == 1 and
        r['userBridge']['started'] >= 2 and r['menuBridge']['configured'] == r['menuBridge']['module_pinned'] == 1 and
        r['queueBefore'] == r['cancelBefore'] == 0 and r['queueAfter'] == r['cancelAfter'] == 1 and
        r['returnedMode'] == 0 and r['returnedRng'] == before['global_rng'] and
        all(r[k] > 0 for k in ('queueThread', 'menuThread', 'returnThread')) and
        r['menuCaller'] == base + 0x50B785 and r['queuedState'] != 0 and
        r['returnUserCallId'] > r['firstUserCallId'] and r['menuCallId'] != 0)


if __name__ == '__main__':
    print({'report_bytes': C.sizeof(Report), 'slot_bytes': C.sizeof(Slot), 'game_access': False})
