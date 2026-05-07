#ifndef DIMACS_PARSER_HPP
#define DIMACS_PARSER_HPP

#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

struct CNFFormula {
    int num_vars;
    int num_clauses;
    std::vector<std::vector<int>> clauses;
};

class DimacsParseError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

CNFFormula parse_dimacs(const std::string& file_path);

#endif
