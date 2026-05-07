#ifndef CDCL_SOLVER_HPP
#define CDCL_SOLVER_HPP

#include <cstdint>
#include <vector>
#include <cassert>
#include <limits>

struct Lit {
    int val;
    Lit() : val(0) {}
    explicit Lit(int v) : val(v) {}
    static Lit from_dimacs(int d) { return Lit(d > 0 ? 2 * d : -2 * d + 1); }
    int var() const { return val >> 1; }
    bool sign() const { return val & 1; }
    Lit neg() const { return Lit(val ^ 1); }
    bool operator==(Lit o) const { return val == o.val; }
    bool operator!=(Lit o) const { return val != o.val; }
    bool operator<(Lit o) const { return val < o.val; }
    int to_dimacs() const { return sign() ? -var() : var(); }
};

static const Lit UNDEF_LIT = Lit(-1);

struct Clause {
    std::vector<Lit> lits;
    bool learnt;
    Clause() : learnt(false) {}
    Clause(std::vector<Lit> l, bool learned) : lits(std::move(l)), learnt(learned) {}
    size_t size() const { return lits.size(); }
    Lit& operator[](size_t i) { return lits[i]; }
    const Lit& operator[](size_t i) const { return lits[i]; }
};

enum class VarValue : uint8_t { UNDEF = 0, TRUE = 1, FALSE = 2 };

struct VarInfo {
    VarValue value;
    int level;
    int reason;
    bool polarity;
    VarInfo() : value(VarValue::UNDEF), level(-1), reason(-1), polarity(false) {}
};

struct Watcher {
    int cref;
    Lit blocker;
    Watcher() : cref(-1) {}
    Watcher(int c, Lit b) : cref(c), blocker(b) {}
};

class CDCLSolver {
public:
    CDCLSolver(int num_vars, const std::vector<std::vector<int>>& clauses);

    bool solve();

private:
    int n_vars;
    int n_clauses;
    int qhead;
    int qtail;
    int decision_level;
    int conflict_count;

    std::vector<VarInfo> vars;
    std::vector<Clause> clause_db;
    std::vector<std::vector<Watcher>> watches;
    std::vector<Lit> trail;
    std::vector<int> trail_lim;
    std::vector<bool> seen;
    std::vector<Lit> learnt_clause;
    std::vector<Lit> analyze_stack;
    std::vector<Lit> analyze_toclear;
    std::vector<Lit> propagate_buffer;

    std::vector<double> activity;
    std::vector<int> heap;
    std::vector<int> heap_pos;
    double var_inc;
    double var_decay;
    bool initial_conflict;

    Lit pick_branch_lit();
    void new_decision_level();
    void unchecked_enqueue(Lit p, int from);
    int propagate();
    int value_of(Lit p) const;
    bool lit_true(Lit p) const;
    bool lit_false(Lit p) const;
    bool lit_undef(Lit p) const;
    void analyze(int confl, std::vector<Lit>& out_learnt, int& out_btlevel);
    void record(const std::vector<Lit>& learnt);
    void cancel_until(int level);
    void vsids_bump(int var);
    void vsids_decay();
    bool heap_empty() const;
    int heap_remove_min();
    void heap_insert(int v);
    void heap_decrease(int v);
    void heap_sift_up(int pos);
    void heap_sift_down(int pos);
    int heap_parent(int i) const { return (i - 1) / 2; }
    int heap_left(int i) const { return 2 * i + 1; }
    int heap_right(int i) const { return 2 * i + 2; }
    bool heap_cmp(int a, int b) const { return activity[a] < activity[b]; }
};

#endif
