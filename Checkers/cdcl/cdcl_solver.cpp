#include "cdcl_solver.hpp"
#include <algorithm>

static const double VAR_INC_INIT = 1.0;
static const double VAR_DECAY = 0.95;

CDCLSolver::CDCLSolver(int num_vars, const std::vector<std::vector<int>>& clauses)
    : n_vars(num_vars), n_clauses(static_cast<int>(clauses.size())),
      qhead(0), qtail(0), decision_level(0), conflict_count(0),
      var_inc(VAR_INC_INIT), var_decay(VAR_DECAY), initial_conflict(false)
{
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
            if (value_of(lits[0]) == -1) {
                initial_conflict = true;
                return;
            }
            if (value_of(lits[0]) == 0) {
                unchecked_enqueue(lits[0], -1);
            }
        } else {
            int idx = static_cast<int>(clause_db.size());
            clause_db.emplace_back(std::move(lits), false);
            Clause& cl = clause_db[idx];
            watches[cl[0].neg().val].emplace_back(idx, cl[1]);
            watches[cl[1].neg().val].emplace_back(idx, cl[0]);
        }
    }

    if (propagate() != -1) {
        initial_conflict = true;
    }
}

void CDCLSolver::unchecked_enqueue(Lit p, int from) {
    int v = p.var();
    vars[v].value = p.sign() ? VarValue::FALSE : VarValue::TRUE;
    vars[v].level = decision_level;
    vars[v].reason = from;
    vars[v].polarity = p.sign();
    trail.push_back(p);
    qtail = static_cast<int>(trail.size());
}

void CDCLSolver::new_decision_level() {
    trail_lim.push_back(qtail);
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
    int confl = -1;
    while (qhead < qtail) {
        Lit p = trail[qhead++];
        auto& ws = watches[p.neg().val];
        size_t i = 0, j = 0;
        while (i < ws.size()) {
            if (lit_true(ws[i].blocker)) {
                ws[j++] = ws[i++];
                continue;
            }
            int ci = ws[i].cref;
            Clause& c = clause_db[ci];

            if (c[0] == p.neg()) {
                std::swap(c[0], c[1]);
            }

            if (lit_true(c[0])) {
                ws[j].cref = ci;
                ws[j].blocker = c[0];
                ++j; ++i;
                continue;
            }

            bool found = false;
            for (size_t k = 2; k < c.size(); ++k) {
                if (!lit_false(c[k])) {
                    std::swap(c[1], c[k]);
                    watches[c[1].neg().val].emplace_back(ci, c[0]);
                    found = true;
                    break;
                }
            }

            if (found) {
                ++i;
                continue;
            }

            ws[j].cref = ci;
            ws[j].blocker = c[0];
            ++j;

            if (lit_false(c[0])) {
                confl = ci;
                ++i;
                while (i < ws.size()) ws[j++] = ws[i++];
                break;
            } else {
                unchecked_enqueue(c[0], ci);
            }
            ++i;
        }
        ws.resize(j);
        if (confl != -1) return confl;
    }
    return -1;
}

void CDCLSolver::analyze(int confl, std::vector<Lit>& out_learnt, int& out_btlevel) {
    out_learnt.clear();
    out_learnt.push_back(UNDEF_LIT);

    seen.assign(n_vars + 1, false);
    int counter = 0;
    Lit p = UNDEF_LIT;
    int trail_idx = static_cast<int>(trail.size()) - 1;

    int ci = confl;
    while (true) {
        Clause& cl = clause_db[ci];
        for (size_t i = 0; i < cl.size(); ++i) {
            Lit q = cl[i];
            if (q == p || seen[q.var()]) continue;
            seen[q.var()] = true;
            vsids_bump(q.var());
            if (vars[q.var()].level >= decision_level) {
                counter++;
            } else {
                out_learnt.push_back(q);
            }
        }

        while (trail_idx >= 0 && (!seen[trail[trail_idx].var()] || vars[trail[trail_idx].var()].level < decision_level)) {
            trail_idx--;
        }
        p = trail[trail_idx];
        seen[p.var()] = false;
        counter--;
        if (counter <= 0) break;
        ci = vars[p.var()].reason;
    }

    out_learnt[0] = p.neg();

    if (out_learnt.size() == 1) {
        out_btlevel = 0;
    } else {
        int max_idx = 1;
        for (size_t i = 2; i < out_learnt.size(); ++i) {
            if (vars[out_learnt[i].var()].level > vars[out_learnt[max_idx].var()].level) {
                max_idx = static_cast<int>(i);
            }
        }
        std::swap(out_learnt[1], out_learnt[max_idx]);
        out_btlevel = vars[out_learnt[1].var()].level;
    }
}

void CDCLSolver::record(const std::vector<Lit>& learnt) {
    if (learnt.size() == 1) {
        unchecked_enqueue(learnt[0], -1);
        return;
    }
    int idx = static_cast<int>(clause_db.size());
    clause_db.emplace_back(std::vector<Lit>(learnt), true);
    Clause& cl = clause_db[idx];
    watches[cl[0].neg().val].emplace_back(idx, cl[1]);
    watches[cl[1].neg().val].emplace_back(idx, cl[0]);
    unchecked_enqueue(cl[0], idx);
}

void CDCLSolver::cancel_until(int level) {
    if (decision_level <= level) return;
    for (int i = static_cast<int>(trail.size()) - 1; i >= trail_lim[level]; --i) {
        int v = trail[i].var();
        vars[v].polarity = (vars[v].value == VarValue::TRUE);
        vars[v].value = VarValue::UNDEF;
        vars[v].level = -1;
        vars[v].reason = -1;
        if (heap_pos[v] == -1) {
            heap_insert(v);
        }
    }
    qhead = trail_lim[level];
    qtail = trail_lim[level];
    trail.resize(trail_lim[level]);
    trail_lim.resize(level);
    decision_level = level;
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
        int smallest = pos;
        int l = heap_left(pos);
        int r = heap_right(pos);
        if (l < sz && heap_cmp(heap[smallest], heap[l])) smallest = l;
        if (r < sz && heap_cmp(heap[smallest], heap[r])) smallest = r;
        if (smallest != pos) {
            std::swap(heap[pos], heap[smallest]);
            heap_pos[heap[pos]] = pos;
            heap_pos[heap[smallest]] = smallest;
            pos = smallest;
        } else {
            break;
        }
    }
}

bool CDCLSolver::solve() {
    if (initial_conflict) return false;

    while (true) {
        int confl = propagate();
        if (confl != -1) {
            if (decision_level == 0) return false;
            std::vector<Lit> learnt;
            int btlevel;
            analyze(confl, learnt, btlevel);
            cancel_until(btlevel);
            record(learnt);
            vsids_decay();
            conflict_count++;
        } else {
            if (static_cast<int>(trail.size()) >= n_vars) return true;
            Lit next = pick_branch_lit();
            if (next.val == 0) return true;
            new_decision_level();
            unchecked_enqueue(next, -1);
        }
    }
}
