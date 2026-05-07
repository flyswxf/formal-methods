# 形式化课程作业 - CDCL 求解器实现

## 📋 作业要求
根据课堂板书，本次大作业的核心目标是**实现一个 CDCL 求解器**。
具体要求如下：
1. **输入与输出**：输入 DIMACS 格式文件，输出 SAT 或 UNSAT（若是 SAT 需给出具体的一组解）。
2. **辅助工具**：允许使用大模型（如 ChatGPT、Claude 等）辅助完成代码或理解算法。
3. **测试规模**：测试集规模**不少于 1000 个**，测试用例可以参考往年的 **SAT 竞赛 (Google 搜索 SAT Competition)**。
4. **性能与正确性比较**：需要将自己实现的求解器与开源的 **Minisat** (C/C++) 进行性能（求解时间、内存）和正确性的比较。

---

## 📚 核心概念解析

### 1. 什么是 SAT？
**SAT (Boolean Satisfiability Problem, 布尔可满足性问题)** 是计算机科学中第一个被证明为 **NP-完全 (NP-Complete)** 的问题。
它的核心是：给定一个布尔公式（通常以合取范式 CNF 表示），问是否存在一组对变量的真值赋值（True/False），使得整个公式的计算结果为 True。
*   如果存在这样的赋值，则称该公式是 **可满足的 (SAT)**。
*   如果无论怎么赋值都无法让公式为 True，则称其为 **不可满足的 (UNSAT)**。

### 2. CDCL 求解器是干嘛的？
**CDCL (Conflict-Driven Clause Learning, 冲突驱动子句学习)** 是现代 SAT 求解器中最核心、最高效的算法架构。
它在早期的 DPLL（回溯搜索）算法基础上，加入了**“从错误中学习”**的机制。
*   **Conflict-Driven (冲突驱动)**：当搜索过程中发生逻辑冲突（即某条规则被打破，发现当前赋值走进了死胡同）时，触发分析。
*   **Clause Learning (子句学习)**：通过分析冲突图（Implication Graph），找出导致冲突的根本原因，并将其转化为一个新的约束条件（子句）加入到原来的公式中。这样求解器在未来的搜索中就**永远不会再犯同样的错误**。
*   **Non-chronological Backtracking (非时序回溯/回跳)**：发生冲突后，不仅回溯一步，而是直接跳回导致冲突的那个更早的决策层，大幅度剪枝搜索树。

### 3. SAT 竞赛网址在哪？
SAT 竞赛（SAT Competition）是全球顶级的 SAT 求解器年度比赛，提供了大量高质量、不同难度的工业界和学术界测试集。
*   **官方主页**：[http://www.satcompetition.org/](http://www.satcompetition.org/)
*   **往届测试用例下载**：你可以进入历年（例如 2022, 2023）的比赛页面，寻找 "Benchmarks" 下载链接。这些 benchmark 包含海量的 DIMACS 格式文件，足够你挑选出 1000 个测试集。

### 4. Minisat 是什么？怎么下载和使用？
**Minisat** 是一个极简、开源且高度优化的 CDCL SAT 求解器，由 C++ 编写。由于其代码结构清晰、性能强悍，它被广泛作为现代 SAT 求解器的教学参考和 Baseline（基线标准）。

**如何下载与编译 (Linux/WSL 推荐):**
```bash
# Ubuntu/Debian 系统可以直接通过包管理器安装：
sudo apt update
sudo apt install minisat

# 或者从 GitHub 源码编译：
git clone https://github.com/niklasso/minisat.git
cd minisat
make
```

**如何使用:**
命令格式：`minisat [输入文件.cnf] [输出文件.txt]`
```bash
# 运行 minisat，并将结果保存到 result.txt 中
minisat test.cnf result.txt
```
查看 `result.txt`，第一行会显示 `SAT` 或 `UNSAT`，如果为 `SAT`，第二行会列出满足条件的变量赋值（以 0 结尾）。

### 5. DIMACS 文件是什么？
**DIMACS** 是表示 SAT 问题（特别是合取范式 CNF）的标准文本文件格式。几乎所有的 SAT 求解器和竞赛都使用这种格式。

**DIMACS 格式规则示例：**
```text
c 这是一行注释
c 变量有 3 个 (1, 2, 3)，子句有 2 个
p cnf 3 2
1 -3 0
2 3 -1 0
```
*   `c` 开头的是注释行。
*   `p cnf <变量总数> <子句总数>` 是声明行。表示这是一个 CNF 公式。
*   接下来的每一行代表一个**子句 (Clause)**。
    *   正数代表变量本身（如 `1` 代表变量 $x_1$）。
    *   负数代表变量的非（如 `-3` 代表 $\neg x_3$）。
    *   每行必须以 `0` 结尾，代表这个子句结束。
*   **逻辑含义**：上面的文件等价于逻辑公式：$(x_1 \lor \neg x_3) \land (x_2 \lor x_3 \lor \neg x_1)$。

---

## 🚀 从零开始学习与工作流指南

### 阶段一：理论储备 (Week 1)
1.  **复习命题逻辑与 CNF**：确保你完全理解变量、文字 (Literal)、子句 (Clause)、合取范式 (CNF) 的概念。
2.  **理解 DPLL 算法**：
    *   **BCP (Boolean Constraint Propagation, 布尔约束传播)**：也就是单文字规则 (Unit Rule)，这是 SAT 求解器的核心引擎。
    *   **纯文字规则 (Pure Literal)** 与 **分支决策 (Branching/Deciding)**。
3.  **攻克 CDCL 核心机制**：
    *   **蕴含图 (Implication Graph)**：如何画图记录变量赋值的因果关系。
    *   **UIP (Unique Implication Point, 唯一蕴含点)**，特别是 **1UIP**：这是学习新子句的切割点。
    *   **非时序回溯 (Backjumping)**：如何计算该回退到哪一层。
    *   推荐阅读：*Conflict-Driven Clause Learning SAT Solvers* (相关论文或知乎通俗讲解)。

### 阶段二：基建与解析器实现 (Week 2)
1.  **语言选择**：推荐使用 C++（性能好，方便和 Minisat 比较）或 Rust。如果只求实现，Python 也可以，但性能比 C++ 差很多。
2.  **编写 DIMACS 解析器**：
    *   写一个函数，读取 `.cnf` 文件，过滤掉 `c` 开头的注释。
    *   解析 `p cnf` 行获取规模，申请数据结构（例如二维数组或 `vector<vector<int>>` 存子句）。
3.  **跑通 Minisat**：
    *   在本地配置好 Minisat，手动写几个极其简单的 DIMACS 文件扔给 Minisat 跑，熟悉它的输入输出。

### 阶段三：核心算法编码 (Week 3)
1.  **数据结构设计**：
    *   变量状态表（当前值是 True/False/未分配，当前处于第几个决策层，它的先决条件是从哪个子句推导出来的）。
    *   **Two-Watched Literals (双监视文字)**：这是 BCP 的加速黑科技，务必学习并实现，否则面对上千变量的题会慢死。
2.  **实现核心循环**：
    ```text
    while (未找到解):
        if (BCP() 产生冲突):
            if (当前决策层 == 0): return UNSAT
            学习新子句 (Analyze Conflict)
            回溯 (Backjump)
        else:
            if (所有变量都赋值了): return SAT
            做决定 (Make a Decision / 启发式选取下一个变量)
    ```
3.  **实现 VSIDS 启发式分支**（可选但强烈建议）：一种根据变量在冲突中出现频率来决定优先给谁赋值的策略。

### 阶段四：测试与性能比较 (Week 4)
1.  **构建测试集 (1000+)**：
    *   从 SAT Competition 下载测试集。
    *   编写 Python 脚本自动随机抽取 1000 个规模适中的 `.cnf` 文件存入 `test_cases` 文件夹。
2.  **编写自动化评测脚本**：
    *   使用 Python 的 `subprocess` 模块。
    *   对于每个 `.cnf` 文件，分别调用 `你的求解器` 和 `minisat`。
    *   记录两者的：1. 输出结果 (SAT/UNSAT 必须完全一致) 2. 运行耗时。
    *   注意设置 **Timeout (超时时间)**，比如每个 case 限制 60 秒，防止死循环。
3.  **整理实验报告**：
    *   将 Python 跑出的对比数据导出为 CSV 或画成折线图/散点图。
    *   分析你的求解器在哪些用例上比 Minisat 慢（通常是 BCP 不够优化，或者没有实现 Restart 机制）。

> [!tip] 提示
> 如果时间紧迫，可以先实现一个不带 1UIP 优化的基础 DPLL，然后再逐步加入 CDCL 的冲突图分析机制。利用大模型（如 ChatGPT）时，可以让它帮你**编写 Two-Watched Literals 的代码骨架**，或者**解释 1UIP 的寻找过程**，这能省下大量时间。
