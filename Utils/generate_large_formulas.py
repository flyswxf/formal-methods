import random
import os

VARIABLES = ['V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10']
BINARY_OPS = ['&', '|', '>>']

def generate_expression(depth=0, max_depth=3):
    """递归生成符合 Sympy 原生格式的随机逻辑表达式"""
    # 达到最大深度，或者随机决定作为叶子节点，返回一个变量
    if depth >= max_depth or (depth > 0 and random.random() < 0.4):
        return random.choice(VARIABLES)
    
    # 随机选择操作类型：一元运算(~)、二元运算(&, |, >>) 或 等价运算(Equivalent)
    op_type = random.choices(['unary', 'binary', 'equivalent'], weights=[0.2, 0.6, 0.2])[0]
    
    if op_type == 'unary':
        inner = generate_expression(depth + 1, max_depth)
        # 避免连续多次取反，例如 ~~A
        if inner.startswith('~'):
            return inner[1:] if inner.startswith('~(') else inner
        return f"~({inner})" if len(inner) > 1 else f"~{inner}"
        
    elif op_type == 'binary':
        left = generate_expression(depth + 1, max_depth)
        right = generate_expression(depth + 1, max_depth)
        op = random.choice(BINARY_OPS)
        return f"({left} {op} {right})"
        
    elif op_type == 'equivalent':
        left = generate_expression(depth + 1, max_depth)
        right = generate_expression(depth + 1, max_depth)
        return f"Equivalent({left}, {right})"

def generate_dataset(output_path, num_formulas=1500):
    """生成指定数量的不重复逻辑公式并写入文件"""
    print(f"开始生成 {num_formulas} 条随机公式...")
    formulas = set()
    
    # 确保生成指定数量的独立公式
    while len(formulas) < num_formulas:
        # 随机选取最大深度，保证公式长短不一，复杂度多样
        max_depth = random.randint(1, 4)
        formula = generate_expression(0, max_depth)
        
        # 过滤掉一些过于简单的公式 (单变量)
        if len(formula) > 2:
            formulas.add(formula)
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 海量自动生成的逻辑公式测试集 (Sympy 原生格式: &, |, ~, >>, Equivalent)\n")
        f.write("# 每行一个公式\n")
        for formula in formulas:
            f.write(formula + '\n')
            
    print(f"成功生成并保存到: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="自动生成海量逻辑公式")
    parser.add_argument("-o", "--output", default=os.path.join("Datasets", "raw_formulas_large.txt"), help="输出文件路径")
    parser.add_argument("-n", "--num", type=int, default=1500, help="生成的公式数量")
    args = parser.parse_args()
    
    generate_dataset(args.output, args.num)
