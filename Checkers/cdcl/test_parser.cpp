#include "dimacs_parser.hpp"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

struct TestCase {
    std::string path;
    int expected_vars;
    int expected_clauses;
    bool expect_parse_error;
    std::string description;
};

static void print_formula(const CNFFormula& f) {
    std::cout << "  num_vars    = " << f.num_vars << "\n";
    std::cout << "  num_clauses = " << f.num_clauses << "\n";
    std::cout << "  actual clauses parsed = " << f.clauses.size() << "\n";
    for (size_t i = 0; i < f.clauses.size(); ++i) {
        std::cout << "  clause[" << i << "]: { ";
        for (size_t j = 0; j < f.clauses[i].size(); ++j) {
            if (j) std::cout << ", ";
            std::cout << f.clauses[i][j];
        }
        std::cout << " }\n";
    }
}

static int tests_run = 0;
static int tests_passed = 0;

static void check(bool condition, const std::string& name) {
    ++tests_run;
    if (condition) {
        ++tests_passed;
        std::cout << "[PASS] " << name << "\n";
    } else {
        std::cout << "[FAIL] " << name << "\n";
    }
}

static void test_parse_existing_files() {
    std::cout << "\n=== 测试: 解析已有 DIMACS 文件 ===\n";

    std::string base = "Datasets/cdcl_dimacs";
    std::vector<std::string> files = {
        "sat_01.cnf", "sat_02.cnf", "unsat_01.cnf", "unsat_02.cnf"
    };

    for (const auto& fname : files) {
        std::string path = base + "/" + fname;
        if (!fs::exists(path)) {
            std::cout << "[SKIP] 文件不存在: " << path << "\n";
            continue;
        }
        try {
            CNFFormula f = parse_dimacs(path);
            std::cout << "--- " << fname << " ---\n";
            print_formula(f);
            check(f.num_vars > 0, fname + ": num_vars > 0");
            check(f.num_clauses > 0, fname + ": num_clauses > 0");
            check(f.clauses.size() == static_cast<size_t>(f.num_clauses),
                  fname + ": clause count matches header");
            bool all_clauses_nonempty = true;
            for (const auto& c : f.clauses) {
                if (c.empty()) { all_clauses_nonempty = false; break; }
            }
            check(all_clauses_nonempty, fname + ": no empty clauses");
            bool all_lits_in_range = true;
            for (const auto& c : f.clauses) {
                for (int lit : c) {
                    int v = std::abs(lit);
                    if (v < 1 || v > f.num_vars) { all_lits_in_range = false; break; }
                }
            }
            check(all_lits_in_range, fname + ": all literals in valid range");
        } catch (const DimacsParseError& e) {
            std::cout << "[ERROR] " << fname << ": " << e.what() << "\n";
            check(false, fname + ": should not throw");
        }
    }
}

static void test_simple_sat() {
    std::cout << "\n=== 测试: 简单 SAT 公式 ===\n";

    std::string path = "Datasets/cdcl_dimacs/sat_01.cnf";
    if (!fs::exists(path)) {
        std::cout << "[SKIP] 文件不存在\n";
        return;
    }
    CNFFormula f = parse_dimacs(path);
    check(f.num_vars == 3, "sat_01: num_vars == 3");
    check(f.num_clauses == 3, "sat_01: num_clauses == 3");
    check(f.clauses.size() == 3, "sat_01: parsed 3 clauses");
    check(f.clauses[0] == std::vector<int>({1, 2}), "sat_01: clause[0] == {1, 2}");
    check(f.clauses[1] == std::vector<int>({-1, 3}), "sat_01: clause[1] == {-1, 3}");
    check(f.clauses[2] == std::vector<int>({-2, 3}), "sat_01: clause[2] == {-2, 3}");
}

static void test_simple_unsat() {
    std::cout << "\n=== 测试: 简单 UNSAT 公式 ===\n";

    std::string path = "Datasets/cdcl_dimacs/unsat_01.cnf";
    if (!fs::exists(path)) {
        std::cout << "[SKIP] 文件不存在\n";
        return;
    }
    CNFFormula f = parse_dimacs(path);
    check(f.num_vars == 1, "unsat_01: num_vars == 1");
    check(f.num_clauses == 2, "unsat_01: num_clauses == 2");
    check(f.clauses[0] == std::vector<int>({1}), "unsat_01: clause[0] == {1}");
    check(f.clauses[1] == std::vector<int>({-1}), "unsat_01: clause[1] == {-1}");
}

static void test_synthetic_formula() {
    std::cout << "\n=== 测试: 合成测试文件 ===\n";

    std::string tmp_path = "test_tmp_synthetic.cnf";

    {
        std::ofstream ofs(tmp_path);
        ofs << "c This is a comment\n";
        ofs << "c Another comment\n";
        ofs << "p cnf 5 4\n";
        ofs << "1 2 -3 0\n";
        ofs << "-1 4 5 0\n";
        ofs << "2 -4 0\n";
        ofs << "-2 -5 3 0\n";
    }

    try {
        CNFFormula f = parse_dimacs(tmp_path);
        check(f.num_vars == 5, "synthetic: num_vars == 5");
        check(f.num_clauses == 4, "synthetic: num_clauses == 4");
        check(f.clauses.size() == 4, "synthetic: parsed 4 clauses");
        check(f.clauses[0] == std::vector<int>({1, 2, -3}), "synthetic: clause[0]");
        check(f.clauses[1] == std::vector<int>({-1, 4, 5}), "synthetic: clause[1]");
        check(f.clauses[2] == std::vector<int>({2, -4}), "synthetic: clause[2]");
        check(f.clauses[3] == std::vector<int>({-2, -5, 3}), "synthetic: clause[3]");
    } catch (const DimacsParseError& e) {
        std::cout << "[ERROR] synthetic: " << e.what() << "\n";
        check(false, "synthetic: should not throw");
    }

    fs::remove(tmp_path);
}

static void test_error_no_header() {
    std::cout << "\n=== 测试: 缺少头部 ===\n";

    std::string tmp_path = "test_tmp_no_header.cnf";
    {
        std::ofstream ofs(tmp_path);
        ofs << "c no header here\n";
        ofs << "1 2 0\n";
    }

    try {
        parse_dimacs(tmp_path);
        check(false, "no_header: should throw");
    } catch (const DimacsParseError& e) {
        std::string msg = e.what();
        check(msg.find("DIMACS") != std::string::npos || msg.find("头") != std::string::npos,
              "no_header: error mentions missing header");
    }

    fs::remove(tmp_path);
}

static void test_error_empty_clause() {
    std::cout << "\n=== 测试: 空子句 ===\n";

    std::string tmp_path = "test_tmp_empty_clause.cnf";
    {
        std::ofstream ofs(tmp_path);
        ofs << "p cnf 2 2\n";
        ofs << "1 0\n";
        ofs << "0\n";
    }

    try {
        parse_dimacs(tmp_path);
        check(false, "empty_clause: should throw");
    } catch (const DimacsParseError& e) {
        std::string msg = e.what();
        check(msg.find("空子句") != std::string::npos,
              "empty_clause: error mentions empty clause");
    }

    fs::remove(tmp_path);
}

static void test_error_missing_terminator() {
    std::cout << "\n=== 测试: 子句缺少终止符 ===\n";

    std::string tmp_path = "test_tmp_missing_term.cnf";
    {
        std::ofstream ofs(tmp_path);
        ofs << "p cnf 3 2\n";
        ofs << "1 2 0\n";
        ofs << "-1 3\n";
    }

    try {
        parse_dimacs(tmp_path);
        check(false, "missing_term: should throw");
    } catch (const DimacsParseError& e) {
        std::string msg = e.what();
        check(msg.find("未以 0 结束") != std::string::npos,
              "missing_term: error mentions unterminated clause");
    }

    fs::remove(tmp_path);
}

static void test_error_bad_format() {
    std::cout << "\n=== 测试: 错误格式头 ===\n";

    std::string tmp_path = "test_tmp_bad_format.cnf";
    {
        std::ofstream ofs(tmp_path);
        ofs << "p sat 3 2\n";
        ofs << "1 0\n";
    }

    try {
        parse_dimacs(tmp_path);
        check(false, "bad_format: should throw");
    } catch (const DimacsParseError& e) {
        std::string msg = e.what();
        check(msg.find("格式") != std::string::npos || msg.find("cnf") != std::string::npos,
              "bad_format: error mentions format issue");
    }

    fs::remove(tmp_path);
}

static void test_error_file_not_found() {
    std::cout << "\n=== 测试: 文件不存在 ===\n";

    try {
        parse_dimacs("nonexistent_file_12345.cnf");
        check(false, "file_not_found: should throw");
    } catch (const DimacsParseError& e) {
        std::string msg = e.what();
        check(msg.find("打开") != std::string::npos || msg.find("无法") != std::string::npos,
              "file_not_found: error mentions file open failure");
    }
}

static void test_multiline_clause_literals() {
    std::cout << "\n=== 测试: 空格分隔多文字 ===\n";

    std::string tmp_path = "test_tmp_multispace.cnf";
    {
        std::ofstream ofs(tmp_path);
        ofs << "p cnf 4 1\n";
        ofs << "  1   -2    3   -4   0  \n";
    }

    try {
        CNFFormula f = parse_dimacs(tmp_path);
        check(f.clauses.size() == 1, "multispace: 1 clause parsed");
        check(f.clauses[0] == std::vector<int>({1, -2, 3, -4}), "multispace: clause contents");
    } catch (const DimacsParseError& e) {
        std::cout << "[ERROR] multispace: " << e.what() << "\n";
        check(false, "multispace: should not throw");
    }

    fs::remove(tmp_path);
}

static void test_cross_validate_python() {
    std::cout << "\n=== 测试: 与 Python 解析器交叉验证 ===\n";

    std::string base = "Datasets/cdcl_dimacs";
    std::vector<std::pair<std::string, std::string>> expected = {
        {"sat_01.cnf",   "3 3  1 2 0  -1 3 0  -2 3 0"},
        {"sat_02.cnf",   ""},
        {"unsat_01.cnf", "1 2  1 0  -1 0"},
        {"unsat_02.cnf", ""},
    };

    for (const auto& [fname, _] : expected) {
        std::string path = base + "/" + fname;
        if (!fs::exists(path)) continue;
        try {
            CNFFormula f = parse_dimacs(path);
            bool ok = f.num_vars > 0 &&
                      f.num_clauses > 0 &&
                      f.clauses.size() == static_cast<size_t>(f.num_clauses);
            if (ok) {
                for (const auto& c : f.clauses) {
                    if (c.empty()) { ok = false; break; }
                    for (int lit : c) {
                        if (std::abs(lit) > f.num_vars) { ok = false; break; }
                    }
                }
            }
            check(ok, "cross_validate: " + fname);
        } catch (const std::exception& e) {
            std::cout << "[ERROR] cross_validate " << fname << ": " << e.what() << "\n";
            check(false, "cross_validate: " + fname);
        }
    }
}

int main() {
    std::cout << "============================================\n";
    std::cout << " DIMACS C++ 解析器测试套件\n";
    std::cout << "============================================\n";

    test_simple_sat();
    test_simple_unsat();
    test_parse_existing_files();
    test_synthetic_formula();
    test_error_no_header();
    test_error_empty_clause();
    test_error_missing_terminator();
    test_error_bad_format();
    test_error_file_not_found();
    test_multiline_clause_literals();
    test_cross_validate_python();

    std::cout << "\n============================================\n";
    std::cout << " 测试结果: " << tests_passed << "/" << tests_run << " 通过\n";
    std::cout << "============================================\n";

    return (tests_passed == tests_run) ? 0 : 1;
}
