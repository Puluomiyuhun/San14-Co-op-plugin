# 未随Git分发的本地生成输入

下列文件含完整原生函数、大段游戏数据或用户世界样本，已从公开源码排除。短入口指纹/RVA锚点仍用于版本与互操作校验。原有生成器保留，但有些依赖历史私有记录，不能保证fresh clone直接生成。不要用空白数据、随意改哈希或其他版本游戏替代。

路径均相对于仓库；生成器为定位信息，不是允许批量执行的安装步骤。输出已由.gitignore精确排除。

| 本地输入 | 生成器 | 所需私有输入 |
| --- | --- | --- |
| `work/mod_research/startup_switch_profile.h` | `py -3 work/mod_research/make_startup_switch.py` | game-runtime-image.bin; startup-load-boundary-baseline.json (783 user world records); imports make_identity_pair_fixture.RANGES |
| `work/mod_research/checkpoint_load_mode_profile.h` | `py -3 work/mod_research/checkpoint_load_mode_make_profile.py` | game-runtime-image.bin; runtime-pdata.bin through disasm_chained |
| `work/mod_research/checkpoint_push_profile.h` | `py -3 work/mod_research/checkpoint_push_make_profile.py` | game-runtime-image.bin; private_checkpoint_save_profile.json |
| `work/mod_research/checkpoint_target_metadata_native_anchors.inc` | `py -3 work/mod_research/checkpoint_target_metadata_native_shadow.py` | private_checkpoint_load_shadow/disasm archive and local parser input records; not a standalone supplied fixture |
| `work/mod_research/identity_pair_fixture_code.h` | `py -3 work/mod_research/make_identity_pair_fixture.py` | game-runtime-image.bin |
| `work/mod_research/native_rng_fixture_code.h` | `py -3 work/mod_research/make_native_rng_fixture.py` | game-runtime-image.bin; lockstep-traces/camera-near-rng-k2/trace.jsonl for additional generated observed states |
| `work/mod_research/visibility_fixture_code.h` | `py -3 work/mod_research/make_visibility_fixture.py` | game-runtime-image.bin |
| `work/mod_research/auto_cache_profile.h` | `py -3 work/mod_research/auto_cache_make.py` | game-runtime-image.bin |
| `work/mod_research/checkpoint_task_completion_profile.h` | 尚缺独立生成器 | No standalone generator found in copied Python sources; requires local profile construction for exact Load/Title spans |
| `work/mod_research/save_return_observer_profile.h` | `py -3 work/mod_research/save_return_observer_make_profile.py` | game-runtime-image.bin; runtime-pdata.bin |
| `work/mod_research/combat_filter_fixture_code.h` | `py -3 work/mod_research/make_combat_filter_fixture.py` | game-runtime-image.bin |
| `work/mod_research/combat_inputs_fixture_code.h` | `py -3 work/mod_research/make_combat_inputs_fixture.py` | game-runtime-image.bin |
| `work/mod_research/economy_selector_fixture_code.h` | `py -3 work/mod_research/make_economy_selector_fixture.py` | game-runtime-image.bin |
| `work/mod_research/troops_fixture_code.h` | `py -3 work/mod_research/make_troops_fixture.py` | game-runtime-image.bin |
| `work/mod_research/human_ai_fixture_code.h` | `py -3 work/mod_research/make_human_ai_fixture.py` | game-runtime-image.bin |
| `work/mod_research/native_gate_fixture_code.h` | `py -3 work/mod_research/make_native_gate_fixture.py` | game-runtime-image.bin |

`startup_switch_profile.h` 尤其包含783条基线世界样本，它不能作为公共默认剧本。`checkpoint_task_completion_profile.h` 尚需补本地生成步骤。新组件测试应接收外部私有输入目录，把临时输入放在ignored构建目录，避免重新把这些内容写入被跟踪源码。
