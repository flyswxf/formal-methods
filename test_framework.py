import argparse
import subprocess
import sys
import os

def run_test_framework(executable_path, dataset_path):
    if not os.path.exists(executable_path):
        print(f"错误: 找不到可执行文件 '{executable_path}'")
        sys.exit(1)
        
    if not os.path.exists(dataset_path):
        print(f"错误: 找不到测试数据集文件 '{dataset_path}'")
        sys.exit(1)

    print(f"--- 开始测试 ---\n可执行程序: {executable_path}\n数据集: {dataset_path}\n")

    passed_count = 0
    total_count = 0

    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"读取数据集文件失败: {e}")
        sys.exit(1)

    # 假设数据集格式为每行一个输入输出对，用 '::' 分隔
    # 格式：输入式子 :: 期望输出
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        # 跳过空行或注释行
        if not line or line.startswith('#'):
            continue
        
        parts = line.split('::')
        if len(parts) != 2:
            print(f"警告: 数据集第 {line_num} 行格式不正确，已跳过。格式应为 '输入 :: 期望输出'")
            continue

        test_input = parts[0].strip()
        expected_output = parts[1].strip()
        total_count += 1

        # 构建运行命令，如果是 Python 脚本则用 python 运行
        if executable_path.endswith('.py'):
            cmd = [sys.executable, executable_path]
        else:
            cmd = [executable_path]

        try:
            # 运行可执行程序，将输入通过 stdin 传入，并捕获 stdout 和 stderr
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # 设定超时时间 5 秒
            actual_output, stderr_data = process.communicate(input=test_input, timeout=5)
            actual_output = actual_output.strip()
            
            # 比较真实输出与期望输出
            if actual_output == expected_output:
                print(f"[通过] 用例 {total_count}: 输入='{test_input}'")
                passed_count += 1
            else:
                print(f"[失败] 用例 {total_count}: 输入='{test_input}'")
                print(f"       期望输出: '{expected_output}'")
                print(f"       实际输出: '{actual_output}'")
                if stderr_data:
                    print(f"       错误信息: '{stderr_data.strip()}'")
                    
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"[超时] 用例 {total_count}: 输入='{test_input}' (程序运行超过5秒)")
        except Exception as e:
            print(f"[异常] 用例 {total_count}: 输入='{test_input}' -> {e}")

    print("\n--- 测试总结 ---")
    print(f"总计用例: {total_count}")
    print(f"通过: {passed_count}")
    print(f"失败: {total_count - passed_count}")
    
    if total_count > 0 and passed_count == total_count:
        print("🎉 所有测试用例均已通过！")
    elif total_count > 0:
        print("❌ 部分测试用例未通过。")
    else:
        print("⚠️ 未找到任何有效的测试用例。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="通用布尔逻辑语法测试框架")
    parser.add_argument("executable", help="可执行文件的路径 (如 bool_checker.py 或 checker.exe)")
    parser.add_argument("dataset", help="测试数据集文件的路径 (格式: 输入 :: 期望输出)")
    
    args = parser.parse_args()
    run_test_framework(args.executable, args.dataset)
