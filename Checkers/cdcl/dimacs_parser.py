from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CNFFormula:
    num_vars: int
    clauses: list[list[int]]


def parse_dimacs_file(file_path: str) -> CNFFormula:
    clauses: list[list[int]] = []
    num_vars = 0
    header_seen = False
    pending_clause: list[int] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip().lstrip("\ufeff")
            if not line or line.startswith("c"):
                continue

            if line.startswith("p"):
                parts = line.split()
                if len(parts) < 4 or parts[1] != "cnf":
                    raise ValueError("DIMACS 头格式错误，期望: p cnf <num_vars> <num_clauses>")
                num_vars = int(parts[2])
                header_seen = True
                continue

            for token in line.split():
                lit = int(token)
                if lit == 0:
                    if not pending_clause:
                        raise ValueError("检测到空子句，公式不可满足。")
                    clauses.append(pending_clause)
                    pending_clause = []
                else:
                    pending_clause.append(lit)

    if not header_seen:
        raise ValueError("缺少 DIMACS 头: p cnf <num_vars> <num_clauses>")
    if pending_clause:
        raise ValueError("存在未以 0 结束的子句。")

    return CNFFormula(num_vars=num_vars, clauses=clauses)
