"""Publish verified CC storage milestone, keeping prior artifacts immutable."""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil
import checkpoint_cc_publish_start as p
from checkpoint_cc_publish_gate import validate_fixture
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs/san14-link'
RUN=ROOT/'checkpoint_cc_publish_runs/20261007-011018-444185'
result=p.load(RUN/'result.json')
assert result['result']=='PASS' and result['native_publish_complete'] and result['two_observed_native_reads_matched']
assert p.report_ok(result['adapter'],1,result['before'])
assert result['existing_files_unchanged'] and result['actual_hook_slots_restored'] and result['known_coverage']['matched']
assert not result['load_requested'] and not result['full_world_verified']
validate_fixture(result['fixture']['fixture_path'],p.DLL)
before=p.load(RUN/'known-before.json');after=p.load(RUN/'known-after.json')
assert before['save_files']==after['save_files'] and len(after['save_files'])==83
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
archive=ROOT/'checkpoint_cc_publish_versions'/stamp;archive.mkdir(parents=True,exist_ok=False)
files=list(result['fixture']['source_sha256'])+['checkpoint_cc_publish.dll','checkpoint_cc_publish_start.py','checkpoint_cc_publish_gate.py',
    'checkpoint_cc_publish_binding.json','checkpoint_cc_stage.py','checkpoint_cc_stage_result.json','checkpoint_cc_stage_once.intent',
    'checkpoint_cc_publish_native_once.intent','checkpoint_cc_publish_dry_once.json','checkpoint_cc_publish_publish_once.json',
    'checkpoint_cc_publish_launcher_test.py','native_storage_publish_handoff.json','native_storage_publish_notes.txt',
    'checkpoint_metadata_boundary_contract.json','publish_checkpoint_cc_progress.py']
for name in files:shutil.copy2(ROOT/name,archive/name)
manifest={'created':datetime.now().astimezone().isoformat(),'executed_result':str(RUN/'result.json'),
    'executed_result_sha256':p.sha(RUN/'result.json'),'files':{name:p.sha(archive/name) for name in files}}
p.save(archive/'manifest.json',manifest)
handoff={'schema':'san14.cc-native-publication-handoff.v1','result':'PASS','executed_result':str(RUN/'result.json'),
    'executed_result_sha256':p.sha(RUN/'result.json'),'frozen_sources_manifest':str(archive/'manifest.json'),
    'target':str(p.TARGET),'slot':63,'bytes':274880,'sha256':p.SHA,'current_game':{k:result['after'][k] for k in ('pid','process_birth','base','pinned_user','pinned_game','pinned_world','global_rng','cache_mode')},
    'current_cache_graph':result['after']['cache_graph'],'native_file_visible_and_two_reads_match':True,
    'metadata_slot63_currently_indexed':False,'world_load_performed':False,'B_identity_restored_by_this_run':False,
    'future_load_bytes_proven':False,'full_world_verified':False,'next':'Fresh guarded load scope must bind this exact CC file through actual native load and B identity initialization; do not rerun any consumed publish/read once.'}
p.save(ROOT/'checkpoint_cc_publish_verified_handoff.json',handoff)
summary={'schema':'san14.checkpoint-cc-publication-progress.v1','updated':datetime.now().astimezone().isoformat(),
    'native_publication':'PASS_ONE_REAL_ATTEMPT','native_file_reads':[274880,274880],'target_basename':p.TARGET.name,'native_slot':63,
    'target_sha256':p.SHA,'original_save_count_unchanged':82,'total_s14_after':83,'known_coverage':result['known_coverage'],
    'hook_slots_and_pages_restored':True,'date':{'year':203,'month':8,'day':11,'period':'中旬'},'player':'张鲁',
    'world_load_completed':False,'B_load_completed':False,'wait_overlay_completed':False,'two_real_clients_completed':False,
    'B_load_latency_measured':False,'evidence':{'live_result':str(RUN/'result.json'),'live_result_sha256':p.sha(RUN/'result.json'),
        'adapter_cases':22,'core_cases':27,'native_write_ABI_cases':5,'launcher_predicate_cases':28},
    'retired_direction':'Private metadata disappears during Title full scan; native CC file publication replaces manual registration for the current route.',
    'historical_metadata_fixture_limit':'The old 54 abstract cases did not prove actual native CC naming; they are not live registration evidence.'}
text=f'''B端原生加载接入进展
更新：{summary['updated']}

本轮已打通：让同步检查点进入游戏正在使用的原生存档接口。
选用了本地与原生接口均为空的第63槽，实际名称为svdexccSC03.s14。新建文件内容与已验证的A导出完全相同，为274,880字节。
实测发现只复制进目录后Steam仍报告文件不存在，因此停止在文件检查阶段，没有继续读档。随后使用独立的新操作范围，经游戏正在使用的Steam接口只写入一次，再连续两次完整读回；两次长度、SHA256和本地字节全部一致。

验证结果
原有82份.s14文件内容保持不变，另有1份本轮创建的专用CC测试文件；当前总数83。
游戏仍是203年8月中旬、张鲁。已核查783条对象记录、48,400格序列化字段及随机状态不变，临时虚表入口和页面保护均恢复。
本轮没有加载世界、推进日期或切换势力，不需要用户再读取34号档。

设计调整
正式加载进入Title时，游戏会重新扫描存档目录，先前临时登记的私有metadata会被清掉。当前改为让游戏从真正的原生CC文件自行扫描重建，减少手动管理原生目录节点的步骤。
真实文件名来自游戏原生格式化函数。旧离线metadata核心的54项测试使用了错误的模拟文件名，只能作为抽象链表和事务测试，不能当作真实命名或实际登记成功。

验证范围
发布核心27项独立进程测试、适配器22项测试、原生写入ABI的5项机器码回放及启动器28项判定检查通过。真实发布也已通过一次。
原生FileWrite并非条件创建接口；本次限制在工具独占创建、身份与完整字节已绑定的测试文件。没有宣称排除了任意外部写入者的竞态，也没有替代未来加载时的实际字节校验。
加载线程和身份线程的异常清理桥另有17种场景、473项检查通过，目前仍是独立进程验证。

下一步
1. 用新的受控加载入口提交这个正数槽位，观察Title扫描、实际文件读取、完整世界重建，并在原生身份初始化前恢复B势力。
2. 核对新世界及下一旬是否可正常操作；继续处理尚未解释的经济等业务差异，不将其当显示字段忽略。
3. 接入窗口/无边框的旧地图等待画面，再做两台真实客户端连续多旬联调。
完整B端加载、等待画面、双机闭环都尚未完成；B加载耗时仍未测得。此次发布/读回成功不能代替整轮同步性能结论。
'''
for name in ('B端原生加载接入进展.txt','B端原生加载接入进展.json'):
    shutil.copy2(OUT/name,archive/('previous-'+name))
(OUT/'B端原生加载接入进展.txt').write_text(text,encoding='utf-8-sig')
(OUT/'B端原生加载接入进展.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assessment=OUT/'开发剩余工作评估.txt'
old=assessment.read_text(encoding='utf-8-sig');shutil.copy2(assessment,archive/('previous-'+assessment.name))
prefix='最新进展（2026-10-07）：原生CC同步文件发布和两次完整读回已实机通过。原82份存档未变，另有1份专用测试文件；未加载世界。当前采用原生CC文件随Title扫描自动建目录，不再把私有metadata登记作为主线。接下来仍是完整B加载、身份恢复、等待画面与双机闭环。详见《B端原生加载接入进展.txt》。\n\n'
old=old.replace('还缺：自动原生保存、完成与文件关联、B安全退出临时战局并自动重载、','还缺：B安全退出临时战局并自动重载、')
assessment.write_text(prefix+old,encoding='utf-8-sig')
print(json.dumps({'result':'PASS','output':str(OUT/'B端原生加载接入进展.txt'),'handoff':str(ROOT/'checkpoint_cc_publish_verified_handoff.json'),'archive':str(archive)},ensure_ascii=False))
