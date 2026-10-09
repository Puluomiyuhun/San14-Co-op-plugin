"""Bounded read-only retries of one exact two-sample planning mismatch.

No Install, FileWrite, native call, process discovery, once reset or old-address
reuse. The original full sampler must succeed anew; task/current fields are not
removed from its comparison. A timeout cannot interrupt an in-flight OS read.
"""
import hashlib
import math
import time

import b_warm_profile_capture as original

RETRYABLE = 'Attachment/planning changed during capture'


def capture_planning(reader,profile,expected_ruler,*,expected_birth,expected_pid=None,
                     max_attempts=3,timeout=0.75,interval=0.02,evidence=None,birth_reader=None):
    """Return an unchanged original sample; retain every refusal in evidence.

    expected_birth must come from the current retained process owner. Callers
    must not acquire it afresh after a rejected incarnation. Optional birth_reader
    supports offline tests, as in the predecessor; real callers omit it.
    """
    original.integer(expected_birth,1,2**64-1)
    original.integer(max_attempts,1,5)
    for value,lo,hi in ((timeout,0.001,2.0),(interval,0,0.1)):
        original.require(type(value) in (int,float) and math.isfinite(value) and lo<=value<=hi,'Bounded sampling timing required')
    original.integer(expected_ruler,1,5999)
    pid=reader.pid if expected_pid is None else expected_pid
    original.integer(pid,1,0xffffffff)
    profile_bytes=bytes(original.abi.validate_profile(profile))
    base=reader.memory.base
    original.require(reader.sha256==original.GAME_SHA,'Unsupported game image')
    if birth_reader is None:
        from checkpoint_complete_live_capture import process_birth
        birth_reader=process_birth
    if evidence is None:evidence={}
    original.require(type(evidence) is dict and not evidence,'Fresh empty capture evidence required')
    start=time.monotonic();deadline=start+timeout
    evidence.update(schema='san14.b-warm-stable-capture.v1',status='CAPTURING',pid=pid,birth=expected_birth,
        base=base,profile_sha256=hashlib.sha256(profile_bytes).hexdigest(),max_attempts=max_attempts,
        timeout_seconds=timeout,interval_seconds=interval,attempts=[],game_writes=0,native_calls=0,
        installation_authorized=False,atomic_snapshot=False)

    def check_identity():
        original.require(reader.pid==pid and reader.memory.base==base and reader.sha256==original.GAME_SHA and
            birth_reader(reader)==expected_birth and bytes(profile)==profile_bytes,
            'Stable capture attachment/profile identity changed')

    def terminal(reason):
        raise ValueError(reason)

    try:
        for number in range(1,max_attempts+1):
            check_identity()
            if time.monotonic()>=deadline:terminal('Stable capture deadline exhausted')
            row=dict(attempt=number,started_seconds=time.monotonic()-start)
            evidence['attempts'].append(row)
            try:
                sample=original.capture_planning(reader,profile,expected_ruler)
            except BaseException as exc:
                row.update(outcome='REJECTED',error_type=type(exc).__name__,error=str(exc),
                    elapsed_seconds=time.monotonic()-start)
                # The predecessor uses the same error for birth drift, so that
                # specific case must be separated before granting another read.
                check_identity()
                if type(exc) is not ValueError or exc.args!=(RETRYABLE,):raise
                row['retryable_two_sample_mismatch']=True
                if number==max_attempts:terminal('Stable capture attempt limit exhausted')
                remaining=deadline-time.monotonic()
                if remaining<=0:terminal('Stable capture deadline exhausted')
                if interval:time.sleep(min(interval,remaining))
                continue
            check_identity()
            original.require(sample['pid']==pid and sample['birth']==expected_birth and sample['base']==base and
                sample['profileSha256']==evidence['profile_sha256'],'Stable capture returned another binding')
            if time.monotonic()>=deadline:
                row.update(outcome='REJECTED_AFTER_SAMPLE',error='Sampling finished after deadline',elapsed_seconds=time.monotonic()-start)
                terminal('Stable capture deadline exhausted')
            row.update(outcome='ACCEPTED_TWO_EQUAL_COMPLETE_SAMPLES',elapsed_seconds=time.monotonic()-start)
            evidence.update(status='PASS_READ_ONLY',elapsed_seconds=time.monotonic()-start,accepted_attempt=number)
            return sample
        terminal('Stable capture attempt limit exhausted')
    except BaseException as exc:
        evidence.update(status='REJECTED',error_type=type(exc).__name__,error=str(exc),elapsed_seconds=time.monotonic()-start)
        # Reviewable even when caller did not supply an evidence dictionary.
        try:exc.stable_capture_evidence=evidence
        except (AttributeError,TypeError):pass
        raise
