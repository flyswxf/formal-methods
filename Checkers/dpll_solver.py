import sys
import ast

def dpll(clauses, assignment):
    """
    DPLL 算法主过程
    :param clauses: CNF 子句集合 (例如: [[1, 2], [-1, 3]])
    :param assignment: 当前的变量赋值列表
    :return: (是否可满足, 最终赋值)
    """
    # 1. 单子句传播 (Unit Propagation)
    while True:
        unit_clauses = [c for c in clauses if len(c) == 1]
        if not unit_clauses:
            break
            
        unit = unit_clauses[0]
        literal = unit[0]
        assignment.append(literal)
        
        new_clauses = []
        for clause in clauses:
            if literal in clause:
                continue  # 该子句已经被满足
            if -literal in clause:
                # 移除相反的文字
                new_clause = [x for x in clause if x != -literal]
                if not new_clause:
                    # 产生了空子句，说明产生冲突，不可满足
                    return False, []
                new_clauses.append(new_clause)
            else:
                new_clauses.append(clause)
        clauses = new_clauses

    # 如果所有子句都被满足 (clauses 为空)
    if not clauses:
        return True, assignment
    
    # 如果存在空子句 (不可满足)
    if any(len(c) == 0 for c in clauses):
        return False, []

    # 2. 纯文字消除 (Pure Literal Elimination)
    # (此步骤可选，但能加速求解)
    literals = set(l for c in clauses for l in c)
    pure_literals = [l for l in literals if -l not in literals]
    for pure in pure_literals:
        assignment.append(pure)
        clauses = [c for c in clauses if pure not in c]

    if not clauses:
        return True, assignment
    if any(len(c) == 0 for c in clauses):
        return False, []

    # 3. 分支/分裂 (Branching/Splitting)
    # 选择一个尚未赋值的文字 (这里简单选择第一个子句的第一个文字)
    l = clauses[0][0]
    
    # 尝试将 l 赋值为 True
    # 相当于在子句集中加入单子句 [l]
    sat, final_assign = dpll(clauses + [[l]], list(assignment))
    if sat:
        return True, final_assign
        
    # 如果失败，则回溯，尝试将 l 赋值为 False (加入 [-l])
    return dpll(clauses + [[-l]], list(assignment))

if __name__ == "__main__":
    # 从标准输入读取数据集的一行输入
    input_data = sys.stdin.read().strip()
    if not input_data:
        sys.exit(0)
        
    try:
        # 假设输入是一个合法的 Python 列表字符串，如 "[[1, 2], [-1, 3]]"
        clauses = ast.literal_eval(input_data)
        if not isinstance(clauses, list):
            raise ValueError("Input is not a list")
            
        # 调用 DPLL 求解
        is_sat, _ = dpll(clauses, [])
        print("SAT" if is_sat else "UNSAT")
    except Exception as e:
        print(f"Error parsing input: {e}", file=sys.stderr)
        print("INVALID")
