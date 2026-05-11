# CDCL SAT Solver — 设计、实现与大规模基准评测

基于 C++ 实现的完整 CDCL（Conflict-Driven Clause Learning）SAT 求解器，与工业级求解器 MiniSat 在 **7350+** 公开测试实例上进行了正确性与性能对比。

---

## 项目结构

```
formal-methods/
├── Checkers/                         # 自研求解器
│   ├── cdcl/                         #   C++ CDCL 核心库
│   │   ├── cdcl_solver.hpp
│   │   ├── cdcl_solver.cpp           #     BCP / 1UIP / VSIDS / 回溯
│   │   ├── dimacs_parser.hpp
│   │   ├── dimacs_parser.cpp         #     DIMACS CNF 解析器
│   │   └── dimacs_parser.py          #     Python 版解析器
│   ├── cdcl_solver.cpp              #   main() 入口
│   ├── cdcl_solver                  #   编译产物（二进制）
│   └── dpll_solver.py               #   DPLL 参考实现
├── Baseline/
│   └── minisat/                      # MiniSat 对比基准（C++）
├── benchmark_compare.py              # 并行评测框架
├── run_cdcl_bench_multinode.sbatch   # SLURM 多节点模板
├── Utils/                            # 自动化脚本
│   ├── download_satlib.sh            #   下载 SATLIB 数据集
│   ├── strip_dimacs_trailer.sh       #   清理 cnf 尾部 % 0
│   ├── batch_submit_bench.sh         #   批量生成 sbatch 并提交
│   ├── merge_shard_results.py        #   合并分片 → detail.json / result.out
│   └── cdcl_random_sanity.py         #   随机小实例暴力枚举自检
├── Datasets/cdcl_dimacs/
│   ├── medium/                       # SATLIB 数据集（10 组，6400 实例）
│   │   ├── uf20-91/SAT/
│   │   ├── uf50-218/{SAT,UNSAT}/
│   │   └── ...
│   └── large/                        # SAT Competition 2021-2023（951 实例）
│       ├── cnfs/{2021,2022,2023}/
│       └── download_small.ps1        #   下载 + 按文件大小过滤
├── Logs/                             # 实验结果
│   ├── medium-uf50-218-SAT/          #   {meta.json, detail.json, result.out, info.out}
│   ├── ...
│   └── large-2023/
├── Knowledge/                        # 实验报告
│   ├── report.tex                    #   LaTeX 源文件
│   ├── report.pdf                    #   编译产物
│   ├── analyze_results.py            #   结果统计 + 图表
│   ├── plot_datasets.py              #   数据集分布图
│   └── images/                       #   配图
└── .gitignore
```

---

## 编译 & 运行

### 编译 CDCL 求解器

```bash
cd Checkers/cdcl
g++ -std=c++17 -O3 -o ../cdcl_solver cdcl_solver.cpp dimacs_parser.cpp
```

### 编译 MiniSat

```bash
cd Baseline/minisat
make config prefix=$PWD/build
make install
# 二进制位于 build/bin/minisat
```

### 单个实例求解

```bash
./Checkers/cdcl_solver Datasets/cdcl_dimacs/medium/uf50-218/SAT/uf50-01.cnf
# 输出: SAT 或 UNSAT
```

---

## 实验复现

### 1. 下载数据集

```bash
# SATLIB 均匀随机 3-SAT（10 组）
bash Utils/download_satlib.sh

# 清理 SATLIB 尾部 % 0（兼容 MiniSat）
bash Utils/strip_dimacs_trailer.sh Datasets/cdcl_dimacs/medium

# SAT Competition 2021-2023（PowerShell）
cd Datasets/cdcl_dimacs/large
./download_small.ps1 -Year 2021
./download_small.ps1 -Year 2022
./download_small.ps1 -Year 2023
# 解压 .xz 文件: bash unpack_xz.sh
```

### 2. 提交批量对比实验（SLURM 集群）

```bash
# 编辑 Utils/batch_submit_bench.sh 中的 TASKS 数组（增删需要跑的 benchmark）
# 串行提交（推荐，避免超 CPU 配额）
bash Utils/batch_submit_bench.sh --serial --max-nodes 16

# 或并行提交所有任务
bash Utils/batch_submit_bench.sh
```

提交后每个任务自动：
1. 在 `Logs/<JOB_ID>/` 下创建独立目录
2. 按 shard 并行运行 `benchmark_compare.py`（CDCL + MiniSat 同实例对比）
3. 调用 `merge_shard_results.py` 合并分片 JSON → `detail.json` + `result.out`

### 3. 查看结果

```bash
# 单任务可读报告
cat Logs/<TASK_NAME>/result.out

# 全量 JSON 数据
cat Logs/<TASK_NAME>/detail.json

# 批量统计 + 图表
cd Knowledge
python analyze_results.py     # 扫描所有 Logs/*/result.out 生成统计 + 图表
```

### 4. 随机一致性自检（小规模验证）

```bash
python Utils/cdcl_random_sanity.py --cdcl Checkers/cdcl_solver --cases 1000 --max-vars 10
```

---

## 核心算法特性

| 特性       | 实现                                                         |
| ---------- | ------------------------------------------------------------ |
| BCP        | 二阶监视文字法（Two-Watched Literals）+ compact 双指针       |
| 冲突分析   | 1UIP 学习（First Unique Implication Point）                  |
| 回溯       | 非时序回溯（Non-chronological Backtracking）                 |
| 决策启发   | VSIDS（Variable State Independent Decaying Sum）+ 二叉小顶堆 |
| 子句管理   | 原始子句与学习子句共存，`clause_db` 统一索引                 |
| 文字编码   | 2-Split 编码（`2x` / `2x+1`），取反用异或                    |
| 运行时自检 | `CDCL_SELF_CHECK=1` 启用，周期性验证 trail / watches 不变量  |

---

## 实验结果摘要（7350 实例）

| 指标                       | 结果                     |
| -------------------------- | ------------------------ |
| 正确性分歧（DIFF）         | **0**                    |
| SATLIB 一致（OK）          | 6298 / 6399              |
| SATCOMP 一致（OK）         | 35 / 951（631 双方超时） |
| SATLIB MiniSat/CDCL 加速比 | 约 85×（累计时间）       |
| MiniSat 零超时范围         | 变量 ≤ 250 全部完成      |

详细图表与分析见 `Knowledge/report.pdf`。
