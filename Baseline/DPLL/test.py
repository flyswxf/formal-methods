from pathlib import Path
from solve import *

def run_file(file_name, sat):
    print(file_name)
    clauses, nvars = parse_problem(file_name)
    dpll = DPLL(clauses, nvars)
    result = dpll.run()
    print(result)
    assert(result.sat == sat)
    if sat:
        # Verify the solution
        for clause in clauses:
            success = False
            for literal in clause.inner:
                if (literal in result.sol):
                    success = True
                    break
            if not success:
                assert(False)
    

def run_dir(dir_name, sat):
    bench_dir = Path(dir_name)

    for file in bench_dir.iterdir():
        run_file(file, sat)

run_file("cnfs/6_SAT.cnf", True)
run_file("cnfs/7_UNSAT.cnf", False)
run_file("cnfs/8_UNSAT.cnf", False)
run_file("cnfs/9_SAT.cnf", True)
run_dir("uf20-91", True)
run_dir("uuf50-218", False)
# run_dir("uf250-1065", True)