# CDCL 求解器说明

本项目新增了一个基于 CDCL 思想实现的 SAT 求解器，输入格式为 DIMACS CNF，输出为：

- `SAT`
- `UNSAT`

## 文件结构

- `Checkers/cdcl_solver.py`
  - 命令行入口。
  - 支持两种输入：
    - 命令行参数：`python Checkers/cdcl_solver.py <dimacs文件>`
    - 标准输入：从 `stdin` 读取 DIMACS 文件路径（用于你的 `test_framework.py`）。

- `Checkers/cdcl/dimacs_parser.py`
  - Python DIMACS 解析器。
  - 支持 `c` 注释行、`p cnf` 头、以及子句以 `0` 结束。

- `Checkers/cdcl/dimacs_parser.hpp` / `dimacs_parser.cpp`
  - **C++ DIMACS 解析器**（阶段二产出），接口与 Python 版一致。
  - 返回 `CNFFormula` 结构体：`num_vars`、`num_clauses`、`clauses`。
  - 错误情况抛出 `DimacsParseError` 异常。

- `Checkers/cdcl/test_parser.cpp`
  - C++ 解析器测试套件，覆盖正常解析、边界情况和错误处理，共 48 项测试。
  - 编译命令：`g++ -std=c++17 -O2 -o Checkers/cdcl/test_parser.exe Checkers/cdcl/dimacs_parser.cpp Checkers/cdcl/test_parser.cpp`

- `Checkers/cdcl/solver.py`
  - CDCL 核心逻辑：
    - 单位传播（Unit Propagation）
    - 决策（Decision）
    - 冲突分析（Conflict Analysis）
    - 学习子句（Clause Learning）
    - 非顺序回溯（Backjumping）

- `Datasets/cdcl_dimacs/*.cnf`
  - DIMACS 测试样例（含 SAT 和 UNSAT）。

- `Datasets/cdcl_dataset.txt`
  - 供 `test_framework.py` 使用的数据集清单。
  - 格式为：`输入 :: 期望输出`，其中输入是 DIMACS 文件路径。

## 运行方式

### 1) 直接运行求解器

```bash
python Checkers/cdcl_solver.py Datasets/cdcl_dimacs/sat_01.cnf
```

### 2) 使用测试框架批量运行

```bash
python test_framework.py Checkers/cdcl_solver.py Datasets/cdcl_dataset.txt
```

## 说明

- 该实现强调可读性与教学用途，便于理解 CDCL 的关键流程。
- 对于你当前课程作业的中小规模样例可直接使用。
