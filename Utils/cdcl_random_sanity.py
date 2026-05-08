import argparse
import itertools
import os
import random
import subprocess
import tempfile
from typing import List


def brute_force_result(num_vars: int, clauses: List[List[int]]) -> str:
    for bits in itertools.product([False, True], repeat=num_vars):
        sat = True
        for clause in clauses:
            clause_sat = False
            for lit in clause:
                v = abs(lit) - 1
                val = bits[v]
                if (lit > 0 and val) or (lit < 0 and (not val)):
                    clause_sat = True
                    break
            if not clause_sat:
                sat = False
                break
        if sat:
            return "SAT"
    return "UNSAT"


def run_solver(exe_path: str, cnf_path: str, timeout: int) -> str:
    proc = subprocess.run([exe_path, cnf_path], capture_output=True, timeout=timeout)
    out = proc.stdout.decode("utf-8", errors="replace").strip()
    if out.startswith("SAT"):
        return "SAT"
    if out.startswith("UNSAT"):
        return "UNSAT"
    return f"ERROR({out[:80]})"


def make_random_cnf(num_vars: int, num_clauses: int, max_clause_len: int) -> List[List[int]]:
    clauses: List[List[int]] = []
    for _ in range(num_clauses):
        k = random.randint(1, min(max_clause_len, num_vars))
        vars_sample = random.sample(range(1, num_vars + 1), k=k)
        clause = [v if random.random() < 0.5 else -v for v in vars_sample]
        clauses.append(clause)
    return clauses


def write_dimacs(path: str, num_vars: int, clauses: List[List[int]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for c in clauses:
            f.write(" ".join(map(str, c)) + " 0\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="随机生成小规模 CNF，用暴力枚举对 CDCL 结果做一致性自检。"
    )
    parser.add_argument("--cdcl", required=True, help="cdcl_solver.exe 路径")
    parser.add_argument("--cases", type=int, default=1000, help="随机用例数量")
    parser.add_argument("--max-vars", type=int, default=10, help="最大变量数")
    parser.add_argument("--max-clauses", type=int, default=30, help="最大子句数")
    parser.add_argument("--max-clause-len", type=int, default=5, help="最大子句长度")
    parser.add_argument("--seed", type=int, default=0, help="随机种子，0 表示系统随机")
    parser.add_argument("--timeout", type=int, default=10, help="单个用例超时秒数")
    args = parser.parse_args()

    if args.seed != 0:
        random.seed(args.seed)

    cdcl_path = os.path.abspath(args.cdcl)
    if not os.path.exists(cdcl_path):
        print(f"[ERROR] CDCL 不存在: {cdcl_path}")
        return 2

    for i in range(1, args.cases + 1):
        n = random.randint(1, args.max_vars)
        m = random.randint(1, args.max_clauses)
        clauses = make_random_cnf(n, m, args.max_clause_len)
        expect = brute_force_result(n, clauses)

        with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False) as tf:
            tmp_path = tf.name
        try:
            write_dimacs(tmp_path, n, clauses)
            got = run_solver(cdcl_path, tmp_path, args.timeout)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        if got != expect:
            print(f"[MISMATCH] case={i} expect={expect} got={got}")
            print(f"[DETAIL] vars={n} clauses={m}")
            print(f"[CNF] {clauses}")
            return 1

        if i % 100 == 0 or i == args.cases:
            print(f"[OK] {i}/{args.cases}")

    print("[PASS] 所有随机用例一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
