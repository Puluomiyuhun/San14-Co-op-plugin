"""Latest retained Period Owner + upstream Gate -> real pipe -> TLS -> SQLite.

The frozen network flow is reused unchanged. Native business/date and B's loaded
receipt remain diagnostic/model; this is not a game launcher or production host.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import unittest

import a_save_ipc_flow_test as flow
import a_save_ipc_client as ipc

HERE=Path(__file__).resolve().parent
BOUNDARIES=[]
ACTIVE=None
BaseClient=ipc.ASaveClient


def validate_build(folder):
    raw=(folder/'result.json').read_bytes();report=flow.strict_json(raw)
    ipc.require(report.get('schema')=='san14.a-save-period-ipc-build.v1' and report.get('result')=='PASS'
        and report.get('sources_unchanged') is True and report.get('game_access') is False,
        'Not a passing offline period pipe build')
    sources=report.get('sources')
    required={'a_save_period_ipc_fixture.cpp','planning_period_owner.cpp','planning_period_owner_lifecycle.inc',
        'planning_input_interlock_gate.cpp','planning_period_interlock.cpp','a_save_ipc.cpp','a_save_ipc.h',
        'a_save_period_ipc_build.py','a_save_period_ipc_flow_test.py','a_save_ipc_flow_test.py'}
    ipc.require(type(sources) is dict and required<=set(sources) and len(sources)<=128,'Missing composition sources')
    ipc.require('a_save_user_owner.cpp' not in sources,'Frozen physical Owner cannot substitute latest period Owner')
    for name,expected in sources.items():
        ipc.require(type(name) is str and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*',name) is not None
            and Path(name).suffix in ('.h','.cpp','.asm','.inc','.py') and type(expected) is str
            and re.fullmatch('[0-9a-f]{64}',expected) is not None,'Invalid composition source identity')
        ipc.require(flow.sha((HERE/name).read_bytes())==expected,'Composition source changed: '+name)
    for name,key in (('fixture.exe','fixture_sha256'),('a_save_period_ipc.lib','production_sha256')):
        ipc.require(flow.sha((folder/name).read_bytes())==report[key],'Native build artifact changed')
    ipc.require(set(report['runtime_sha256'])=={'reward.dll','checkpoint_planning_hold.dll'},'Incomplete owned runtime')
    for name,expected in report['runtime_sha256'].items():
        ipc.require(flow.sha((folder/name).read_bytes())==expected,'Owned runtime changed')
    return dict(result_sha256=flow.sha(raw),fixture_sha256=report['fixture_sha256'],sources=sources,
        source_count=len(sources),sources_match_current=True,game_access=False)


class PeriodFixture(flow.OwnedFixture):
    def __init__(self,*args,**kwargs):
        global ACTIVE
        ipc.require(ACTIVE is None,'One retained native fixture required')
        super().__init__(*args,**kwargs);ACTIVE=self

    def boundary(self,period):
        row=self.message()
        ipc.require(row.get('event')=='PERIOD_BOUNDARY' and row.get('period')==period
            and row.get('serial')==2 and row.get('retired_count')==period
            and row.get('retired') is (period==2) and row.get('command_sequence')==2
            and row.get('ready_revision')==(2 if period==1 else 3)
            and row.get('same_owner') is True and row.get('game_access') is False
            and row.get('fixture_date_transition') is True and row.get('production_permit') is False,
            'Native logical transition not confirmed')
        BOUNDARIES.append(row)

    def close(self):
        global ACTIVE
        super().close()
        if ACTIVE is self: ACTIVE=None


class PeriodClient(BaseClient):
    """Test adapter: wait for actual owned engine event, never approve game input."""
    def submit(self,reservation):
        if reservation.request['generation']==2:
            ipc.require(ACTIVE is not None,'No owned native source');ACTIVE.boundary(1)
        return super().submit(reservation)

    def wait_artifact(self,generation,**kwargs):
        artifact=super().wait_artifact(generation,**kwargs)
        if generation==2:
            ipc.require(ACTIVE is not None,'No owned native source');ACTIVE.boundary(2)
        return artifact


class PeriodFlowTests(unittest.TestCase):
    def test_actual_period_owner_pipe_tls_and_journal(self):
        previous_fixture=flow.OwnedFixture
        try:
            flow.OwnedFixture=PeriodFixture;ipc.ASaveClient=PeriodClient
            case=flow.NativeFlowTests()
            case.test_room_reserve_precedes_two_native_submits_then_tls_and_sqlite()
            self.assertEqual([b['period'] for b in BOUNDARIES],[1,2])
            end=flow.EVIDENCE[-1]['owner_final']
            self.assertEqual((end['period_serial'],end['retired_periods'],end['reward_sequence'],end['native_reads']),(2,2,2,4))
            self.assertIs(end['production_permit'],False)
        finally:
            ipc.ASaveClient=BaseClient;flow.OwnedFixture=previous_fixture

    def test_stop_after_real_rebind_denies_second_save_and_old_export(self):
        model=flow.Fixture();reservation=model.reserve();fixture=channel=None
        try:
            fixture=PeriodFixture(flow.OUTPUT/'stop-after-rebind',reservation.request['room_id'],reservation.request['room_epoch'])
            channel=BaseClient(fixture.endpoint,on_fault=model.binding.hold)
            channel.submit(reservation);channel.wait_artifact(1);fixture.boundary(1)
            self.assertEqual(channel.snapshot()['completed_requests'],1)
            stopped=channel.stop();self.assertEqual(stopped['stopped'],1)
            with self.assertRaises(ipc.ASaveChannelError):channel.copy(1)
            with self.assertRaises(ipc.ASaveChannelError):channel.submit(reservation)
            self.assertTrue(model.room.checkpoint_status()['closed'])
        finally:
            if channel:channel.close()
            if fixture:fixture.close()
        flow.NativeFlowTests().closed_owner(fixture,1,1)
        end=fixture.final
        self.assertEqual((end['period_serial'],end['retired_periods'],end['reward_sequence']),(2,1,2))
        flow.EVIDENCE.append(dict(case='STOP_AFTER_NATIVE_REBIND',owner_final=end,game_access=False,
            room_closed=True,second_save=False,old_packet_republished=False,resources_closed=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build-run',required=True,type=Path)
    args=parser.parse_args();flow.BUILD=args.build_run.resolve();flow.BUILD_EVIDENCE=validate_build(flow.BUILD)
    flow.OUTPUT=HERE/'a_save_period_ipc_flow_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');flow.OUTPUT.mkdir(parents=True)
    # Include the actual imported Python transport/protocol dependency closure.
    import sys
    repository=HERE.parents[1]
    paths={Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,'__file__',None)
        and Path(m.__file__).suffix=='.py' and Path(m.__file__).resolve().is_relative_to(repository)}
    paths.add(Path(__file__).resolve())
    before={str(p.relative_to(repository)).replace('\\','/'):flow.sha(p.read_bytes()) for p in paths}
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
        for cls in (flow.ClientTests,PeriodFlowTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged=all(flow.sha((repository/n).read_bytes())==h for n,h in before.items())
    try:validate_build(flow.BUILD)
    except (OSError,ValueError,RuntimeError):unchanged=False
    passed=result.wasSuccessful() and not result.skipped and unchanged
    report=dict(schema='san14.a-save-period-ipc-flow.v1',result='PASS' if passed else 'FAIL',
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        sources_unchanged=unchanged,source_sha256=before,build_evidence=flow.BUILD_EVIDENCE,
        cases=flow.EVIDENCE,boundaries=BOUNDARIES,game_access=False,steam_access=False,actual_two_games=False,
        full_input_held=False,production_permit=False,actual_simulation=False,actual_game_save_load=False,
        planning_period_session_composed=False,native_logical_period_mapping='OWNED_FIXTURE',
        network_transport='REAL_LOOPBACK_TLS',native_business='TEST_DOUBLES',guest_load_receipt='MODEL_ONLY')
    path=flow.OUTPUT/'result.json';path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=report['result'],path=str(path))))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
