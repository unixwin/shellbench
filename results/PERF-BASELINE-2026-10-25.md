# 性能基线资产 — rubash / niubash vs GNU bash 5.3.20（2026-10-25）

> 本文件是性能工作的**确定性基线资产**：后续每轮优化的 before/after 对照、回归判定与对外引用数字，一律以本文件为准。原始数据与两份源报告见文末索引；数字冲突时以原始数据为准并修订本文件。

## 口径与溯源

- 被测引擎：rubash master `1e72c7f9b323356894402582fb004409c0b990e8`（release 构建：仓库 `[profile.release]` opt-level 3 + LTO + codegen-units 1，`RUSTFLAGS=-C debuginfo=0`；引擎真身 = `src/main.rs` 的 `rubash` 二进制，仓内 `target/*/bash` 是 niu 转发 shim，不作数）。
- 宿主：niubash master `b53e6bff`（v1.4.4），仅启动裁决节使用。
- Oracle：自编译 GNU bash 5.3.20（`~/workspace/rubash-audit/gnu-bash-5.3.20/bin/bash`）。
- 采样纪律：采样门 = load1 ≤ 2.0 且全机无 cargo/rustc；绑核 `taskset -c 0`、`nice -n 10`；每例新进程、多次取中位；stdout 逐例 sha256 与 GNU 校验一致。
- 两套数据：**A 表** = perf 簇 30 例精密盘点（墙钟 + rusage user 双记）；**B 表** = shellbench 409 例广度差距表（per-op 中位比值）。release 套件全程 load 1.52–2.02，数据干净；debug 数字仅作形状旁证，不作对外引用。

## 一、启动开销裁决（对外唯一可引用口径）

统一口径：50 样本弃 5 预热、三壳交错采样、干净 HOME、release、load_end=1.47。墙钟 ms。

| 条件 | 壳 | min | p50 | p90 | mean | max |
|---|---|---|---|---|---|---|
| 空跑（stdin=/dev/null） | niu 1.4.4 | 16.64 | **16.98** | 23.15 | 18.81 | 37.14 |
| | rubash | 3.25 | 3.39 | 4.53 | 4.20 | 24.11 |
| | GNU 5.3.20 | 2.58 | 2.65 | 3.09 | 2.91 | 8.26 |
| `-c 'true'` | niu 1.4.4 | 3.84 | **3.96** | 4.10 | 4.03 | 5.70 |
| | rubash | 3.35 | 3.43 | 3.57 | 3.51 | 4.95 |
| | GNU 5.3.20 | 2.53 | 2.59 | 2.70 | 2.70 | 4.78 |

裁决（定谳，不得翻用旧数）：
1. niu #79 的「~550 ms 固定开销」**不复现，差两个数量级**，至多为其报告环境个案，永不得作为 niu 的性质引用。
2. 「~14 ms 启动」**不成立**（对 `-c` 高估 3.5 倍、对空跑低估），维持摘除、禁用。
3. 官网 facet 6 的 26.3 ms 是 Windows 真机数（min-of-20），本机不可复现/证伪；**对外唯一可引用 = 本表这组带完整口径的 Linux 数**；Windows 对 Git Bash 的数字须真机按现行版本重测后才可用，此前全线禁用启动毫秒数。
4. 附带优化项：niu 空跑比 `-c` 贵 ~13 ms（非 tty 也付交互栈初始化全价），已立案 **niubash #562**（非交互快路径）。

## 二、A 表：release 全表（30 例，perf 簇）

秒，中位数；ratio = rubash/GNU；全部用例 stdout sha 与 GNU 逐例一致。

| case | rubash wall | rubash user | GNU wall | GNU user | ratio wall | ratio user |
|---|---|---|---|---|---|---|
| arith_200k | 2.191 | 2.071 | 0.7326 | 0.7266 | 2.99x | 2.85x |
| arith_20k | 0.2169 | 0.2052 | 0.0756 | 0.0726 | 2.87x | 2.83x |
| array_arith_read_8000 | 0.4533 | 0.4395 | 0.0472 | 0.0400 | 9.60x | **10.98x** |
| array_braced_read_8000 | 0.1847 | 0.1776 | 0.0706 | 0.0554 | 2.61x | 3.21x |
| array_fill_30000 | 0.4211 | 0.4061 | 0.1204 | 0.1060 | 3.50x | 3.83x |
| array_fill_4000 | 0.0604 | 0.0552 | 0.0175 | 0.0150 | 3.46x | 3.68x |
| array_iterate_10000 | 0.1982 | 0.1107 | 0.0599 | 0.0385 | 3.31x | 2.87x |
| array_iterate_20000 | 0.3045 | 0.2248 | 0.1264 | 0.0730 | 2.41x | 3.08x |
| array_iterate_40000 | 0.6160 | 0.4557 | 0.1675 | 0.1424 | 3.68x | 3.20x |
| array_literal_100k | 0.2217 | 0.1811 | 0.0846 | 0.0432 | 2.62x | 4.20x |
| assign_20k | 0.1543 | 0.1344 | 0.0474 | 0.0441 | 3.25x | 3.05x |
| assoc_fill_100k | 1.429 | 1.373 | 0.4053 | 0.3510 | 3.53x | 3.91x |
| big_scalar | 0.3983 | 0.2662 | 0.2534 | 0.0518 | 1.57x | 5.14x |
| comsub_loop | 0.0511 | 0.0449 | 0.6851 | 0.3970 | 0.07x | **0.11x** |
| comsub_nest50 | 0.0646 | 0.0594 | 0.0440 | 0.0184 | 1.47x | 3.22x |
| declare_p_dump | 0.5157 | 0.2492 | 0.1673 | 0.0618 | 3.08x | 4.04x |
| floor_flat | 0.2074 | 0.1472 | 0.0340 | 0.0302 | 6.09x | 4.88x |
| floor_if | 0.0803 | 0.0719 | 0.0205 | 0.0181 | 3.92x | 3.98x |
| floor_if_redir | 0.1318 | 0.1027 | 0.0210 | 0.0143 | 6.28x | 7.19x |
| floor_redir | 0.0797 | 0.0646 | 0.0433 | 0.0218 | 1.84x | 2.96x |
| func_20k | 0.3316 | 0.3147 | 0.1113 | 0.1087 | 2.98x | 2.90x |
| func_2k | 0.0364 | 0.0315 | 0.0131 | 0.0111 | 2.78x | 2.85x |
| heredoc_10mb | 0.8243 | 0.2942 | 0.1894 | 0.0704 | 4.35x | 4.18x |
| pipe_200 | 0.0074 | 0.0035 | 0.1915 | 0.0747 | 0.04x | **0.05x** |
| pos_5000 | 0.0184 | 0.0087 | 0.0150 | 0.0061 | 1.23x | 1.42x |
| read_loop_100k | 2.681 | 1.180 | 0.8571 | 0.4074 | 3.13x | 2.90x |
| spawn_true | 0.3256 | 0.1328 | 0.2448 | 0.1034 | 1.33x | 1.28x |
| startup_colon | 0.0036 | 0.0005 | 0.0026 | ~0 | 1.37x | n/m |
| startup_echo | 0.0036 | 0.0010 | 0.0026 | ~0 | 1.41x | n/m |
| string_ops | 0.3083 | 0.3012 | 0.3698 | 0.2825 | 0.83x | 1.07x |

三档归类（user 比值）：**已领先** pipe_200 0.05×、comsub_loop 0.11×（少 fork 进程模型）；**接近** string_ops 1.07×、spawn_true 1.28×、startup 墙钟 1.37–1.41×、pos_5000 1.42×；**其余明显落后**，主体是 2.8–3.2× 的均匀地板税。

单位成本（user/单位，rubash vs GNU）：平铺 `:` 7.4µs vs 1.5µs；赋值 6.7 vs 2.2；算术迭代 10.3 vs 3.6；if 句 14.4 vs 3.6；函数调用 15.7 vs 5.4；`: >/dev/null` 12.9 vs 4.4；**if+重定向复合 51.3 vs 7.1（地板里最贵）**；spawn_true 442.8µs vs 344.7µs。

exec-profile 分桶（release，平铺 `:`，µs/条，分桶总 2.96）：**dispatch 1.88（占 64%）** · chain 0.97 · jobs 0.86 · matcmd 0.66 · linecmd 0.54 · expand 0.18 · scans 0.14。攻地板第一刀位 = dispatch 本体。if_redir 的 7.2× 经分桶确认本质仍是 dispatch 税 ×3 命令/迭代，非重定向簿记税。

## 三、B 表：shellbench 广度差距表（409 例，gap-v1）

ratio = rubash/GNU per-op 中位，<1 = rubash 快。可比 408 例（1 例不可测）：**领先 53 / 接近 17 / 落后 338**。唯一整类领先：subst（命令替换）中位 0.538×。

| 类别 | 例数 | 中位比值 | 读数 |
|---|---|---|---|
| subst | 14 | 0.538 | 领先 |
| jobs | 12 | 1.297 | 落后 |
| redir | 18 | 1.310 | 落后 |
| funcs | 12 | 1.652 | 落后 |
| builtin | 68 | 1.705 | 落后 |
| mixed | 8 | 2.010 | 落后 |
| glob | 12 | 2.534 | 落后 |
| control | 19 | 2.792 | 落后 |
| cond | 18 | 2.936 | 落后 |
| arith | 66 | 3.010 | 落后 |
| data | 34 | 3.017 | 落后 |
| startup | 10 | 3.151 | 落后 |
| expand | 71 | 4.118 | 落后 |
| arrays | 20 | 4.715 | 落后 |
| strings | 18 | 5.420 | 落后 |
| parse | 8 | 14.725 | 落后 |

最差单条（前 12）：arrays.assoc_get_miss **37.3×**、parse.n_control@2000 30.7×、parse.n_funcs@1500 27.8×、builtin.declare_local_like 23.1×、arrays.append@100000 19.5×、parse.n_mixed@5000 18.2×、arrays.assign_idx_mod 16.0×、parse.n_simple@3000 15.8×、parse.n_expand@2000 13.6×、expand.arith_in_subscript 13.3×、builtin.declare_assign 12.9×、expand.brace_nested 11.7×。全量逐例表见 `gap-v1.md` 与同目录 CSV/JSON。

注：B 表的 parse 类口径是「整脚本解析吞吐」，与 A 表的逐命令执行地板是两个维度，不可混读。

## 四、历史对照裁决（防回退基线）

- **#914 / #1510 无回退**：iterate release 三档 user ×2.03/×2.03 严格线性，形状税为零；fill/assoc 全线性（assoc 100k release 1.37s）。
- **#1264 已降级**：debug 同口径字面量改善 ~3.9×、big_scalar ~2.8×、heredoc ~2.1×；release 下收拢到 3–5× 一般地板税，不再单独立项。
- **#682 地板**：release 分桶与修复前 M 账本（debug）同名对照每桶皆降（dispatch −59%、jobs −67%），与 #1510 修复面吻合；本簇全包含口径比历史斜率口径系统性高约 8%，不可跨口径判回退。
- **#349 桌面 release 口径**：arith/func 四个工作量同落 2.8–2.9×，与 Android 真机 ~2.1× 已可桥接；关单仍以真机 release 复测为唯一门槛。
- **唯一形状性差距**：`$((a[i]))` 算术直读 Θ(n)/读残差（release 11.0×，同 N braced 读 3.2×）——优化第一优先，已派 perf-arrays 簇列为第一靶子；parse 类（B 表 14.7×）已派 perf-parse 簇。

## 五、原始数据与复跑

- A 表源报告：`~/workspace/rubash-fix4/clusters/perf/REPORT.md`；原始数据 `~/workspace/rubash-fix4/clusters/perf/results/{release.jsonl, debug.jsonl, profile_release.txt, profile_debug.txt, startup_adjud.json}`；harness 在其 `harness/`（`bash harness/drive_rest.sh` 幂等续跑）。
- B 表原始数据：本目录 `20261025-101340-gnu.{csv,json,md}`、`20261025-102548-rubash.{csv,json,md}`、`gap-v1.md`（全量逐例表）。
- 套件本体：`~/workspace/shellbench/`（用例即数据 + 生成器；后续每轮优化跑完在此目录落新一期结果，并回填本文件的对照结论）。
