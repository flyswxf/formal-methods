#include "dimacs_parser.hpp"
#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>

static std::string trim(const std::string& s) {
    size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start])))
        ++start;
    if (start == s.size())
        return {};
    size_t end = s.size() - 1;
    while (end > start && std::isspace(static_cast<unsigned char>(s[end])))
        --end;
    return s.substr(start, end - start + 1);
}

static std::string strip_bom(const std::string& s) {
    if (s.size() >= 3 &&
        static_cast<unsigned char>(s[0]) == 0xEF &&
        static_cast<unsigned char>(s[1]) == 0xBB &&
        static_cast<unsigned char>(s[2]) == 0xBF) {
        return s.substr(3);
    }
    return s;
}

CNFFormula parse_dimacs(const std::string& file_path) {
    std::ifstream ifs(file_path);
    if (!ifs.is_open())
        throw DimacsParseError("无法打开文件: " + file_path);

    CNFFormula formula{};
    bool header_seen = false;
    std::vector<int> pending_clause;
    std::string raw_line;
    bool first_line = true;

    while (std::getline(ifs, raw_line)) {
        if (first_line) {
            raw_line = strip_bom(raw_line);
            first_line = false;
        }

        std::string line = trim(raw_line);
        if (line.empty() || line[0] == 'c')
            continue;

        if (line[0] == 'p') {
            std::istringstream iss(line);
            std::string p_tag, cnf_tag;
            iss >> p_tag >> cnf_tag;
            if (cnf_tag != "cnf")
                throw DimacsParseError("DIMACS 头格式错误，期望: p cnf <num_vars> <num_clauses>");
            if (!(iss >> formula.num_vars))
                throw DimacsParseError("DIMACS 头缺少变量数");
            if (!(iss >> formula.num_clauses))
                throw DimacsParseError("DIMACS 头缺少子句数");
            header_seen = true;
            formula.clauses.reserve(formula.num_clauses);
            continue;
        }

        std::istringstream iss(line);
        int lit;
        while (iss >> lit) {
            if (lit == 0) {
                if (pending_clause.empty())
                    throw DimacsParseError("检测到空子句，公式不可满足。");
                formula.clauses.push_back(std::move(pending_clause));
                pending_clause.clear();
            } else {
                pending_clause.push_back(lit);
            }
        }
    }

    if (!header_seen)
        throw DimacsParseError("缺少 DIMACS 头: p cnf <num_vars> <num_clauses>");
    if (!pending_clause.empty())
        throw DimacsParseError("存在未以 0 结束的子句。");

    return formula;
}
