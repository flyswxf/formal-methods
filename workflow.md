# 形式化方法 - DPLL自动化测试工作流

本文档介绍了用于验证 DPLL 求解器的自动化测试工作流。整个工作流由一个 PowerShell 脚本 `workflow.ps1` 串联，包含公式生成、CNF 转换、标准答案生成和最终的框架测试四个步骤。

## 🚀 快速开始

在项目根目录下，打开 PowerShell（或者 VS Code 终端），直接运行以下命令：

```powershell
.\workflow.ps1
```

你也可以通过参数自定义生成的测试公式数量，例如生成 500 条进行压力测试：
```powershell
.\workflow.ps1 -NumFormulas 500
```

## 🛠️ 工作流步骤及可调参数

整个工作流由四个子脚本依次执行，下面是它们的详细说明：

### 1. 逻辑公式生成 (`Utils/generate_large_formulas.py`)
- **功能**: 递归生成随机的、符合 Sympy 原生格式的布尔逻辑公式（包含 `~`, `&`, `|`, `>>`, `Equivalent` 等运算），并且为了防止与内置变量冲突，将变量统一为 `V1` 到 `V10`。
- **可调参数**:
  - `-n, --num`: 生成的独立公式数量（默认 `1500`）。在 `workflow.ps1` 中默认配置为 `100` 以便快速验证。
  - `-o, --output`: 输出文件路径。
- **工作流默认输出**: `Datasets/workflow_raw_formulas.txt`

### 2. 转换为 CNF (`Utils/formula_to_cnf.py`)
- **功能**: 读取上一步生成的随机逻辑公式，使用 Sympy 库将其化简并转化为 CNF（合取范式），最后输出为整数列表格式（例如 `[[1, 2], [-1, 3]]`）。
- **可调参数**:
  - `-f, --file`: 包含多行逻辑公式的输入文件。
  - `-i, --input`: 单个逻辑公式字符串输入（用于单独测试）。
  - `-o, --output`: 输出文件路径。
  - `--format`: 输出格式，可选 `raw` (Sympy表达式) 或 `list` (整数列表，默认)。
- **工作流默认输出**: `Datasets/workflow_converted_cnf.txt`

### 3. 生成标准测试集 (`Utils/generate_standard_sat.py`)
- **功能**: 读取整数列表格式的 CNF，调用工业级 SAT 求解器 `PySAT (Glucose3)` 来验证每个 CNF 的可满足性，将结果追加到每行末尾生成形如 `输入 :: SAT` 或 `输入 :: UNSAT` 的标准数据集。
- **可调参数**:
  - `-i, --input`: 输入的 CNF 列表文件。
  - `-o, --output`: 包含标准答案的数据集输出文件。
- **工作流默认输出**: `Datasets/workflow_dpll_dataset.txt`

### 4. 运行测试框架验证 (`test_framework.py` & `Checkers/dpll_solver.py`)
- **功能**: 测试框架读取标准测试集中的每一个测试用例，将 CNF 列表作为标准输入（`stdin`）传给你手写的 DPLL 求解器 (`Checkers/dpll_solver.py`)。比较手写求解器的输出结果与 PySAT 的标准结果，最终生成统计报告。
- **可调参数**:
  - `executable` (位置参数): 被测试程序的路径 (如 `Checkers/dpll_solver.py`)。
  - `dataset` (位置参数): 带有期望输出的标准测试集路径。
- **超时机制**: 测试框架内置了单次测试 5 秒的超时保护，防止你的求解器出现死循环。

## 📁 目录结构说明

- `Checkers/`: 存放各种可执行程序和求解器（如我们实现的 DPLL 算法 `dpll_solver.py`）。
- `Utils/`: 存放各个工具流脚本（公式生成、CNF转换、PySAT验证）。
- `Datasets/`: 存放所有中间生成的数据集和最终测试集。
- `test_framework.py`: 核心评测框架。
- `workflow.ps1`: 一键测试执行脚本。
