import sys
from copy import copy

def parse_problem(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    for i in range(len(lines) - 1):
        if lines[i] == "%\n" and lines[i + 1] == "0\n":
            lines = lines[:i]
            break

    clauses = []
    for line in lines:
        if line[0] == "c":  # comment
            continue
        if line[0] == "p":
            toks = line.split()
            assert toks[1] == "cnf"
            assert len(toks) == 4
            num_vars, num_clauses = map(int, (toks[2], toks[3]))
        else:
            toks = list(map(int, line.split()))
            assert toks[-1] == 0
            toks.pop()
            clauses.append(Clause.default_clause(toks))

    assert num_clauses == len(clauses)

    return clauses, num_vars

class Assignment:
    @classmethod
    def implication(cls, literal, idx):
        assignment = cls()
        assignment.literal = literal
        assignment.idx = idx
        return assignment

    @classmethod
    def decision(cls, literal):
        assignment = cls()
        assignment.literal = literal
        assignment.idx = None
        return assignment

    def impl(self):
        return self.idx is not None

    def desc(self):
        return self.idx is None

    def __repr__(self):
        if self.impl():
            return f"I(i={self.idx}, L={self.literal})"
        else:
            return f"D(L={self.literal})"


class Solution:
    def __init__(self, sat, sol=None):
        self.sat = sat
        self.sol = sol

    def __repr__(self):
        if self.sat:
            first_line = "s SATISFIABLE\n"
            L = ["v"]
            for s in self.sol:
                L.append(str(-(s >> 1)  if (s & 1) else (s >> 1)))
            L.append("0")
            return first_line + " ".join(L)
        
        return "s UNSATISFIABLE"


class Clause:
    def __init__(self):
        self.inner = set()
        self.undecided = set()
        self.true = set()
        self.false = set()
        self.watched_literals = set()

    @classmethod
    def default_clause(cls, iterable):
        clause = cls()
        for val in iterable:
            val_encoded = val << 1 if val > 0 else ((-val) << 1) | 1
            clause.inner.add(val_encoded)
            clause.undecided.add(val_encoded)
            if (len(clause.watched_literals) < 2):
                clause.watched_literals.add(val_encoded)

        return clause

    def __repr__(self):
        return "{" + ", ".join(map(
            lambda i: f"*{i}{'=T' if i in self.true else ''}{'=F' if i in self.false else ''}"
            , self.inner)) + "}"

    def disassign(self, literal):
        # assert((literal in self.true - self.false) or (literal in self.false - self.true))
        self.true.discard(literal)
        self.false.discard(literal)
        self.undecided.add(literal)

    def empty(self):
        return len(self.inner) == 0

    def exist(self, var):
        return (var in self.inner) or ((var ^ 1) in self.inner)

    def is_true(self):
        return bool(self.true)

    def is_false(self):
        return self.false == self.inner

    def is_unit(self):
        return not bool(self.true) and len(self.undecided) == 1

    def resolvent(self, literal, clause):
        cl = Clause()
        cl.inner = self.inner.union(clause.inner)
        cl.inner.remove(literal)
        cl.inner.remove(literal ^ 1)
        return cl          # Will assign undecided / false later


class DPLL:
    def __init__(self, clauses, nvars):
        self.clauses = clauses
        self.assignment = []
        self.vmap = set()
        self.updates = [set() for _ in range (2 * (nvars+1))]
        self.watched_literal_to_clause = [set() for _ in range (2 * (nvars+1))]
        self.literal_to_clause = [set() for _ in range (2 * (nvars+1))]
        self.unit = []  # unit clauses

        for i, clause in enumerate(clauses):
            if clause.is_unit():
                self.unit.append(i)
            for literal in clause.inner:
                self.literal_to_clause[literal].add(i)
            for literal in clause.watched_literals:
                self.watched_literal_to_clause[literal].add(i)

    def add_watched_literal(self, idx, literal):
        clause = self.clauses[idx]
        self.watched_literal_to_clause[literal].add(idx)
        clause.watched_literals.add(literal)

    def remove_watched_literal(self, idx, literal):
        clause = self.clauses[idx]
        self.watched_literal_to_clause[literal].remove(idx)
        clause.watched_literals.remove(literal)

    # Update of literal i
    # Return True if conflict in updating watched literals
    def update_literal(self, i, literal):
        clause: Clause = self.clauses[i]
        if clause.is_true():
            return False
        clause.undecided.remove(literal)
        self.updates[literal].add(i)
        if literal in self.vmap:
            clause.true.add(literal)
            return False
        else:
            clause.false.add(literal)
        
        # Update watched literal
        if literal in clause.watched_literals:
            self.remove_watched_literal(i, literal)
            for new_literal in clause.undecided - clause.watched_literals:
                if (new_literal ^ 1) in self.vmap:
                    # False
                    clause.undecided.remove(new_literal)
                    self.updates[new_literal].add(i)
                    clause.false.add(new_literal)
                else:
                    # Undecided
                    self.add_watched_literal(i, new_literal)
                    break
        
        if clause.is_false():
            # Conflict in lazy false update
            return True
        
        if clause.is_unit():
            self.unit.append(i)
        return False
            
    def unit_prop(self):
        while self.unit:
            i = self.unit.pop()
            clause = self.clauses[i]
            if clause.is_true():
                continue
            
            # assert(clause.is_unit())
            literal = next(iter(clause.undecided))
            # assert(not (-literal in self.vmap))
            
            self.vmap.add(literal)
            self.assignment.append(Assignment.implication(literal, i))
            
            for j in copy(self.watched_literal_to_clause[literal ^ 1]):
                # Possible conflict
                if self.update_literal(j, literal ^ 1):
                    return j
            
            for j in self.literal_to_clause[literal]:
                # No conflict in True assignment
                self.update_literal(j, literal)

        return None
    
    
    def satisfied(self):
        for clause in self.clauses:
            if not clause.is_true():
                return False
        return True

    def learn_clause(self, conflict_clause: Clause):
        learned_clause: Clause = conflict_clause
        for assn in self.assignment.__reversed__():
            if assn.desc():  # Decision assignment
                continue
            if not learned_clause.exist(assn.literal):
                continue
            else:  # Implied assignment with var
                #print(f"Learning iter: {learned_clause}, {self.clauses[assn.idx]}")
                learned_clause = learned_clause.resolvent(assn.literal, self.clauses[assn.idx])

        n = len(self.clauses)

        for literal in learned_clause.inner:
            self.literal_to_clause[literal].add(n)
            self.updates[literal].add(n)
            # assert(-literal in self.vmap)
            learned_clause.false.add(literal)

        self.clauses.append(learned_clause)

        return learned_clause
    
    def backtrack(self, learned_clause: Clause):
        #print(self.assignment)
        while True:
            assn = self.assignment.pop()
            literal = assn.literal
            self.rollback_update(literal)

            if learned_clause.exist(literal):
                break
    
    def rollback_update(self, literal):
        self.vmap.remove(literal)
        while self.updates[literal]:
            i = self.updates[literal].pop()
            clause: Clause = self.clauses[i]
            clause.disassign(literal)
            if len(clause.watched_literals) < 2:
                self.add_watched_literal(i, literal)

        neg_literal = literal ^ 1
        while self.updates[neg_literal]:
            i = self.updates[neg_literal].pop()
            clause: Clause = self.clauses[i]
            clause.disassign(neg_literal)
            if len(clause.watched_literals) < 2:
                self.add_watched_literal(i, neg_literal)

    def decision(self):
        for clause in self.clauses:
            if not clause.is_true():
                # Watched literals are undecided and not target of lazy-evaluation
                literal = next(iter(clause.watched_literals))
                # assert(-literal not in self.vmap)
                self.vmap.add(literal)
                self.assignment.append(Assignment.decision(literal))
        
                # False updates
                for j in copy(self.watched_literal_to_clause[literal ^ 1]):
                    # Possible conflict
                    if self.update_literal(j, literal ^ 1):
                        # This is lazy-evaluated unit clause
                        self.rollback_update(literal)
                        self.assignment.pop()
                        self.unit.append(j)
                        return j
                
                for j in self.literal_to_clause[literal]:
                    # No conflict in True assignment
                    self.update_literal(j, literal)
                return None

    def run(self):
        preprocess = True
        while True:
            #print(self.unit)
            #print(f"Current Solution: {self.vmap}")
            #print(f"Assignments: {self.assignment}")
            
            conflict = self.unit_prop()
            #print(f"Clauses: {self.clauses}")
            #input()
            
            if preprocess:
                if conflict is not None:
                    return Solution(False)
                preprocess = False

            if self.satisfied():
                return Solution(True, self.vmap)

            if conflict is not None:
                self.unit.clear()
                # assert(self.clauses[conflict].is_false())
                learned_clause = self.learn_clause(self.clauses[conflict])
                if learned_clause.empty():
                    return Solution(False)
                self.backtrack(learned_clause)
                assert learned_clause.is_unit()
                self.unit.append(len(self.clauses)-1)
            else:
                self.decision()


if __name__ == "__main__":
    dpll = DPLL(*parse_problem(sys.argv[1]))
    result = dpll.run()
    print(result)
