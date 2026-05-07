import sys
import ast

def check_boolean_syntax(expr):
    # 将常见的布尔运算符替换为 Python 运算符以进行语法检查
    # 例如：&& -> and, || -> or, ! -> not
    expr = expr.replace('&&', ' and ').replace('||', ' or ').replace('!', ' not ')
    
    # 将一些常见的逻辑变量符号全部替换为 'True'，这样只有运算符和括号留下来检查语法
    # 使用正则表达式匹配变量（假设变量都是字母开头的单词）
    import re
    # 找到所有的单词
    words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', expr)
    # 保留 Python 的关键字（and, or, not, True, False）
    import keyword
    for w in words:
        if not keyword.iskeyword(w):
            expr = re.sub(rf'\b{w}\b', 'True', expr)

    try:
        # 使用 ast.parse 在 eval 模式下尝试解析表达式
        ast.parse(expr, mode='eval')
        return "Valid"
    except SyntaxError:
        return "Invalid"
    except Exception:
        return "Invalid"

if __name__ == "__main__":
    # 从标准输入读取内容
    input_data = sys.stdin.read().strip()
    if input_data:
        # 输出语法检查结果
        print(check_boolean_syntax(input_data))
