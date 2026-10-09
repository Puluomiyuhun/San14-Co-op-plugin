"""Warm profile-aware production completion classifier; data only, never a next-bank permit."""
from __future__ import annotations
import ctypes as C
import hashlib
import json
import re
from checkpoint_complete_live_owner_contract import BytesReceipt, LifecycleReceipt, IdentityReceipt, receipt
from checkpoint_live_prefetch_contract import HardwareReceipt

import b_warm_profile_contract as warm
GAME_SHA = "42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025"
CLASSIFICATION = "PASS_WARM_LOAD_RETIRED"
SLOTS = (0x12CC4D0, 0x12DB4E8, 0x12CC9E0, 0x12DBD90, 0x138E8D0)
ORIGINALS = (0x3F9B00, 0x4AA200, 0x3F8140, 0x4A85C0, 0x4FABC0)

def require(value, message):
    if not value:
        raise ValueError(message)

def integer(value, label, minimum=0):
    require(type(value) is int and minimum <= value < 2**64, label + " must be an exact bounded integer")
    return value

def exact(row, fields, value, prefix):
    for key in fields.split():
        require(integer(row[key], prefix + key) == value, prefix + key + " differs")

def positive(row, fields, prefix):
    for key in fields.split():
        integer(row[key], prefix + key, 1)

def module_contains(modules, address, size=1):
    integer(address, "module address", 1)
    found = [m for m in modules if integer(m["base"], "module base", 1) <= address
             and address + size <= m["base"] + integer(m["sizeOfImage"], "module size", 1)]
    require(len(found) == 1, "address has no unique supplied module owner")
    return found[0]

def _validate_bytes(b, base, attempt, profile):
    exact(b, "version", 1, "bytes.")
    exact(b, "size", 288, "bytes.")
    exact(b, "error exceptionCode workerAbnormal readAbnormal activeWorker activeRead stopped loadAuthorized joined planningReady", 0, "bytes.")
    exact(b, "workerBefore workerAfter workerFinally readBefore readAfter readFinally bytesMatched workerReturned observedWorkerAndBytes ownedReadCandidates nativeResult", 1, "bytes.")
    require(b["token"] == attempt, "bytes attempt differs")
    positive(b, "load title worker callable workerCall readCall buffer workerThread readThread", "bytes.")
    require(b["worker"] == b["load"] + 0x478 and b["workerThread"] == b["readThread"], "bytes native worker identity differs")
    require((b["workerCaller"], b["readCaller"], b["parentCaller"]) ==
            (base + 0x834D9B, base + 0x3A9227, base + 0x2F77CF), "bytes native caller path differs")
    require(b["requested"] == b["returned"] == profile.file.size and b["readRax"] & 0xFFFFFFFF == profile.file.size,
            "bytes actual request/read size differs")
    require(b["sha256"] == bytes(profile.file.sha256).hex(), "bytes actual buffer SHA differs")

def _validate_report(r, *, base, attempt, epoch, generation, attachment_hex, description, planning, storage, profile, profile_report, retire_report):
    for label, value in (("base", base), ("attempt", attempt), ("epoch", epoch), ("generation", generation)):
        integer(value, label, 1)
    require(type(attachment_hex) is str and re.fullmatch("[0-9a-f]{64}", attachment_hex)
            and any(bytes.fromhex(attachment_hex[:32])) and any(bytes.fromhex(attachment_hex[32:])), "attachment token shape")
    require(type(r) is dict and type(description) is dict and type(planning) is dict and type(storage) is dict, "report/config dict required")
    require((r["attempt"], r["epoch"], r["planningAttempt"], r["planningEpoch"]) == (attempt, epoch, attempt, epoch), "owner/planning attempt or epoch differs")
    integer(r["sequence"], "sequence", 1)
    require(planning["base"] == base and planning["gameSha256"] == GAME_SHA, "captured game profile differs")
    warm.validate_profile(profile)
    observed_profile = warm.decode(warm.Report, bytes(profile_report))
    retired = warm.decode(warm.RetireReport, bytes(retire_report))
    require(observed_profile.ready and bytes(observed_profile.profile) == bytes(profile), "captured immutable profile differs")
    require(retired.sealed and retired.restored and not retired.restoreFailed, "bank not fully retired")
    require((retired.attempt, retired.userCall, retired.identityCall, retired.loadCall) ==
            (attempt, r["planningUserCall"], r["planningIdentityCall"], r["planningCompletedCall"]), "retirement completion binding differs")
    snap = planning["context"]["snapshot"]
    require(tuple(snap["date"][k] for k in ("year", "month", "day")) ==
            (profile.before.year, profile.before.month, profile.before.day) and
            snap["player"]["force_id"] == profile.currentForce, "captured current date/player differs")
    require(planning["profileSha256"] == hashlib.sha256(bytes(profile)).hexdigest(), "planning belongs to another profile")
    require(len(planning["states"]) == 5 and len(set(planning["states"])) == 5, "initial states differ")
    for state in planning["states"]: integer(state, "initial state", 1)
    require(planning["queue"] == planning["queueCapacity"] == planning["expectedMode"] == 0, "initial empty queue/mode profile differs")

    exact(r, "OwnerState", 2, "owner.")
    exact(r, "SessionState", 13, "owner.")
    exact(r, "RequestState", 6, "owner.")
    exact(r, "QueueStage", 5, "owner.")
    exact(r, "OwnerError OwnerException OsError StopRequested RestoreCalls RestoreReturned SessionError SessionException RequestInFlight ActiveDispatch ActiveWorker ActiveRead DispatchUnpaired QueueError QueueStopped ControllerError ControllerBlocked ControllerActive ControllerStopped ControllerAbnormal RequestOsError RequestException BytesError BytesWorkerAbnormal BytesReadAbnormal BytesActiveWorker BytesActiveRead LifecycleError LifecycleInFlight IdentityError IdentityActive IdentityAbnormal PlanningError PlanningException PlanningInFlight PlanningSessionError PlanningSessionStop HardwareError HardwareRestoreUncertain StorageError StorageInvalidated GuardError GuardException InputExclusionProven FullWorldVerified PixelPresentationProven ReadyAuthorized", 0, "owner.")
    exact(r, "InstallCalls InstallIntentCreated InstallIntentDurable ModulePinned Installed Armed HooksRestored MenuBound RequestSettled CasPublished MayHavePublished UserControllerCalls QueueNativeCalls QueueNativeReturned QueueVerified QueueResolverCalls QueueAuthorized QueueMayHaveQueued ControllerFinished ControllerQueueCalls ControllerQueueReturned ControllerAuthorizeCalls ControllerAuthorized ControllerCommit ControllerBind ControllerClosed RequestMenuCalls RequestGameCalls RequestReadAttempts RequestCasAttempts RequestCasApplied RequestIntentCreated RequestIntentDurable RequestPostGuard BytesWorkerBefore BytesWorkerAfter BytesWorkerFinally BytesReadBefore BytesReadAfter BytesReadFinally BytesMatched BytesWorkerReturned BytesObserved LifecycleBound LifecycleJoinReturned LifecycleRequestCleared LifecycleExactPop LifecycleFrozen LifecycleReady IdentityCommitCalls IdentityCasAttempts IdentityCasApplied IdentityIntentCreated IdentityIntentDurable IdentityNativeReturned IdentityObserved IdentityReady PlanningBefore PlanningAfter PlanningReceiptBound PlanningStack PlanningIdentity PlanningRequestCleared PlanningUi PlanningNativeReturned PlanningObserved HardwareEntered HardwareCaptured HardwareRestored HardwareFinished StorageOpened", 1, "owner.")
    # Includes transparent calls for the new User and subsequent ordinary frames.
    integer(r["ControllerOriginalCalls"], "ControllerOriginalCalls", 1)
    require(r["LifecycleSuccessFlag"] == 0x7FFFFFFD and r["RequestObservedPending"] == 2**64 - 1, "request CAS source or lifecycle success differs")
    require(integer(r["GuardChecks"], "GuardChecks", 29) >= 29 and integer(r["StorageValidations"], "StorageValidations", 1), "validators were not used")
    require(r["planningFailure"] == "none" and r["requestStage"] == "pending_committed_native_original_not_yet_called", "failed or unexpected request/planning stage")
    require(r["requestReadSha"] == bytes(profile.file.sha256).hex(), "complete native precommit read SHA differs")

    modules = storage["storageModules"]
    require(storage["storageModuleCount"] == 3 and len(modules) == 3, "production storage module list required")
    owner_module = description["module"]
    owner = module_contains(modules, owner_module)
    require(owner["base"] == owner_module, "owner module binding differs")
    bridges = description["dispatchBridge"] + [description["workerBridge"], description["readBridge"]]
    require(len(bridges) == 6 and len(set(bridges + [description["authorizedForward"]])) == 7, "bridge description is not unique")
    for address in bridges + [description["authorizedForward"]]:
        require(module_contains(modules, address, 32) == owner, "bridge outside supplied owner module")
    require(storage["ownedReadBridge"]["address"] == description["readBridge"], "storage bridge differs")
    read_address = storage["read"]["address"]
    require(module_contains(modules, read_address, 32) == modules[storage["read"]["moduleIndex"]], "storage native read owner differs")
    expected_slots = [base + n for n in SLOTS] + [storage["storageVtable"] + 8]
    expected_originals = [base + n for n in ORIGINALS] + [read_address]
    require(len(r["hooks"]) == len(r["bridges"]) == 6 and r["retained_hooks"] is False, "six restored bridge reports required")
    for n, (h, bridge) in enumerate(zip(r["hooks"], r["bridges"])):
        require((h["slot"], h["original"], h["hook"], h["observed"]) ==
                (expected_slots[n], expected_originals[n], bridges[n], expected_originals[n]), "hook binding differs: " + str(n))
        exact(h, "error dirty published reserved", 0, "hook.")
        exact(h, "known restored", 1, "hook.")
        require(h["protection"] in (2, 4, 8) and h["lastProtection"] == h["protection"], "hook page protection differs")
        exact(bridge, "abnormal beforeFaults afterFaults cleanupFaults", 0, "bridge.")
        require(integer(bridge["started"], "bridge.started", 1) == integer(bridge["returned"], "bridge.returned", 1), "native bridge is not balanced")

    for key, typ, raw_name in (("bytes", BytesReceipt, "bytesReceipt"), ("lifecycle", LifecycleReceipt, "lifecycleReceipt"),
                              ("identity", IdentityReceipt, "identityReceipt"), ("hardware", HardwareReceipt, "hardwareReceipt")):
        raw = bytes.fromhex(r["receipts"][raw_name])
        require(len(raw) == C.sizeof(typ), "nested POD exact length differs: " + key)
        require(receipt(typ, raw) == r[key], "decoded receipt and raw POD differ: " + key)
    b, l, i, h = (r[k] for k in ("bytes", "lifecycle", "identity", "hardware"))
    _validate_bytes(b, base, attempt, profile)
    _validate_bytes(l["frozenBytes"], base, attempt, profile)
    # Other-worker counters can grow after the frozen load receipt. Compare the
    # actual bound byte-read identity/result instead of requiring raw equality.
    byte_keys = "token load title worker callable workerCall readCall workerThread readThread workerCaller readCaller parentCaller buffer requested returned readRax sha256".split()
    require(all(l["frozenBytes"][k] == b[k] for k in byte_keys), "frozen lifecycle byte evidence differs")
    exact(l, "error exceptionCode inFlight stopped directFinalizerObserved planningReady loadAuthorized reserved", 0, "lifecycle.")
    exact(l, "bound workerStarted joinReturned requestCleared nativeResult exactPop completionFrozen receiptReady", 1, "lifecycle.")
    require((l["token"], l["load"], l["title"], l["worker"]) == (attempt, b["load"], b["title"], b["worker"]), "lifecycle object binding differs")
    positive(l, "completionClosure boundCall joinedCall completedCall lastCall lastThread beforeCalls", "lifecycle.")
    require(l["boundCall"] < l["joinedCall"] < l["completedCall"] == l["lastCall"] and l["beforeCalls"] == l["afterCalls"], "native completion/join chronology differs")
    require(l["completedCall"] <= r["bridges"][3]["started"], "Load completion call exceeds its native bridge sequence")
    require(b["readCall"] <= r["bridges"][5]["started"], "byte read call exceeds its native bridge sequence")
    require(l["phaseBefore"] == l["phaseAfter"] == 4 and l["phaseMask"] == 30 and l["successFlag"] == 0x7FFFFFFD, "native Load phase completion differs")

    exact(i, "error exceptionCode active abnormal stopped commitException commitOsError initializerCallsDirectlyObserved planningReady fullWorldVerified", 0, "identity.")
    exact(i, "beforeCalls afterCalls finallyCalls commitCalls casAttempts casApplied intentCreated intentDurable postGuard commitReturned nativeReturned identityObserved receiptReady", 1, "identity.")
    exact(i, "commitState", 4, "identity.")
    require((i["token"], i["historicalLoad"], i["title"], i["completionCall"]) == (attempt, l["load"], l["title"], l["completedCall"]), "identity completion binding differs")
    positive(i, "root world callable workerCall thread", "identity.")
    require(i["caller"] == base + 0x834D9B and b["workerCall"] < i["workerCall"] <= r["bridges"][4]["started"],
            "identity native worker path or same-bridge sequence differs")
    for pair in (i["source"], i["target"], i["observedPair"]): positive(pair, "force person", "identity.pair.")
    require(i["source"]["force"] != i["target"]["force"] and i["source"]["person"] != i["target"]["person"]
            and i["observedPair"] == i["target"] and i["commitStage"] == "pair_committed_initializer_not_called",
            "identity commit did not observe the target pair after its source CAS")
    # source/target Pair fields are object pointers, not numeric profile IDs.
    # Native identity guards resolve those tables; the launcher separately reads
    # the final ruler/force IDs after retirement.
    require((i["worldForceAfter"], i["worldControlAfter"]) == (profile.target.force, 1), "native initializer did not establish target view")
    for phase_key, stack_key in (("phaseBefore", "stackBefore"), ("phaseAfter", "stackAfter")):
        require(i[phase_key] in (13, 15) and i[stack_key] in (3, 4) and (i[stack_key] != 3 or i[phase_key] == 15), "identity Title lifecycle differs")

    require(r["planningIdentityCall"] == i["workerCall"] and r["planningCompletedCall"] == l["completedCall"], "planning used another upstream receipt")
    integer(r["planningUserCall"], "planningUserCall", 1)
    before, after = r["planningBeforeSample"], r["planningAfterSample"]
    # uiForceContext is multi-writer presentation telemetry, not player identity.
    compare_keys = "states stack root world force ruler district cache worker toolbar panel".split()
    require(all(before[k] == after[k] for k in compare_keys), "planning objects changed during original User call")
    require(len(after["states"]) == len(set(after["states"])) == 5 and after["states"][:2] == planning["states"][:2]
            and after["states"][4] == r["planningUser"], "new planning state chain differs")
    # V2 native observer verifies current formal RTTI/vtable and lifecycle.
    # The allocator may reuse retired Load/Title addresses for new formal objects.
    # Address equality alone cannot identify a previous object lifetime.
    for key in compare_keys[1:]: integer(after[key], "planning." + key, 1)
    require((after["root"], after["world"], after["force"], after["ruler"]) ==
            (i["root"], i["world"], i["target"]["force"], i["target"]["person"]), "planning target force/ruler pointers differ")
    require(r["PlanningUserReused"] == int(r["planningUser"] == planning["states"][4]) and
            r["PlanningUiForceMatches"] == int(after["uiForceContext"] == profile.target.force), "planning diagnostic summary differs")

    exact(h, "capture_kind entered captured restored finished module_pinned observer_calls", 1, "hardware.")
    exact(h, "error os_error exception_code helper_deadline_exceeded restore_uncertain", 0, "hardware.")
    positive(h, "thread call_id", "hardware.")
    require(h["call_id"] < r["planningUserCall"] <= r["bridges"][0]["started"],
            "planning User call does not follow admitted User call within its bridge sequence")
    require(h["site_rip"] == base + 0x3F9DAF and h["user"] == planning["states"][4] and
            len(h["gpr"]) == 16 and h["gpr"][6] == h["user"] and integer(h["gpr"][4], "hardware rsp", 1) % 16 == 0, "hardware User/site/register binding differs")
    require(h["binding"] == dict(attempt=attachment_hex[:32], attachment=attachment_hex[32:], owner_generation=generation), "hardware exact binding differs")
    require(len(h["original_dr"]) == len(h["restored_dr"]) == 6 and h["original_dr"] == h["restored_dr"]
            and h["original_code_unchanged"] is True and h["queue_authorized"] is False and h["full_input_hold"] is False, "hardware restoration or permission differs")
    p = h["pending"]
    exact(p, "error game_transition load_queued advance panel_advance queue_count", 0, "prefetch.pending.")
    require(p["decision"] == 1 and p["stage"] == 2 and p["call_id"] == h["call_id"] and p["menu_command"] == -1 and
            p["user_phase"] == 2 and p["stack_count"] == 5 and p["read_only"] is True and p["pending_admission_candidate"] is True,
            "hardware captured pending state was not clean")
    require(p["native_hook_installed"] is False and p["all_pending_sources_covered"] is False and p["full_input_hold"] is False,
            "prefetch pending receipt claims unsupported exclusion")

    stable = dict(profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(), retirement=bytes(retired).hex(), base=base, attempt=attempt, epoch=epoch, generation=generation, attachment=attachment_hex,
                  hooks=[(x["slot"], x["original"], x["hook"], x["protection"]) for x in r["hooks"]],
                  bytes={k:b[k] for k in byte_keys},
                  lifecycle={k:l[k] for k in "token load title completionClosure boundCall joinedCall completedCall".split()},
                  identity={k:i[k] for k in "token title historicalLoad completionCall callable workerCall thread root world source target".split()},
                  planning={k:after[k] for k in compare_keys}, planning_user_call=r["planningUserCall"],
                  hardware={k:h[k] for k in "thread call_id site_rip user binding original_dr restored_dr".split()})
    key = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return dict(result=CLASSIFICATION, receipt_key=key, source_force=profile.source.force, source_ruler=profile.source.ruler,
                target_force=profile.target.force, target_ruler=profile.target.ruler, ready_authorized=False, full_world_verified=False,
                input_exclusion_proven=False, pixel_presentation_proven=False, scheduler_fence_proven=False,
                post_cas_detach_allowed=False, automatic_retry_allowed=False)

def validate_report(report, *, base, attempt, epoch, generation, attachment_hex, description, planning, storage, profile, profile_report, retire_report):
    """Return a stable frozen-evidence key, or raise ValueError on any deficit.

    Caller must compare two separately captured samples and separately verify
    the approved DLL/config/process identity. The key deliberately excludes
    sequence, ongoing balanced bridge counts and incidental UI telemetry.
    """
    try:
        return _validate_report(report, base=base, attempt=attempt, epoch=epoch, generation=generation,
                                attachment_hex=attachment_hex, description=description, planning=planning, storage=storage, profile=profile,
                                profile_report=profile_report, retire_report=retire_report)
    except (KeyError, TypeError, IndexError, OverflowError) as exc:
        raise ValueError("incomplete or malformed native receipt: " + str(exc)) from exc
