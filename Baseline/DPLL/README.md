# SAT Solver for CNF formulas

It is well-known that every boolean satisfiability problem (SAT) can be reduced to a conjunctive normal formula (CNF). Therefore it is common to write a solver for CNF formulas to solve SAT in general.

## 1. Design Choices
- [ ] Variable Elimination
- [x] DPLL Algortihm
- [x] Encode positive and negative literals into natrual numbers (inspired by Art of Computer Programming 4B, Donald Knuth)
- [x] Watched Literals
- [x] Decision heurisitic to choose any undecided literal in undecided clause
- [ ] Random Restart

## 2. Clause Data Structure

In order to record the value of each literal in clauses as undecided/true/false, `Clause` has five sets - inner, undecided, true, false, and watched_literals. The set data structure was used to do fast add, delete, and existence checks of any literals.

Inspired by Art of Computer Programming 4B (Donald Knuth), it encodes each literal to a natural number by mapping positive literal $p$ as $2p$ and negative literal $\neg p$ as $2p+1$. Then the negation is equvalent to doing **xor** with 1 for all literals.

## 3. Main Routine

I defined `DPLL` class to implement the DPLL algorithm. It has several class attributes to use DPLL algorithms.

- clauses: It is the list of clauses of this problem . New clauses are added when it runs the clause learning algorithm.
- assignment: The list that collects every implication and decision information. It is used in the clause learning algorithm.
- vmap: the partial solution that it searched so far.
- updates: For each literal, it maintains in which clause the literal is updated. It is used when it rollbacks the updates after backtracking.
- watched_literal_to_clause: For each literal, it keeps the information in which clause the literal is configured as watched literals.
- literal_to_clause: For each literal, it keeps in which clause the literal exists.

### 3.1.  The DPLL Algorithm

```python
preprocess = True
while True:
    conflict = self.unit_prop()
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
        self.unit.append(len(self.clauses)-1)
    else:
        self.decision()
```

In the while loop, it first runs unit propagation. If a conflict occurs in the first iteration, the problem itself is unsatisfiable. Otherwise, if every clause is satisfied, the problem is solved so return the satisfying partial assignment. If a conflict exists, run the clause learning algorithm and mark the newly learned clause as the unit clause which is used in the next unit propagation. If there was no conflict, run the decision algorithm.

### 3.2. Unit Propagation with Watched Literals

```python
while self.unit:
    i = self.unit.pop()
    clause = self.clauses[i]
    if clause.is_true():
        continue
    
    literal = next(iter(clause.undecided))
    
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
```

Suppose literal $L$ remains as undecided in the unit clause. Unit propagation step updates this literal as true. In a simple way, the solver updates $L$ and $\overline{L}$ in every clause. My algorithm updates $L$ in every clause, but not $\overline{L}$. Only if $\overline{L}$ is a watched literal, it update $\overline{L}$ as false. This lazy false-updating strategy is adopted because assigning true to literal is important to decide the satisfiability, but assigning false is not that interesting.  False is important only when the change makes the clause unit or false. This is the core idea of watched literals. By keep watching only two literals, it makes us reduce the resource for updates and backtracking.

To check the effectiveness of watched literals, I checked the time spent by my solver for the four example cases.

|  | 6_SAT | 7_UNSAT | 8_UNSAT | 9_SAT |
| --- | --- | --- | --- | --- |
| unit propagation with watched literals | 0.03s | 4.55s | 0.37s | 1.14s |
| unit propagation updating all literals  | 1.19s | 11.75s | 1.00s | 0.04s |

The performance improved for three cases, especially 7_UNSAT performance is gained from 11.75s to 4.55s. The performance dropped for 9_SAT - from 0.04s to 1.14s. It needs more study to inspect the reason. Overall, I think watched literals technique is beneficial, hence I decided to use watched literals as default.

## 4. Formats of Input and Output

I slightly modified the homework instruction found in https://github.com/hongseok-yang/logic23. This was a homework of Introduction to Logic for Computer Science course in KAIST, Spring 23.

* It follows DIMACS input/output requirements. You can learn about these requirements at the following URL: [http://www.satcompetition.org/2009/format-benchmarks2009.html](http://www.satcompetition.org/2009/format-benchmarks2009.html). This is the format used in the SAT competition. 
* Assume that the input is always in CNF format.

### 4.1. Input Interface

To run the solver with cnf problem "test.cnf", the corresponding command is:

* python3 solve.py "testn.cnf"

### 4.2. Output Interface

The output specifies SATISFIABLE/UNSATISFIABLE using s and give a partial assignment using v. So, if solver is run

```
python3 solve.py "test1.cnf"
```

but "test1.cnf" is unsatisfiable and the solver finds this out, it returns

```
s UNSATISFIABLE
```

in the standard output. On the other hand, if the solver is run

```
python3 solvepy3.py "test2.cnf"
```

but "test2.cnf" is satisfiable and the solver finds a satisfying partial assignment (2, 5, -7) meaning that variables 2 and 5 have the value 1 and the variable 7 has the value -1 in the found partial assignment, then the solver returns

```
s SATISFIABLE
v 2 5 -7 0
```

Here 0 indicates the end of the found partial assignment.
