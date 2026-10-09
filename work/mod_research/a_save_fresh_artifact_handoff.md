# A 自动新档 → B 加载材料

2026-10-09。本次只读取私有归档并创建独立副本/配置，没有打开游戏进程、Steam文件或UI，没有执行加载。存档不提交Git。

**现有成功路线并非离线修改存档势力字节。** B在原生Load完成后的Title身份阶段，由 `b_warm_profile_identity.cpp` 按不可变profile从张鲁转换为刘备，再建立规划界面。因此保留A原档完整字节；不新增猜测格式的补丁或将副本谎称已转好的刘备存档。

私有材料：`a_save_fresh_artifact_runs/20261009-231156-564728/result.json`，SHA `5f51bf1c0c0a444eb02c9e7c7ea81610885733394270e22565d31f064e24134c`。6份来源、7份归档输入、6份新材料逐项复核哈希一致，两个profile经过原 `profile_from_dict` 严格验证，各96字节。

| 文件 | 大小 | SHA-256 | 读取验证状态 |
|---|---:|---|---|
| source-1/svdexccSC03.s14 | 274879 | a3de964420d8f0c9f34dcdbd1056dc0e3f355222732b00e3e10bc49742e2eab7 | 来自本轮真实A自动Save及完整读回校验，尚未由B读回 |
| source-2/svdexccSC03.s14 | 274975 | cbe6d0b9cd97ed6053fb797d68193c8bbe74a4118ffdebc83583215c64c51bd0 | 上轮用户新49的归档副本，已有真实B加载验证 |

两个副本均与各自来源逐字相等，0字节变化，只改私有副本路径和文件名以匹配slot63/CC03原生接口。未使用存档格式解析器；不能把真实Save/读回SHA与profile预期等同于新A档已通过游戏再次加载。

新A来源为 `a_save_runtime_live_runs/20261009-230910-151040/mp9df29e91.s14`。已核该run返回PASS_REAL_SINGLE_FRESH_SAVE、原档不变且仅新增预期文件；artifact回执error0/Complete、phase31、workerJoined/finalizer/returnMatched/completedRequests各1、active/abnormal0、完整字节校验为true。

`plan-draft.json` 第一代：203-08-11/current张鲁12 → 加载同日A档 → 刘备2；第二代：203-08-11/current刘备2 → 已验证203-08-21新49 → 刘备2。保存来源均张鲁force12/ruler666/district11，目标均刘备force2/ruler952/district2。第二档仍是人工保存来源，不能称两份A自动旬末档。

**草稿不可直接执行。** `initial_target=null`，没有伪造旧file_id。主agent须新采实际CC03的大小/SHA/7字段file_id并写到另一个新plan，备份当前85份存档，确认fresh PID/birth、张鲁中旬五态、原槽/规则/无debugger和批准构建闭包。草稿中的target/Steam路径只是沿用本机历史路径文本，本任务没有访问这些目录；如本机环境改变必须重新选择核验。

复用现有实测入口 `b_warm_stable_refresh_diagnostic.py`：完成上述新plan后先 `--check --pid <fresh> --plan <new-plan>`，再在独立授权条件下 `--execute --no-new-commands`，两者均带原入口要求的helper/pair构建路径与SHA。本任务没有运行这两个命令。

已实测构建参考：pair `b_warm_stable_refresh_build_runs/20261009-220219-504303/result.json` SHA `66c42b886ee818da39fe987d79d296e2aab71eac4d7d8d0cff784abe2c69363a`；helper `b_warm_coordinator_build_runs/20261009-181031-457801/result.json` SHA `4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a`。必须现场重验来源，不能复制旧PID/claim/已消费bank。原生Refresh负责真正FileWrite/读回、加载、身份转换、封存和锁释放；不得提前调用旧 `files.apply` 物理替换目标。
