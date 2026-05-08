# SAT Solver Benchmark 与 CDCL 自检使用说明

本文档说明如何使用仓库中的工具进行 SAT 求解器对比与自检，主要包含：

- `benchmark_compare.py`
- `Utils/cdcl_random_sanity.py`（随机一致性对拍组件）
- MiniSat 编译与使用
- 自研 C++ CDCL Solver 编译与使用（含模块级断言自检）

> 默认推荐 `--timeout 300`，对中大规模实例更稳妥。

***

## 1. benchmark\_compare.py 使用说明

脚本位置：`benchmark_compare.py`

功能：对比 **自研 CDCL Solver** 与 **MiniSat** 在同一组 DIMACS CNF 上的求解结果与耗时。

### 参数说明

```bash
python benchmark_compare.py --cdcl <cdcl可执行文件> --minisat <minisat可执行文件> --dataset <cnf目录> [选项]
```

必选参数：

- `--cdcl`：自研 CDCL Solver 可执行文件路径
- `--minisat`：MiniSat 可执行文件路径
- `--dataset`：包含 `.cnf` 文件的目录

可选参数：

- `--timeout`：单用例超时时间（秒），默认 `300`
- `--output`：结果输出为 JSON 文件路径

### 典型用法

**Windows：**

```powershell
python benchmark_compare.py --cdcl Checkers\cdcl_solver.exe --minisat Baseline\minisat\build\minisat.exe --dataset Datasets\cdcl_dimacs\large\mini --timeout 300
```

```powershell
python benchmark_compare.py --cdcl Checkers\cdcl_solver.exe --minisat Baseline\minisat\build\minisat.exe --dataset Datasets\cdcl_dimacs\large\mini --timeout 300 --output mini_results.json
```

**Linux：**

```bash
python3 benchmark_compare.py --cdcl Checkers/cdcl_solver --minisat Baseline/minisat/build/release/bin/minisat --dataset Datasets/cdcl_dimacs/large/mini --timeout 300
```

```bash
python3 benchmark_compare.py --cdcl Checkers/cdcl_solver --minisat Baseline/minisat/build/release/bin/minisat --dataset Datasets/cdcl_dimacs/large/mini --timeout 300 --output mini_results.json
```

### 输出结果说明

脚本输出：

- 每个 `.cnf` 文件的求解结果
- CDCL / MiniSat 各自耗时
- 一致性标记（`OK` / `DIFF` / `N/A`）
- 汇总统计（总实例数、一致/不一致、超时、快慢次数、总耗时、加速比）

***

## 2. 随机一致性自检组件（Utils）

脚本位置：`Utils/cdcl_random_sanity.py`

功能：随机生成小规模 CNF，用**暴力枚举真值**作为基准，和你的 CDCL 结果对拍。\
用途：在没有公开大测试集时，快速发现实现级 bug（错误 SAT/UNSAT）。

### 典型用法

**Windows / Linux：**

```bash
python Utils/cdcl_random_sanity.py --cdcl Checkers/cdcl_solver.exe --cases 1000 --max-vars 10 --max-clauses 30 --timeout 10
```

可选参数（常用）：

- `--cases`：随机用例数量（默认 1000）
- `--max-vars`：最大变量数（默认 10）
- `--max-clauses`：最大子句数（默认 30）
- `--max-clause-len`：最大子句长度（默认 5）
- `--seed`：随机种子（默认 0，表示随机）
- `--timeout`：单用例超时（秒）

***

## 3. MiniSat 编译与使用

MiniSat 源码位置：`Baseline/minisat`

### 编译

**Windows（MinGW / MSYS2）：**

```powershell
cd Baseline\minisat
make r
```

**Linux：**

```bash
cd Baseline/minisat
make r
```

编译产物路径：

- Windows：`Baseline/minisat/build/minisat.exe`
- Linux：`Baseline/minisat/build/release/bin/minisat`

### 使用方法

```bash
minisat <input.cnf> <output.txt>
```

返回码：

- `10`：SAT
- `20`：UNSAT

***

## 4. 自研 C++ CDCL Solver 编译与使用

源码位置：

- 入口：`Checkers/cdcl_solver.cpp`
- 核心：`Checkers/cdcl/cdcl_solver.cpp`
- 解析器：`Checkers/cdcl/dimacs_parser.cpp`

### 编译

**Windows：**

```powershell
g++ -std=c++17 -O2 Checkers\cdcl_solver.cpp Checkers\cdcl\dimacs_parser.cpp Checkers\cdcl\cdcl_solver.cpp -o Checkers\cdcl_solver.exe
```

**Linux：**

```bash
g++ -std=c++17 -O2 Checkers/cdcl_solver.cpp Checkers/cdcl/dimacs_parser.cpp Checkers/cdcl/cdcl_solver.cpp -o Checkers/cdcl_solver
```

### 运行

```bash
Checkers/cdcl_solver.exe <input.cnf>
```

输出：

- `SAT`
- `UNSAT`

***

## 5. 模块级断言自检（大实例排查）

`cdcl_solver.cpp` 内置了“模块级断言自检”开关，默认关闭。\
开启后会检查 `enqueue / propagate / analyze / cancel_until / watcher引用` 等关键状态一致性。

### 启用方式（PowerShell）

```powershell
$env:CDCL_SELF_CHECK='1'
$env:CDCL_SELF_CHECK_INTERVAL='20000'
```

说明：

- `CDCL_SELF_CHECK=1`：开启自检
- `CDCL_SELF_CHECK_INTERVAL`：每隔多少次事件做一次 watcher 采样检查（正整数）
- 建议大实例从 `20000` 开始，若要更激进可调小（会更慢）

若触发异常，会输出类似：

```text
[CDCL_SELF_CHECK][模块名] 错误信息
```

并立即中止，便于定位状态不一致源头。

***

## 6. 快速完整流程（推荐）

### 6.1 编译 MiniSat

```bash
module load compiler/gnu/10.2.0
cd Baseline/minisat
make r
cd ../..
```

### 6.2 编译 CDCL Solver

```bash
g++ -std=c++17 -O2 Checkers/cdcl_solver.cpp Checkers/cdcl/dimacs_parser.cpp Checkers/cdcl/cdcl_solver.cpp -o Checkers/cdcl_solver
```

### 6.3 先跑随机一致性自检

```bash
python3 Utils/cdcl_random_sanity.py --cdcl Checkers/cdcl_solver --cases 1000 --max-vars 10 --max-clauses 30 --timeout 10
```

### 6.4申请独占节点资源

```bash
# 申请1个完整节点，独占32核128G内存，时长按需调整（示例4小时）
salloc --exclusive -N 1 -n 1 --cpus-per-task=32 --mem=100G -t 4:00:00
```

- `--exclusive`：**核心参数**，独占整个节点，不与其他用户共享，避免CPU争抢，性能最稳定
- `-N 1`：固定1个节点（单线程SAT跨节点无意义）
- `--cpus-per-task=32`：匹配节点全部32个物理核
- `--mem=100G`：匹配节点全部内存，避免OOM
- `-t 4:00:00`：运行时长，格式`小时:分钟:秒`，按需修改（比如跑大规模实验可以设`24:00:00`）

申请成功后，登录到计算节点：

```bash
srun --pty --cpu-bind=cores bash
```

- `--cpu-bind=cores`：CPU绑定，避免进程上下文切换，大幅提升CPU密集型任务的性能

### 6.5 额外：非交互提交（sbatch）

项目根目录已提供脚本：`run_cdcl_bench.sbatch`。提交命令：

```bash
sbatch run_cdcl_bench.sbatch
```

可选查看任务状态：

```bash
squeue -u $USER
```

### 6.6 再跑 MiniSat 对比基准（timeout=300）

```bash
python3 benchmark_compare.py --cdcl Checkers/cdcl_solver --minisat Baseline/minisat/build/release/bin/minisat --dataset Datasets/cdcl_dimacs/large/cnfs --timeout 300 --output bench_results.json
```

## 7. 注意事项

- Windows 下 `benchmark_compare.py` 会尝试把 `D:\strawberry\c\bin` 加入 `PATH`，用于兼容部分 `minisat.exe` 运行环境。
- `dataset` 目录必须直接包含 `.cnf` 文件；若为空会直接报错退出。
- 若你使用的是超大实例，建议先关自检跑性能，再开自检定位一致性问题。
