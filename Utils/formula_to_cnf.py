import os
import argparse
from sympy.logic.boolalg import to_cnf
from sympy.parsing.sympy_parser import parse_expr

def convert_to_cnf(formula_str):
    """
    将任意布尔逻辑公式转换为 CNF 格式
    :param formula_str: 字符串形式的逻辑公式，必须使用 Sympy 支持的格式 (&, |, ~, >>, Equivalent)
    :return: 转换后的 CNF 表达式对象
    """
    try:
        from sympy import Equivalent
        # 直接解析表达式，不再进行任何字符串替换预处理
        expr = parse_expr(formula_str, evaluate=False, local_dict={"Equivalent": Equivalent})
        
        # 转换为 CNF
        cnf_expr = to_cnf(expr, simplify=True)
        return cnf_expr
    except Exception as e:
        print(f"Error parsing or converting formula '{formula_str}': {e}")
        return None

def format_cnf_to_list(cnf_expr):
    """
    将 sympy 的 CNF 表达式转换为类似 [[1, 2], [-1, 3]] 的整数列表格式
    这通常需要建立一个变量到整数的映射表
    :param cnf_expr: sympy 的 CNF 表达式
    :return: (列表格式的 CNF, 变量映射表)
    """
    from sympy.logic.boolalg import And, Or, Not
    from sympy import Symbol

    # 获取所有变量
    variables = list(cnf_expr.free_symbols)
    # 按变量名字母顺序排序，以保证结果稳定
    variables.sort(key=lambda x: x.name)
    
    # 建立变量名到正整数的映射
    var_map = {var.name: i+1 for i, var in enumerate(variables)}
    reverse_map = {i+1: var.name for i, var in enumerate(variables)}

    clauses = []
    
    # 处理单个文字、单个子句或多个子句的合取
    if isinstance(cnf_expr, And):
        args = cnf_expr.args
    else:
        args = [cnf_expr]

    for arg in args:
        clause = []
        if isinstance(arg, Or):
            lits = arg.args
        else:
            lits = [arg]
            
        for lit in lits:
            if isinstance(lit, Not):
                var_name = lit.args[0].name
                clause.append(-var_map[var_name])
            elif isinstance(lit, Symbol):
                var_name = lit.name
                clause.append(var_map[var_name])
            elif lit == True:
                 # True 意味着这个子句永远为真，可以忽略（但在标准 CNF 转换中通常不会出现单纯的 True 作为子句）
                 pass
            elif lit == False:
                 # False 意味着产生空子句
                 pass
        if clause:
            clauses.append(clause)

    return clauses, reverse_map

def main():
    parser = argparse.ArgumentParser(description="任意逻辑公式转换为 CNF 工具")
    parser.add_argument("-i", "--input", help="要转换的单个逻辑公式字符串")
    parser.add_argument("-f", "--file", help="包含多行逻辑公式的输入文件")
    parser.add_argument("-o", "--output", default=r"d:\HuaweiMoveData\Users\fengl\Desktop\作业\大三下\形式化\Datasets\converted_cnf.txt", help="输出文件路径")
    parser.add_argument("--format", choices=['raw', 'list'], default='list', help="输出格式：raw (Sympy表达式), list (整数列表)")

    args = parser.parse_args()

    formulas = []
    if args.input:
        formulas.append(args.input)
    
    if args.file:
        if os.path.exists(args.file):
            with open(args.file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        formulas.append(line)
        else:
            print(f"Error: Input file '{args.file}' not found.")

    if not formulas:
        print("Please provide an input formula via -i or an input file via -f.")
        return

    # 确保输出目录存在
    output_dir = os.path.dirname(args.output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(args.output, 'w', encoding='utf-8') as out_f:
        out_f.write("# Converted CNF Formulas\n")
        out_f.write(f"# Original Formulas -> Converted Output ({args.format} format)\n\n")
        
        for formula in formulas:
            cnf_expr = convert_to_cnf(formula)
            if cnf_expr is not None:
                if args.format == 'list':
                    list_cnf, var_map = format_cnf_to_list(cnf_expr)
                    map_str = ", ".join([f"{k}:{v}" for k, v in var_map.items()])
                    out_f.write(f"# Formula: {formula}\n")
                    out_f.write(f"# Var Map: {map_str}\n")
                    out_f.write(f"{list_cnf}\n\n")
                    print(f"Converted '{formula}' to List CNF successfully.")
                else:
                    out_f.write(f"# Formula: {formula}\n")
                    out_f.write(f"{cnf_expr}\n\n")
                    print(f"Converted '{formula}' to Raw CNF successfully.")

    print(f"\nConversion complete. Results saved to: {args.output}")

if __name__ == "__main__":
    main()
