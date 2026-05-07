# SAT Solver Benchmark 使用说明

本文档说明如何使用当前仓库中的工具进行 SAT 求解器对比测试，主要包含：

- `benchmark_compare.py`
- MiniSat 编译与使用
- 自研 CDCL Solver 编译与使用

> 以下同时给出 **Windows** 和 **Linux (CentOS 7)** 的命令。

---

## 1. benchmark_compare.py 使用说明

脚本位置：`benchmark_compare.py`

功能：对比 **自研 CDCL Solver** 与 **MiniSat** 在同一组 DIMACS CNF 用例上的求解结果与耗时。

### 参数说明

```
python benchmark_compare.py --cdcl <cdcl可执行文件> --minisat <minisat可执行文件> --dataset <cnf目录> [选项]
```

必选参数：
- `--cdcl`：自研 CDCL Solver 可执行文件路径
- `--minisat`：MiniSat 可执行文件路径
- `--dataset`：包含 `.cnf` 文件的目录

可选参数：
- `--timeout`：单用例超时时间（秒），默认 300
- `--output`：结果输出为 JSON 文件路径

### 典型用法

**Windows：**

```powershell
python benchmark_compare.py --cdcl Checkers\build\cdcl_solver.exe --minisat Baseline\minisat\build\release\bin\minisat.exe --dataset Datasets\cdcl_dimacs\mini --timeout 60
```

```powershell
python benchmark_compare.py --cdcl Checkers\build\cdcl_solver.exe --minisat Baseline\minisat\build\release\bin\minisat.exe --dataset Datasets\cdcl_dimacs\mini --timeout 120 --output mini_results.json
```

**Linux：**

```bash
python3 benchmark_compare.py --cdcl Checkers/build/cdcl_solver --minisat Baseline/minisat/build/release/bin/minisat --dataset Datasets/cdcl_dimacs/mini --timeout 60
```

```bash
python3 benchmark_compare.py --cdcl Checkers/build/cdcl_solver --minisat Baseline/minisat/build/release/bin/minisat --dataset Datasets/cdcl_dimacs/mini --timeout 120 --output mini_results.json
```

### 输出结果说明

脚本会输出以下内容：

- 每个 `.cnf` 文件的求解结果
- CDCL / MiniSat 各自结果与耗时
- 结果是否一致（`OK` / `DIFF` / `N/A`）
- 汇总统计：
  - 总实例数
  - 一致数量
  - 不一致数量
  - 超时数量
  - CDCL / MiniSat 更快的次数
  - 总耗时与加速比

---

## 2. MiniSat 编译与使用

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

编译成功后，可执行文件路径：

- Windows：`Baseline/minisat/build/release/bin/minisat.exe`
- Linux：`Baseline/minisat/build/release/bin/minisat`

> MiniSat 编译需要 zlib。CentOS 7 如未安装：`sudo yum install -y zlib-devel gcc-c++ make`

### 使用方法

**Windows：**

```powershell
minisat.exe <input.cnf> <output.txt>
```

**Linux：**

```bash
./minisat <input.cnf> <output.txt>
```

- `input.cnf`：DIMACS 格式输入文件
- `output.txt`：求解结果输出文件

### 返回码

- `10`：SAT
- `20`：UNSAT

> `benchmark_compare.py` 中正是根据该返回码判断 MiniSat 求解结果。

---

## 3. 自研 CDCL Solver 编译与使用

自研 solver 源码位置：`Checkers/cdcl_solver.cpp`

入口逻辑读取一个 DIMACS CNF 文件，输出 `SAT` 或 `UNSAT`。

### 编译

**Windows（MinGW / MSYS2）：**

```powershell
mkdir Checkers\build
g++ -std=c++14 -O2 Checkers\cdcl_solver.cpp Checkers\cdcl\dimacs_parser.cpp Checkers\cdcl\cdcl_solver.cpp -o Checkers\build\cdcl_solver.exe
```

**Linux：**

```bash
mkdir -p Checkers/build
g++ -std=c++14 -O2 Checkers/cdcl_solver.cpp Checkers/cdcl/dimacs_parser.cpp Checkers/cdcl/cdcl_solver.cpp -o Checkers/build/cdcl_solver
```

> CentOS 7 默认 gcc 4.8.5 支持 `-std=c++14`，自研 solver 核心代码（`cdcl_solver.cpp`、`dimacs_parser.cpp`）不依赖 C++17，可以直接编译。
>
> 如果需要编译 `test_parser.cpp`（使用了 `std::filesystem`），则需要 C++17 支持，CentOS 7 需先安装较新版本的 gcc：
>
> ```bash
> sudo yum install -y centos-release-scl
> sudo yum install -y devtoolset-11-gcc-c++
> scl enable devtoolset-11 bash
> g++ -std=c++17 -O2 ...
> ```

### 使用方法

**Windows：**

```powershell
Checkers\build\cdcl_solver.exe <input.cnf>
```

**Linux：**

```bash
./Checkers/build/cdcl_solver <input.cnf>
```

### 输出结果

程序输出一个单词：

- `SAT`
- `UNSAT`

这与 `benchmark_compare.py` 对 CDCL Solver 的调用逻辑一致。

---

## 4. 快速完整流程

### 4.1 编译 MiniSat

**Windows：**

```powershell
cd Baseline\minisat
make r
cd ..\..
```

**Linux：**

```bash
cd Baseline/minisat
make r
cd ../..
```

### 4.2 编译自研 CDCL Solver

**Windows：**

```powershell
mkdir Checkers\build
g++ -std=c++14 -O2 Checkers\cdcl_solver.cpp Checkers\cdcl\dimacs_parser.cpp Checkers\cdcl\cdcl_solver.cpp -o Checkers\build\cdcl_solver.exe
```

**Linux：**

```bash
mkdir -p Checkers/build
g++ -std=c++14 -O2 Checkers/cdcl_solver.cpp Checkers/cdcl/dimacs_parser.cpp Checkers/cdcl/cdcl_solver.cpp -o Checkers/build/cdcl_solver
```

### 4.3 运行对比 benchmark

**Windows：**

```powershell
python benchmark_compare.py --cdcl Checkers\build\cdcl_solver.exe --minisat Baseline\minisat\build\release\bin\minisat.exe --dataset Datasets\cdcl_dimacs\mini --timeout 120 --output mini_results.json
```

**Linux：**

```bash
python3 benchmark_compare.py --cdcl Checkers/build/cdcl_solver --minisat Baseline/minisat/build/release/bin/minisat --dataset Datasets/cdcl_dimacs/mini --timeout 120 --output mini_results.json
```

---

## 5. CentOS 7 环境准备

在 CentOS 7 服务器上首次运行前，需要安装编译工具和依赖：

```bash
sudo yum install -y gcc-c++ make zlib-devel python3
```

如需 C++17 支持（编译 `test_parser.cpp` 等）：

```bash
sudo yum install -y centos-release-scl
sudo yum install -y devtoolset-11-gcc-c++
scl enable devtoolset-11 bash
```

---

## 6. 注意事项

- Windows 下 `benchmark_compare.py` 调用 `minisat.exe` 时会额外将 `D:\strawberry\c\bin` 加入 PATH，这是 Windows 特有的兼容逻辑，Linux 下无影响。
- 若编译后的可执行文件路径不同，请按实际路径修改命令。
- 若 `dataset` 目录下没有 `.cnf` 文件，脚本会直接报错退出。
