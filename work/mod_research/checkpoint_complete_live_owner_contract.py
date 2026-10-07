"""Stable data-only ABI. No process access, installation or success authorization."""
import ctypes as C
import struct

MAGIC = 0x53414E14434F5631
VERSION = 1
U8, U32, U64 = C.c_uint8, C.c_uint32, C.c_uint64
VALUE_NAMES = tuple("""OwnerState OwnerError OwnerException OsError InstallCalls InstallIntentCreated InstallIntentDurable ModulePinned Installed StopRequested RestoreCalls RestoreReturned SessionState SessionError SessionException Armed MenuBound RequestInFlight RequestSettled CasPublished MayHavePublished HooksRestored ActiveDispatch ActiveWorker ActiveRead UserControllerCalls DispatchUnpaired QueueStage QueueError QueueNativeCalls QueueNativeReturned QueueVerified QueueResolverCalls QueueAuthorized QueueStopped QueueMayHaveQueued ControllerError ControllerBlocked ControllerActive ControllerStopped ControllerFinished ControllerOriginalCalls ControllerAbnormal ControllerQueueCalls ControllerQueueReturned ControllerAuthorizeCalls ControllerAuthorized ControllerCommit ControllerBind ControllerClosed RequestState RequestMenuCalls RequestGameCalls RequestReadAttempts RequestCasAttempts RequestCasApplied RequestIntentCreated RequestIntentDurable RequestPostGuard RequestOsError RequestException RequestObservedPending BytesError BytesWorkerBefore BytesWorkerAfter BytesWorkerFinally BytesWorkerAbnormal BytesReadBefore BytesReadAfter BytesReadFinally BytesReadAbnormal BytesMatched BytesWorkerReturned BytesObserved BytesActiveWorker BytesActiveRead LifecycleError LifecycleBound LifecycleInFlight LifecycleJoinReturned LifecycleRequestCleared LifecycleSuccessFlag LifecycleExactPop LifecycleFrozen LifecycleReady IdentityError IdentityActive IdentityAbnormal IdentityCommitCalls IdentityCasAttempts IdentityCasApplied IdentityIntentCreated IdentityIntentDurable IdentityNativeReturned IdentityObserved IdentityReady PlanningError PlanningException PlanningBefore PlanningAfter PlanningInFlight PlanningWaiting PlanningReceiptBound PlanningStack PlanningIdentity PlanningRequestCleared PlanningUi PlanningNativeReturned PlanningObserved PlanningUserReused PlanningUiForceMatches PlanningSessionError PlanningSessionStop HardwareError HardwareEntered HardwareCaptured HardwareRestored HardwareFinished HardwareRestoreUncertain StorageError StorageValidations StorageOpened StorageInvalidated GuardError GuardChecks GuardException InputExclusionProven FullWorldVerified PixelPresentationProven ReadyAuthorized""".split())
assert len(VALUE_NAMES) == 130

class ModuleApproval(C.Structure):
    _fields_ = [("base", U64), ("sizeOfImage", U32), ("timestamp", U32),
                ("path", C.c_wchar * 1024), ("fileSize", U64),
                ("fileSha256", U8 * 32), ("headerSha256", U8 * 32)]

class Endpoint(C.Structure):
    _fields_ = [("address", U64), ("moduleIndex", U32), ("first32", U8 * 32)]

class Config(C.Structure):
    _fields_ = [("magic", U64), ("size", U32), ("version", U32), ("pid", U32), ("reserved", U32)]
    _fields_ += [(n, U64) for n in ("birth", "base", "attempt", "epoch", "generation")]
    _fields_ += [(n, U8 * 32) for n in ("attachment", "ownerBinding", "nonce", "gameSha256")]
    _fields_ += [("states", U64 * 5)]
    _fields_ += [(n, U64) for n in ("root", "world", "cache", "keyboard", "toolbar", "panel", "stack", "stackCapacity", "queue", "queueCapacity")]
    _fields_ += [(n, U32) for n in ("rng", "expectedMode", "helperDeadlineMs", "reserved2")]
    _fields_ += [(n, C.c_wchar * 512) for n in ("localPath", "installIntent", "requestIntent", "identityIntent")]
    _fields_ += [("storageModules", ModuleApproval * 3)]
    _fields_ += [(n, U32) for n in ("storageModuleCount", "vtableModuleIndex", "counterModuleIndex", "reserved3")]
    _fields_ += [(n, Endpoint) for n in ("contextInit", "exists", "fileSize", "read", "ownedReadBridge")]
    _fields_ += [(n, U64) for n in ("storage", "storageVtable", "storageCounter", "cachedGeneration")]
    _fields_ += [("contextCode", U8 * 0x65)]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.magic, self.size, self.version = MAGIC, C.sizeof(type(self)), VERSION
        self.helperDeadlineMs = 1000

class HookReceipt(C.Structure):
    _fields_ = [(n, U64) for n in ("slot", "original", "hook", "observed")]
    _fields_ += [(n, U32) for n in ("protection", "lastProtection", "error", "known", "dirty", "published", "restored", "reserved")]

class BridgeReceipt(C.Structure):
    _fields_ = [(n, U64) for n in ("started", "returned", "abnormal", "beforeFaults", "afterFaults", "cleanupFaults")]

class Report(C.Structure):
    _fields_ = [("magic", U64), ("size", U32), ("version", U32)]
    _fields_ += [(n, U64) for n in ("sequence", "attempt", "epoch")]
    _fields_ += [("value", U64 * len(VALUE_NAMES)), ("hooks", HookReceipt * 6), ("bridges", BridgeReceipt * 6)]
    _fields_ += [("bytesReceipt", U8 * 288), ("lifecycleReceipt", U8 * 488), ("identityReceipt", U8 * 344), ("hardwareReceipt", U8 * 696), ("requestReadSha", U8 * 32)]
    _fields_ += [(n, U64) for n in ("planningAttempt", "planningEpoch", "planningUserCall", "planningIdentityCall", "planningCompletedCall", "planningUser")]
    _fields_ += [("planningBeforeSample", U8 * 128), ("planningAfterSample", U8 * 128), ("requestStage", C.c_char * 64), ("planningFailure", C.c_char * 64)]

class Description(C.Structure):
    _fields_ = [("magic", U64), ("size", U32), ("version", U32), ("configSize", U32), ("reportSize", U32), ("valueCount", U32), ("reserved", U32), ("module", U64), ("dispatchBridge", U64 * 4), ("workerBridge", U64), ("readBridge", U64), ("authorizedForward", U64)]

class BytesReceipt(C.Structure):
    _fields_ = [('version',U32),('size',U32),('error',C.c_int32),('exceptionCode',U32)]
    _fields_ += [(n,U64) for n in 'token load title worker callable workerCall readCall workerCaller readCaller parentCaller buffer workerRax readRax'.split()]
    _fields_ += [(n,U32) for n in 'workerThread readThread requested returned nativeResult workerBefore workerAfter workerFinally workerAbnormal readBefore readAfter readFinally readAbnormal otherWorkers titleWorkers unownedReads ownedReadCandidates activeWorker activeRead bytesMatched workerReturned observedWorkerAndBytes stopped loadAuthorized joined planningReady'.split()]
    _fields_ += [('sha256',U8*32),('workerXmm0',U8*16),('readXmm0',U8*16)]

class LifecycleReceipt(C.Structure):
    _fields_ = [('version',U32),('size',U32),('error',C.c_int32),('exceptionCode',U32)]
    _fields_ += [(n,U64) for n in 'token load title completionClosure worker boundCall joinedCall completedCall lastCall lastRax'.split()]
    _fields_ += [(n,U32) for n in 'lastThread phaseBefore phaseAfter phaseMask beforeCalls afterCalls otherUpdates inFlight bound workerStarted joinReturned requestCleared successFlag nativeResult exactPop completionFrozen receiptReady stopped directFinalizerObserved planningReady loadAuthorized reserved'.split()]
    _fields_ += [('lastXmm0',U8*16),('frozenBytes',BytesReceipt)]

class Pair(C.Structure):
    _fields_=[('force',U64),('person',U64)]

class IdentityReceipt(C.Structure):
    _fields_ = [('version',U32),('size',U32),('error',C.c_int32),('exceptionCode',U32)]
    _fields_ += [(n,U64) for n in 'token title historicalLoad completionCall callable workerCall caller root world originalRax'.split()]
    _fields_ += [(n,Pair) for n in ('source','target','observedPair')]
    _fields_ += [(n,U32) for n in 'thread phaseBefore phaseAfter stackBefore stackAfter beforeCalls afterCalls finallyCalls otherWorkers active abnormal stopped commitState commitCalls casAttempts casApplied intentCreated intentDurable postGuard commitReturned commitException commitOsError nativeReturned worldForceAfter worldControlAfter identityObserved receiptReady initializerCallsDirectlyObserved planningReady fullWorldVerified'.split()]
    _fields_ += [('originalXmm0',U8*16),('commitStage',C.c_char*64)]

assert C.sizeof(BytesReceipt)==288 and C.sizeof(LifecycleReceipt)==488 and C.sizeof(IdentityReceipt)==344

def pod_dict(obj):
    result={}
    for name,typ in obj._fields_:
        value=getattr(obj,name)
        if isinstance(value,C.Structure):value=pod_dict(value)
        elif isinstance(value,C.Array):value=bytes(value).hex() if typ._type_==U8 else list(value)
        elif isinstance(value,bytes):value=value.decode('ascii','strict')
        result[name]=value
    return result

def receipt(typ,raw):
    if not any(raw):return None
    obj=typ.from_buffer_copy(raw)
    if hasattr(obj,'version') and (obj.version,obj.size)!=(1,C.sizeof(typ)):
        raise ValueError('nested receipt ABI')
    return pod_dict(obj)

CONFIG_SIZE, REPORT_SIZE, DESCRIPTION_SIZE = 11224, 4032, 96
assert C.sizeof(ModuleApproval) == 2136 and C.sizeof(Endpoint) == 48
assert C.sizeof(Config) == CONFIG_SIZE and C.sizeof(Report) == REPORT_SIZE and C.sizeof(Description) == DESCRIPTION_SIZE

def _fields(obj):
    return {n: int(getattr(obj, n)) for n, _ in obj._fields_}

def _sample(raw):
    words = struct.unpack_from("<15QI", raw)
    keys = ("stack", "root", "world", "force", "ruler", "district", "cache", "worker", "toolbar", "panel", "uiForceContext")
    return {"states": list(words[:5]), **dict(zip(keys, words[5:]))}

def decode_description(raw):
    if len(raw) != DESCRIPTION_SIZE:
        raise ValueError("description size")
    d = Description.from_buffer_copy(raw)
    if d.reserved or (d.magic, d.size, d.version, d.configSize, d.reportSize, d.valueCount) != (MAGIC, DESCRIPTION_SIZE, VERSION, CONFIG_SIZE, REPORT_SIZE, len(VALUE_NAMES)):
        raise ValueError("description ABI")
    return {"module": d.module, "dispatchBridge": list(d.dispatchBridge), "workerBridge": d.workerBridge, "readBridge": d.readBridge, "authorizedForward": d.authorizedForward}

def decode_report(raw):
    if len(raw) != REPORT_SIZE:
        raise ValueError("report size")
    r = Report.from_buffer_copy(raw)
    if (r.magic, r.size, r.version) != (MAGIC, REPORT_SIZE, VERSION):
        raise ValueError("report ABI")
    result = dict(zip(VALUE_NAMES, map(int, r.value)))
    result.update(sequence=r.sequence, attempt=r.attempt, epoch=r.epoch,
                  hooks=[_fields(x) for x in r.hooks], bridges=[_fields(x) for x in r.bridges],
                  requestReadSha=bytes(r.requestReadSha).hex(), requestStage=r.requestStage.decode("ascii", "replace"),
                  planningFailure=r.planningFailure.decode("ascii", "replace"),
                  planningAttempt=r.planningAttempt, planningEpoch=r.planningEpoch, planningUserCall=r.planningUserCall,
                  planningIdentityCall=r.planningIdentityCall, planningCompletedCall=r.planningCompletedCall, planningUser=r.planningUser,
                  planningBeforeSample=_sample(bytes(r.planningBeforeSample)), planningAfterSample=_sample(bytes(r.planningAfterSample)))
    result["receipts"] = {n: bytes(getattr(r, n)).hex() for n in ("bytesReceipt", "lifecycleReceipt", "identityReceipt", "hardwareReceipt")}
    from checkpoint_live_prefetch_contract import HardwareReceipt
    for key,typ,field in (('bytes',BytesReceipt,'bytesReceipt'),('lifecycle',LifecycleReceipt,'lifecycleReceipt'),
            ('identity',IdentityReceipt,'identityReceipt'),('hardware',HardwareReceipt,'hardwareReceipt')):
        result[key]=receipt(typ,bytes(getattr(r,field)))
    result["retained_hooks"] = any(x["published"] and not x["restored"] for x in result["hooks"])
    return result
