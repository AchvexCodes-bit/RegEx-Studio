# Algorithms and supported semantics

The engine is pure Python and independent of Django. Its recursive-descent parser applies atom/group, quantifier, concatenation, and alternation precedence. Each AST node retains source offsets. Thompson construction emits epsilon transitions for concatenation, alternation, and repetition. Epsilon closure uses a visited set, preventing cycles from looping forever. NFA simulation tracks a set of active states at each input position.

DFA conversion uses subset construction over a documented ASCII alphabet (code points 0–127). It intentionally does not claim complete Unicode semantics. DFA minimization uses iterative partition refinement and treats missing transitions as an implicit rejecting sink for partition signatures; only reachable subsets are emitted by subset construction.

Limits: pattern 512 characters, repetition bound 32, 1,200 automaton states, and 4,096 input characters. The first release supports literals, groups, alternation, classes/ranges, dot, ASCII shorthand classes, escapes, and repetition. Anchors, lookaround, backreferences, and capture tracking are not supported by automaton mode. Native JavaScript matching is a separate mode and does not expose a fabricated automaton trace.
