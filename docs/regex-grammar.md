# Regex grammar

Automaton mode uses an ASCII alphabet (U+0000 through U+007F) and recognizes the **entire input**. It is not intended to emulate JavaScript backtracking or search semantics.

Supported:
- Literal ASCII characters and escaped punctuation.
- Groups (expression), alternation a|b, concatenation.
- Character classes [abc], ranges [a-z], and negated classes [^0-9].
- Wildcard ., excluding LF and CR.
- ASCII \d, \w, \s and their uppercase complements.
- Escaped newline, carriage return, tab, form feed, vertical tab.
- Greedy-agnostic language quantifiers *, +, ?, {m}, {m,}, {m,n}. Repetition bounds are capped at 32.

Unsupported and explicitly rejected:
- Start/end anchors, lookahead/lookbehind, backreferences, named groups, capture semantics, lazy quantifiers, Unicode property escapes, and flavor-specific extensions.
- Shorthand character classes inside a character class (for example [\d]) are not supported by the automaton parser yet.
- Non-ASCII input characters are rejected by automaton simulation. The browser's native JavaScript tester supports syntax and Unicode behavior implemented by that browser.

Parser limits: pattern length 512 characters, maximum repetition bound 32, NFA/DFA state cap 1,200, simulation input cap 4,096 characters. These limits are implementation safeguards, not regex-language standards.
