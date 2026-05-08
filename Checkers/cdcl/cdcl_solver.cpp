#include "cdcl_solver.hpp"
#include <algorithm>
#include <cstdlib>
#include <cstdio>

static const double VAR_INC_INIT = 1.0;
static const double VAR_DECAY = 0.95;

CDCLSolver::CDCLSolver(int num_vars, const std::vector<std::vector<int>>& clauses)
    : n_vars(num_vars), n_clauses(static_cast<int>(clauses.size())),
      qhead(0), decision_level(0), conflict_count(0),
      var_inc(VAR_INC_INIT), var_decay(VAR_DECAY), initial_conflict(false),
      self_check_enabled(false), self_check_interval(20000), self_check_counter(0)
{
    const char* check_env = std::getenv("CDCL_SELF_CHECK");
    self_check_enabled = (check_env != nullptr && check_env[0] == '1');
    const char* interval_env = std::getenv("CDCL_SELF_CHECK_INTERVAL");
    if (interval_env != nullptr) {
        int parsed = std::atoi(interval_env);
        if (parsed > 0) self_check_interval = parsed;
    }

    vars.resize(n_vars + 1);
    activity.resize(n_vars + 1, 0.0);
    heap_pos.resize(n_vars + 1, -1);
    seen.resize(n_vars + 1, false);
    watches.resize(2 * (n_vars + 1));

    for (int v = 1; v <= n_vars; ++v) {
        heap_insert(v);
    }

    for (const auto& c : clauses) {
        if (c.empty()) {
            initial_conflict = true;
            return;
        }

        std::vector<Lit> lits;
        lits.reserve(c.size());
        for (int d : c) {
            lits.push_back(Lit::from_dimacs(d));
        }

        if (lits.size() == 1) {
            if (!enqueue(lits[0], -1)) {
                initial_conflict = true;
                return;
            }
            continue;
        }

        int idx = static_cast<int>(clause_db.size());
        clause_db.emplace_back(std::move(lits), false);
        attach_clause(idx);
    }

    if (propagate() != -1) {
        initial_conflict = true;
    }

    if (self_check_enabled) {
        self_check_trail_and_assignments("ctor");
        self_check_watchers_sample("ctor");
    }
}

void CDCLSolver::self_check_fail(const char* module, const char* message) const {
    std::fprintf(stderr, "[CDCL_SELF_CHECK][%s] %s\n", module, message);
    std::fflush(stderr);
    std::abort();
}

void CDCLSolver::self_check_require(bool condition, const char* module, const char* message) const {
    if (!self_check_enabled) return;
    if (!condition) self_check_fail(module, message);
}

void CDCLSolver::self_check_clause_shape(int cref, const char* module) const {
    if (!self_check_enabled) return;
    self_check_require(cref >= 0 && cref < static_cast<int>(clause_db.size()), module, "invalid clause reference");
    const Clause& c = clause_db[cref];
    self_check_require(c.size() >= 2, module, "watched clause must have size >= 2");
    for (size_t i = 0; i < c.size(); ++i) {
        int v = c[i].var();
        self_check_require(v >= 1 && v <= n_vars, module, "literal variable out of range");
    }
}

void CDCLSolver::self_check_trail_and_assignments(const char* module) const {
    if (!self_check_enabled) return;
    self_check_require(qhead >= 0 && qhead <= static_cast<int>(trail.size()), module, "qhead out of range");
    self_check_require(decision_level >= 0, module, "negative decision level");
    self_check_require(static_cast<int>(trail_lim.size()) == decision_level, module, "trail_lim size mismatch");

    std::vector<bool> seen_var(n_vars + 1, false);
    for (size_t i = 0; i < trail.size(); ++i) {
        int v = trail[i].var();
        self_check_require(v >= 1 && v <= n_vars, module, "trail variable out of range");
        self_check_require(!seen_var[v], module, "duplicate variable in trail");
        seen_var[v] = true;
        self_check_require(vars[v].value != VarValue::UNDEF, module, "trail variable is unassigned");
    }

    for (int v = 1; v <= n_vars; ++v) {
        bool on_trail = seen_var[v];
        bool assigned = vars[v].value != VarValue::UNDEF;
        self_check_require(on_trail == assigned, module, "trail/assignment mismatch");
    }
}

void CDCLSolver::self_check_watchers_sample(const char* module) {
    if (!self_check_enabled) return;
    ++self_check_counter;
    if (self_check_counter % self_check_interval != 0) return;

    for (size_t wi = 0; wi < watches.size(); ++wi) {
        const auto& ws = watches[wi];
        for (size_t j = 0; j < ws.size(); ++j) {
            int cref = ws[j].cref;
            self_check_clause_shape(cref, module);
        }
    }
}

bool CDCLSolver::enqueue(Lit p, int from) {
    self_check_require(p.var() >= 1 && p.var() <= n_vars, "enqueue", "literal variable out of range");
    self_check_require(from < static_cast<int>(clause_db.size()), "enqueue", "reason out of range");
    int val = value_of(p);
    if (val == 1) return true;
    if (val == -1) return false;
    unchecked_enqueue(p, from);
    self_check_trail_and_assignments("enqueue");
    return true;
}

void CDCLSolver::unchecked_enqueue(Lit p, int from) {
    int v = p.var();
    vars[v].value = p.sign() ? VarValue::FALSE : VarValue::TRUE;
    vars[v].level = decision_level;
    vars[v].reason = from;
    vars[v].polarity = p.sign();
    trail.push_back(p);
}

void CDCLSolver::attach_clause(int cref) {
    Clause& cl = clause_db[cref];
    self_check_clause_shape(cref, "attach_clause");
    watches[cl[0].neg().val].emplace_back(cref, cl[1]);
    watches[cl[1].neg().val].emplace_back(cref, cl[0]);
}

void CDCLSolver::new_decision_level() {
    trail_lim.push_back(static_cast<int>(trail.size()));
    decision_level++;
}

int CDCLSolver::value_of(Lit p) const {
    int v = p.var();
    if (vars[v].value == VarValue::UNDEF) return 0;
    bool is_true = (p.sign() && vars[v].value == VarValue::FALSE) ||
                   (!p.sign() && vars[v].value == VarValue::TRUE);
    return is_true ? 1 : -1;
}

bool CDCLSolver::lit_true(Lit p) const { return value_of(p) == 1; }
bool CDCLSolver::lit_false(Lit p) const { return value_of(p) == -1; }
bool CDCLSolver::lit_undef(Lit p) const { return value_of(p) == 0; }

int CDCLSolver::propagate() {
    while (qhead < static_cast<int>(trail.size())) {
        Lit p = trail[qhead++];
        auto& ws = watches[p.val];
        size_t i = 0;
        size_t j = 0;

        while (i < ws.size()) {
            Watcher w = ws[i++];
            if (lit_true(w.blocker)) {
                ws[j++] = w;
                continue;
            }

            int ci = w.cref;
            self_check_clause_shape(ci, "propagate");
            Clause& c = clause_db[ci];

            if (c[0] == p.neg()) {
                std::swap(c[0], c[1]);
            }

            if (lit_true(c[0])) {
                ws[j++] = Watcher(ci, c[0]);
                continue;
            }

            bool found_new_watch = false;
            for (size_t k = 2; k < c.size(); ++k) {
                if (!lit_false(c[k])) {
                    std::swap(c[1], c[k]);
                    watches[c[1].neg().val].emplace_back(ci, c[0]);
                    found_new_watch = true;
                    break;
                }
            }

            if (found_new_watch) {
                continue;
            }

            ws[j++] = Watcher(ci, c[0]);
            if (lit_false(c[0])) {
                while (i < ws.size()) {
                    ws[j++] = ws[i++];
                }
                ws.resize(j);
                self_check_watchers_sample("propagate-conflict");
                return ci;
            }

            if (!enqueue(c[0], ci)) {
                ws.resize(j);
                return ci;
            }
        }

        ws.resize(j);
        self_check_watchers_sample("propagate-step");
    }

    return -1;
}

void CDCLSolver::analyze(int confl, std::vector<Lit>& out_learnt, int& out_btlevel) {
    self_check_clause_shape(confl, "analyze");
    out_learnt.clear();
    out_learnt.push_back(UNDEF_LIT);

    std::fill(seen.begin(), seen.end(), false);
    int path_count = 0;
    Lit p = UNDEF_LIT;
    int idx = static_cast<int>(trail.size()) - 1;

    do {
        Clause& c = clause_db[confl];
        for (size_t i = 0; i < c.size(); ++i) {
            Lit q = c[i];
            int v = q.var();
            if (q == p || seen[v]) continue;

            seen[v] = true;
            vsids_bump(v);

            if (vars[v].level == decision_level) {
                path_count++;
            } else {
                out_learnt.push_back(q);
            }
        }

        while (idx >= 0 && !seen[trail[idx].var()]) {
            idx--;
        }

        if (idx < 0) {
            out_btlevel = 0;
            out_learnt[0] = p.neg();
            return;
        }

        p = trail[idx--];
        seen[p.var()] = false;
        path_count--;

        if (path_count <= 0) {
            break;
        }

        confl = vars[p.var()].reason;
        if (confl < 0) {
            break;
        }
        self_check_clause_shape(confl, "analyze-reason");
    } while (true);

    out_learnt[0] = p.neg();

    if (out_learnt.size() == 1) {
        out_btlevel = 0;
        return;
    }

    int max_idx = 1;
    for (size_t i = 2; i < out_learnt.size(); ++i) {
        if (vars[out_learnt[i].var()].level > vars[out_learnt[max_idx].var()].level) {
            max_idx = static_cast<int>(i);
        }
    }
    std::swap(out_learnt[1], out_learnt[max_idx]);
    out_btlevel = vars[out_learnt[1].var()].level;
}

void CDCLSolver::record(const std::vector<Lit>& learnt) {
    if (learnt.size() == 1) {
        enqueue(learnt[0], -1);
        return;
    }

    int idx = static_cast<int>(clause_db.size());
    clause_db.emplace_back(learnt, true);
    attach_clause(idx);
    self_check_require(enqueue(clause_db[idx][0], idx), "record", "asserting literal enqueue conflict");
    self_check_watchers_sample("record");
}

void CDCLSolver::cancel_until(int level) {
    self_check_require(level >= 0 && level <= decision_level, "cancel_until", "invalid backtrack level");
    if (decision_level <= level) return;

    for (int i = static_cast<int>(trail.size()) - 1; i >= trail_lim[level]; --i) {
        int v = trail[i].var();
        vars[v].polarity = (vars[v].value == VarValue::FALSE);
        vars[v].value = VarValue::UNDEF;
        vars[v].level = -1;
        vars[v].reason = -1;
        if (heap_pos[v] == -1) {
            heap_insert(v);
        }
    }

    trail.resize(trail_lim[level]);
    trail_lim.resize(level);
    decision_level = level;
    qhead = static_cast<int>(trail.size());
    self_check_trail_and_assignments("cancel_until");
}

void CDCLSolver::vsids_bump(int var) {
    activity[var] += var_inc;
    if (heap_pos[var] != -1) {
        heap_decrease(var);
    }
}

void CDCLSolver::vsids_decay() {
    var_inc *= (1.0 / var_decay);
}

Lit CDCLSolver::pick_branch_lit() {
    while (!heap_empty()) {
        int v = heap_remove_min();
        if (vars[v].value == VarValue::UNDEF) {
            return Lit(vars[v].polarity ? 2 * v + 1 : 2 * v);
        }
    }
    return UNDEF_LIT;
}

bool CDCLSolver::heap_empty() const {
    return heap.empty();
}

int CDCLSolver::heap_remove_min() {
    int v = heap[0];
    heap_pos[v] = -1;
    int last = heap.back();
    heap.pop_back();
    if (!heap.empty()) {
        heap[0] = last;
        heap_pos[last] = 0;
        heap_sift_down(0);
    }
    return v;
}

void CDCLSolver::heap_insert(int v) {
    heap_pos[v] = static_cast<int>(heap.size());
    heap.push_back(v);
    heap_sift_up(heap_pos[v]);
}

void CDCLSolver::heap_decrease(int v) {
    heap_sift_up(heap_pos[v]);
}

void CDCLSolver::heap_sift_up(int pos) {
    while (pos > 0) {
        int p = heap_parent(pos);
        if (heap_cmp(heap[p], heap[pos])) {
            std::swap(heap[p], heap[pos]);
            heap_pos[heap[p]] = p;
            heap_pos[heap[pos]] = pos;
            pos = p;
        } else {
            break;
        }
    }
}

void CDCLSolver::heap_sift_down(int pos) {
    int sz = static_cast<int>(heap.size());
    while (true) {
        int best = pos;
        int l = heap_left(pos);
        int r = heap_right(pos);

        if (l < sz && heap_cmp(heap[best], heap[l])) best = l;
        if (r < sz && heap_cmp(heap[best], heap[r])) best = r;

        if (best == pos) break;

        std::swap(heap[pos], heap[best]);
        heap_pos[heap[pos]] = pos;
        heap_pos[heap[best]] = best;
        pos = best;
    }
}

bool CDCLSolver::solve() {
    if (initial_conflict) return false;

    while (true) {
        int confl = propagate();
        if (confl != -1) {
            if (decision_level == 0) return false;

            std::vector<Lit> learnt;
            int btlevel = 0;
            analyze(confl, learnt, btlevel);
            cancel_until(btlevel);
            record(learnt);
            vsids_decay();
            conflict_count++;
            continue;
        }

        Lit next = pick_branch_lit();
        if (next == UNDEF_LIT) {
            return true;
        }

        new_decision_level();
        if (!enqueue(next, -1)) {
            return false;
        }

        self_check_watchers_sample("solve-loop");
    }
}
