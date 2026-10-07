"""Publish reviewed evidence for the integration turn, without game access."""
from pathlib import Path
from datetime import datetime
import hashlib,json
P=Path(__file__).resolve().parent
OUT=P.parent.parent/'outputs/san14-link'
REPORTS={
    'dispatch_bridge':'checkpoint_load_dispatch_bridge_fixtures/20261007-015956-096833/result.json',
    'hook_set':'checkpoint_load_hook_set_fixtures/20261007-020339-973362/result.json',
    'request_commit':'checkpoint_load_request_commit_fixtures/20261007-021528-890139/result.json',
    'input_boundary':'checkpoint_load_input_boundary_fixture_20261007-021211-123341.json',
    'native_boundary_paths':'checkpoint_load_input_boundary_shadow_20261007-021732-513876.json',
    'title_identity':'checkpoint_title_identity_adapter_fixtures/20261007-020850-764906/result.json',
    'load_identity_chain':'checkpoint_guest_load_observation_chain_fixtures/20261007-021250-281578/result.json',
    'persistent_visual_helper':'checkpoint_map_wait_helper_runs/20261007-021116-101771/result.json',
}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    now=datetime.now().astimezone().isoformat();evidence={}
    for name,relative in REPORTS.items():
        path=P/relative;data=json.loads(path.read_text(encoding='utf8'));assert data['result']=='PASS',(name,data.get('result'))
        sources=data.get('source_sha256',{})
        if name=='native_boundary_paths':sources={'checkpoint_load_input_boundary_shadow.py':sources,**data.get('dependency_sha256',{})}
        assert isinstance(sources,dict),(name,'unsupported source manifest')
        for filename,digest in sources.items():assert sha(P/filename)==digest,(name,filename,'source changed since evidence')
        evidence[name]={'path':relative,'sha256':sha(path),'case_count':len(data.get('cases',[])),'checks':data.get('checks'),'source_hashes_matched':True,'scope':data.get('scope','See exact report limitations')}
    snapshot='checkpoint_load_boundary_snapshot_20261007-021504-715157.json'
    state=json.loads((P/snapshot).read_text(encoding='utf8'));assert state['result']=='PASS' and state['game_writes']==0
    report={
        'schema':'san14.guest-load-chain-progress.v1','updated_at':now,
        'result':'CORE_CHAIN_AND_OWN_WINDOW_HELPER_VERIFIED_NOT_LIVE',
        'evidence':evidence,'readonly_game_sample':{'path':snapshot,'sha256':sha(P/snapshot)},
        'active_ui_issue':{'selected_window':72358320,'first_error':'window is minimized; call activate_window, refresh with get_window, then retry get_window_state','recovery_error':'failed to activate captured window','user_requested_restore':True},
        'real_game_load_started':False,'real_game_hooks_installed_this_turn':False,'gameplay_date_advanced':False,
        'continuous_reward_sync_ready':False,'two_client_roundtrip_verified':False,'b_load_latency_measured':False,
        'new_code':[
            'Four independent dispatch entries plus the prior two finally entries cover User/Menu/Game/Load/worker/FileRead without reconfiguring an immutable bridge.',
            'Six pointer slots preserve page protections, restore only our own installed pointer and refuse to overwrite foreign replacements.',
            'Native field inspector binds Menu AFTER and parent Game BEFORE with paused User/input fields and worker ownership.',
            'One-use request core performs complete fresh native reads, durable intent and aligned -1 to63 CAS. A post-CAS failure remains uncertain and must keep load observers armed.',
            'Title adapter consumes actual upstream load receipts, commits force/person once, and observes the native initializer result without dereferencing old Load.',
            'Persistent visual helper implements explicit window/session binding, freeze/hold/prepare/reveal protocol and failure handling in its own process.'
        ],
        'next':[
            'Compose the production six-hook installer/controller using the verified cores, supported image/attachment checks and owned native menu entry.',
            'When the game window is visible, verify actual target capture, geometry, overlay ordering and failure behavior without loading a world.',
            'Connect native request/load/identity/new planning observation, local view restoration and shared-state verification before enabling real world replacement.'
        ]
    }
    text=f'''B端加载串联进展
更新：{now}

这轮从分散组件推进到了串联验证，但尚未成为可玩的双客户端MOD。

已经开发
加载请求入口：等游戏自己的读档菜单暂停大地图，再在父游戏状态即将处理加载请求的位置核对后台任务、选择和输入缓存；完整检查同步档后记录一次性加载意图，再提交63号专用槽位。它是我们明确实现的请求写入，不冒充原版已有的联机加载API。
身份适配器：只接受本次实际文件读取、加载线程和结束阶段产生的记录；恢复刘备势力与君主后，让原生初始化继续执行。旧加载对象即使已释放，也不会再读取它。
函数接入支撑：4个独立更新入口配合原有2个工作线程/文件读取入口；6个临时函数指针统一登记、恢复页面保护，不覆盖别的模块后来换上的入口。
持久画面助手：独立进程通过明确指令完成窗口绑定、保留旧图、等待或失败提示、新画面准备与撤罩；不是在游戏工作线程里同步截图。

串联测试有什么不同
本轮确实把“读到完整归档字节 → 核验 → 加载结束记录 → B身份切换”几个核心接在同一个调用链上。上游记录由核心自己产生，没有给下游塞一个假成功记录。
完整链的6个用例覆盖早/晚身份线程、文件内容不符、读取/加载/身份线程异常。文件不符和上游异常会阻止身份写入；已经提交身份后再异常不会假装恢复成功，也不会自动回滚重试。
不过测试仍在独立进程里的合成游戏对象上运行，原生世界反序列化、调度和初始化体部分为替身。它验证组件能串起来，不证明新DLL已经在真实游戏里完整读档。
身份适配39项、请求提交15项、原生边界检查48项、函数入口恢复7项和四入口ABI的91项检查通过。
另有9种原生机器码路径回放，核对暂停时大地图业务入口被挡住、旧协作任务的标记、无选择菜单路径和父游戏状态消费加载请求后的调度顺序。其外围UI/分配/部分构造仍使用替身，不宣称完整的全线程输入锁已经验证。
画面助手在我们自己创建的两个真实进程/窗口中通过8种协议测试，包含后台画面改变、超时、窗口移动/销毁、控制管道断开和失败保持。尚未证明SAN14真实窗口的加载页面已被遮住。

真实游戏情况
两次只读检查通过，仍是已恢复的34号测试起点，原生更新入口保持原样。本轮没有注入新的游戏模块、执行读档、换势力或推进日期。
发现一条特殊菜单分支的服务对象实际非空，已经按原生代码改为核对真正触发条件；实读world+BC=-1、panel+1F4=0，当前不会触发该分支。没有为了通过检查而改游戏字段。
窗口工具识别到了SAN14窗口，但报告最小化；尝试恢复时返回“failed to activate captured window”。已请用户恢复可见大地图，未继续发界面输入。

仍需接通
把这些核心组成真实常驻适配模块与控制器，完成地图遮罩和原生暂停之间的联动；再观测新地图、恢复B镜头并核对共享状态。当前只有加载/身份组件的串联测试，没有两台真实客户端的一旬闭环，也没有B完整读档的耗时数据。
恢复窗口后先验证真实窗口捕获与等待层，不需要用户重新演示赏赐或出征；完整读档要等生产入口和恢复条件接齐。
'''
    (OUT/'B端加载串联进展.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUT/'B端加载串联进展.txt').write_text(text,encoding='utf8')
    prefix='最新进展（2026-10-07）：加载核验、生命周期、B身份适配已完成同链独立进程验证；持久画面助手通过自有双进程窗口测试。请求提交核心已实现，但尚未安装为真实游戏完整加载入口。游戏窗口最小化且自动恢复失败，真实窗口验证等待恢复。详见《B端加载串联进展.txt》。\n\n'
    for filename in ('B端原生加载接入进展.txt','开发剩余工作评估.txt'):
        target=OUT/filename;old=target.read_text(encoding='utf8')
        if not old.startswith(prefix):target.write_text(prefix+old,encoding='utf8')
    contract=P/'checkpoint_load_integration_contract.json';c=json.loads(contract.read_text(encoding='utf8'))
    c['request']['pending_publication_implemented']=True
    c['request']['implementation']='checkpoint_load_request_commit.cpp; own-process verified, not installed'
    c['request']['selected_boundary']='Owned parent Game Update BEFORE after matching real Menu AFTER; original menu pauses User, exact native fields/worker ownership are checked by checkpoint_load_input_boundary. These observations are not an all-input global lock.'
    c['request']['after_cas_uncertainty']='If casApplied is1, keep load/identity observers armed even on false/Uncertain. Original Game may consume the published request. Never infer not-executed from return false.'
    c['identity_pair']['native_title_adapter_implemented']=True
    c['identity_pair']['adapter']='checkpoint_title_identity_adapter.cpp; 39 own-process tests and6 integrated byte/lifecycle/identity cases, no live installer'
    c['presentation']['persistent_helper_implemented']=True
    c['presentation']['helper']='checkpoint_map_wait_helper.exe;8 own-window cross-process tests, no SAN14 display proof'
    c['latest_evidence_report']=str(OUT/'B端加载串联进展.json')
    contract.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'result':report['result'],'exact_source_hashes_verified':True,'output':str(OUT/'B端加载串联进展.txt')},ensure_ascii=True))
if __name__=='__main__':main()
