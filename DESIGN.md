# benchsuite — 设计文档

## 1. 定位

benchsuite 是一个**独立的、跨平台的 shell 性能基准套件**：定位类比
redis-benchmark 之于 Redis——一个标准、可复跑、口径固定的基准工具，
任何 shell 二进制放进来都用同一套题跑出可比的数。

它服务于一个总目标：**rubash / niubash 的性能全面超越 GNU bash**。
套件产出的差距清单（哪些项落后、落后多少）就是引擎优化的优先级队列；
每次优化后用基线对照模式复测，数字说了算。

**边界（重要）**：本套件只测性能，不测正确性。正确性回归是另一条线
（各仓自家测试套件，issue 固化成回归用例在那边做）。本套件的用例只带
一个 sanity 守卫（退出码/输出正则校验），目的是防止「跑错了所以显得快」
的假数据进入报表，不构成正确性断言。

## 2. 设计原则

1. **零依赖**：运行器只用 Python 标准库。装了 Python 3.8+ 的机器
   （Linux / Windows / macOS）原样可跑，不引入任何安装摩擦。
2. **被测对象只是路径**：`--shell /path/to/binary`，同一语料跑所有
   shell；版本字符串、主机信息、起始 load 都记进结果元数据。
3. **用例即数据**：用例是带分类标签的 shell 片段 + 规模参数
   （见 `benchsuite/model.py` 的 `Case`）。新增覆盖 = 往表里加一行，
   不是写一段新程序。
4. **规模靠生成器，不靠手写堆量**：运算符×上下文、内建×形态、
   展开式×规模、语料生成器——紧凑的规格表经生成器展开成成千上万条
   微用例。这是本套件长到几万行量级的正道（见 §9 路线图）。
5. **数字要可复现**：预热 + 多轮重复，报 min / median / p95 与
   派生吞吐；结果同时出 JSON（ canonical ，供机器对照）、CSV、Markdown。
6. **基线是一等公民**：`compare` 模式与存档基线比 % 变化、超阈值
   标记并以非零退出码收尾，可直接做版本回归门。

## 3. 架构

```
cases/*.py          手写用例模块（每个分类一册，广度优先）
generators/*.py     规格表 -> 用例列表（矩阵展开 / 阶梯展开 / 语料生成）
        |
        v
benchsuite/model.py     Case / CaseResult 数据模型
benchsuite/compile.py   Case -> 脚本文本 / argv（占位符替换）
benchsuite/fixtures.py  主机侧 fixture 生成（@gen:lines:N 等）
benchsuite/runner.py    校验跑 -> 预热 -> 计时重复；loop 用例 autorange
benchsuite/report.py    JSON/CSV/MD 输出；基线对照；三档差距表
benchsuite/cli.py       list / run / compare / gap 四个子命令
        |
        v
results/                每次运行的三件套 + 差距表存档（基线进 git）
```

### 用例的三种执行形态（kind）

| kind | 形态 | 指标 |
|---|---|---|
| `loop` | body 被包进进程内计数循环跑 `iters` 次 | ns/op（中位数总时长 / iters） |
| `process` | 每次重复都以给定 argv 拉起 shell（启动族） | 每次启动墙钟 |
| `script` | setup+body 写成脚本文件跑一遍，`iters` = 脚本内处理的操作数（行/元素） | ns/op + ops/s |

### 计时与校验流程（每条用例）

1. 准备独立工作目录，物化 fixture 文件；
2. **校验跑**（不计时、捕获输出）：退出码 ≠ 期望或输出正则不符 →
   `verify-failed`，不计时——错误跑出的「快」不是数据；
3. loop 用例 **autorange**：探针跑一次，把 iters 放大到单次运行
   ≈200 ms（上限 ×1000），避免计时分辨率污染微用例；
4. 预热（默认 1 次）后计时重复（默认 5 次），逐次检查退出码。

### 统计口径

- 时钟：`time.perf_counter_ns()` 单调纳秒钟，包住子进程全程；
- 汇总：逐用例报 min / median / p95（重复序列）、中位数派生
  ns/op 与 ops/s；
- 环境：默认 `LC_ALL=C`（用例可覆盖），保证排序/区域口径确定；
- 公平性：同一语料、同一台机器、同一口径；结果元数据记录
  shell 版本串、平台、Python 版本、CPU 数、起始 loadavg——
  数字离开采集条件不可引用。

## 4. 分类学全图

覆盖原则：**先全后深**——每个角落先有至少一批用例（哪怕浅），
再按差距结果加深。当前 v1 共 16 类、409 条。

| 分类 | 覆盖面 | v1 条数 | 后续加深方向 |
|---|---|---|---|
| startup | 空跑 / `-c` 形态 / 脚本文件 / `--login` / `-i` / 大库 source | 10 | rc 文件规模阶梯、PATH 规模、环境变量规模 |
| parse | `-n` 纯解析语料（简单命令/函数/控制/展开/混合，生成器产 3000–5000 行） | 8 | 10k+ 行语料、深嵌套、长行、注释密度梯度 |
| expand | 参数展开全家：`${}` 全部形态（生成器矩阵 ~71 条）、tilde、brace（范围/笛卡尔/嵌套）、词分裂、嵌套替换 | 71+21 | 每种形态 × 字符串规模（短/中/长）全积 |
| arith | 运算符 × 上下文矩阵（`$(())` / `(())` / `let` / `for((;;))`）：30 算子 × 2 上下文 + 基数/大数/下标 | 67 | 位宽梯度、表达式深度、数组下标表达式面 |
| builtin | 逐个内建至少一行（生成器表 ~68 行）：echo/printf/read/test/declare/local/typeset/mapfile/readarray/cd/pwd/type/hash/jobs/wait/kill/ulimit/umask/shopt/set/export/unset/shift/getopts/eval/exec/command/builtin/alias/… | 68 | 每内建 × 参数形态（选项组合、参数个数阶梯） |
| strings | 字符串构建（+= / 拼接 / 50k 增长）、join、比较、模式匹配、`[[ =~ ]]` 与 BASH_REMATCH、填充格式化 | 18 | 长度阶梯（10/1k/100k 字符）全积、UTF-8 面 |
| arrays | 索引数组与关联数组：填/读/迭代/切片/拷贝删/`declare -p` 转储/稀疏/ 100k 追加 | 20 | 规模阶梯全积、嵌套与复合赋值形态 |
| control | if/elif/for/while/until/case（含 `;&` 落穿）/&&\|\|/取反/分组/子 shell 组/select/PIPESTATUS | 19 | 嵌套深度、分支分布（命中位置）梯度 |
| funcs | 函数调用：空/带参/local/返回码/shift/嵌套链/替换中调用/递归 fib/`declare -f`/`export -f` | 12 | 参数个数阶梯、局部变量层数、递归宽度 |
| subst | 命令替换（内建/外部/自拉起/嵌套/大输出）、反引号、进程替换（读/diff 形/双路）、子 shell | 14 | 捕获体积阶梯、嵌套深度、procsub 并发数 |
| redir | 重定向全形：/dev/null、追加、截断、2>&1、&>、heredoc（含展开）、herestring、fd 开关/复制、管线 2–3 段、10k 行过管 | 18 | fd 数量、管线深度、数据量阶梯 |
| glob | 路径展开：*/**/?/[]/extglob（含否定）、nullglob、点文件、300 项树 | 12 | 树规模阶梯（100/1万 文件）、深目录、排序口径 |
| cond | `[[ ]]` 全形：字符串/整数/文件/变量存在/选项/正则与模式的变量形；`[ ]` 的 -a/-o 组合 | 18 | 文件测试 × 文件系统状态、复合深度 |
| jobs | 后台+wait 扇出、`$!`、kill -TERM/-0、jobs/disown、trap 安装清除/USR1 投递/EXIT/DEBUG | 12 | 并发作业数阶梯、信号风暴、fg/bg 交互形（需 pty，后置） |
| data | 大数据阶梯（生成器：10/1k/100k 行 × 读循环/mapfile/字段切分/assoc 填/数组填）+ 批量输出/大转储/字符串与数组增长曲线 | 34 | 1M 行档、混合读写、二进制安全面 |
| mixed | 真实脚本形状：日志统计、配置解析、文件名变换、报表、状态机、字段手术、派发循环、参数解析 | 8 | 从真实脚本库采样扩充（每类 ≥5 个形状） |
| （交互相邻） | history/fc/compgen/complete 等非交互可测面（暂挂 builtin 类） | 含上 | pty 驱动的补全/历史专项（独立 harness，后置） |

分类学维护规则：bash 参考手册每出现一个可测构造，分类学必须有对应
行；暂时测不了的（需要 pty、需要真 Windows 句柄等）显式标注后置，
不许静默缺席。

## 5. 基线对照与回归门

```
python3 bench.py run --shell <new> --save-baseline base.json
python3 bench.py run --shell <new>            # 产出 new.json
python3 bench.py compare new.json --baseline base.json --threshold 5
```

- 逐用例比 ns/op 中位数，Δ% 超 +阈值标 `REGRESSION`、低于 -阈值标
  `IMPROVED`；有回归时退出码非零——可直接挂进 CI / 发版检查单；
- 基线 JSON 连同采集元数据（机器/版本/load）一起进 git 存档，
  换机器必须重采基线，禁止跨机器比数。

## 6. 差距表（三档）

`bench.py gap <subject.json> <reference.json>`：逐用例
ratio = subject 时间 / reference 时间（<1 表示 subject 更快），三档：

- **已领先**：ratio ≤ 0.98
- **接近**：0.98 < ratio ≤ 1.10
- **明显落后**：ratio > 1.10

附分类中位数汇总与落后项明细（最差在前）——这是优化排期的输入。

## 7. 跨平台方案

- **运行器层**：纯标准库 + `perf_counter_ns` 全平台一致；临时目录、
  路径拼接走 `os.path`；脚本文件统一写 `\n` 换行（被测 shell 均接受）。
- **Linux**：主战场，口径即本文件所述。
- **Windows**：被测对象为 rubash 原生构建（经 niubash 分发）与 Git Bash
  的 bash.exe；运行器用官方 Python for Windows 原样跑。注意点：
  进程创建成本口径不同（CreateProcess vs fork/exec），差距表必须
  同平台内比较；fixture 路径用相对路径避免盘符差异。
- **macOS**：系统自带 bash 3.2 仅作兼容性参照（不在超越目标内）；
  GNU bash 5.x 经 Homebrew 安装后同口径跑。
- **Android/Termux**：后置；运行器本身可跑，待 rubash 移动端构建
  就绪后接入同一语料（与 niu #352 的移动端矩阵呼应）。

## 8. 已知限制（v1）

1. 两 shell 顺序跑（先 A 全套、再 B 全套），机器状态漂移会影响
   对照——缓解：安静窗口采数、元数据记 load；根治在路线图
   （逐用例交错跑）。
2. 无 CPU 绑核/频率锁定（`taskset` 等属可选增强，跨平台口径不一，
   v1 不做，结果以中位数抗噪）。
3. process 族（spawn）的下限是 OS 进程创建成本，跨平台不可比，
   只做同平台内对照。
4. 交互路径（补全呈现、历史搜索）只测了非交互可达的部分，
   pty 专项后置。
5. Windows / macOS / Android 腿尚未实测——分类学与运行器已按
   跨平台写，数字待各平台窗口补。

## 9. 分期路线图（长到几万行的正道）

规模 = 生成器展开的乘积，不是手写行数。增长引擎有四个：

1. **矩阵补全**：展开式形态 × 字符串规模、内建 × 参数形态、
   运算符 × 表达式深度——现有三张规格表全积展开，量级 ×10；
2. **语料生成器**：解析语料从 5k 行长到 100k 行（参数化语法
   模板），数据阶梯加 1M 档；
3. **真实脚本采样**：从公开脚本与自家运维脚本中提炼 mixed 形状
   库，每形状多规模；
4. **差分语料回收**：正确线差分审计的用例语料（246+ 条及后续）
   性能无害的，自动转成 parse/expand 微用例——找茬线喂养基准线。

| 期 | 内容 | 量级目标 |
|---|---|---|
| P0（本期） | 运行器核心 + 分类学全图 + 广度语料 + 差距表 v1 | 409 条 / 16 类 |
| P1 | 逐用例交错对照、重复数自适应、CI 门接法文档；矩阵全积第一波 | ~2,000 条 |
| P2 | Windows 腿实测 + 语料生成器升级（100k 行解析语料、1M 数据档） | ~8,000 条 |
| P3 | mixed 形状库、历史趋势存档、多机基线库 | 10,000+ 条，语料与生成代码合计几万行 |

每期收尾都重采 GNU 基线并更新差距表；「明显落后」清单清零且
全表 ratio 中位数 < 1.00 之日，即「全面超越」达成之时——以本套件
的数字为准，不靠感觉。
