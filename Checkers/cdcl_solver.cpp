#include "cdcl/dimacs_parser.hpp"
#include "cdcl/cdcl_solver.hpp"
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    std::string path;
    if (argc >= 2) {
        path = argv[1];
    } else {
        if (!std::getline(std::cin, path)) {
            std::cout << "UNSAT" << std::endl;
            return 0;
        }
    }

    if (path.empty()) {
        std::cout << "UNSAT" << std::endl;
        return 0;
    }

    try {
        CNFFormula formula = parse_dimacs(path);
        CDCLSolver solver(formula.num_vars, formula.clauses);
        bool sat = solver.solve();
        std::cout << (sat ? "SAT" : "UNSAT") << std::endl;
    } catch (...) {
        std::cout << "UNSAT" << std::endl;
    }

    return 0;
}
