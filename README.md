# RegEx Studio

**See every state. Understand every match.**

A developer-focused regular-expression playground with a real parser, Thompson NFA compiler, DFA conversion/minimization, SVG automaton view, step debugger, and a separate native JavaScript regex tester.

> This repository was empty when implementation began. The first milestone focuses on a working, independently testable automata engine and responsive browser workspace. Authentication, persistence, lessons/challenges, and production deployment are staged follow-up work; they are not claimed complete by this initial commit.

## Quick start

The playground is static and can run without a server:

```bash
python -m http.server 8000
```

Open <http://localhost:8000>. For the Python API, use Python 3.11+:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Current functionality

- Native JavaScript regex tester: flags, global matches, captures, replacement preview, and safe zero-length iteration.
- Automaton mode: supported regex subset parsed into an AST, compiled to Thompson NFA, simulated over the full input, converted to DFA, and minimized.
- SVG graph with state selection, fit/reset, NFA/DFA/minimized DFA views, and execution trace stepping.
- Resource limits and explicit unsupported-syntax errors.
- Django health and compile API foundation.

## Automaton grammar

Supports literals, escaped punctuation, groups, alternation, concatenation, `.`, character classes/ranges/negation, `\\d \\D \\w \\W \\s \\S`, `\\n \\r \\t`, and `* + ? {m} {m,} {m,n}`. Automaton matching is **full-string recognition**. Anchors, lookarounds, backreferences, captures, and flavor-specific Unicode behavior are not implemented in this first engine milestone; unsupported constructs should be reported rather than silently approximated. Use Native Tester for browser-supported JavaScript syntax.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Security and limitations

The browser-native tester uses JavaScript's RegExp engine and cannot promise that every regex is cheap to execute. Keep input bounded when testing untrusted patterns. The automaton engine applies pattern, repetition, state, and input limits. Do not deploy the Django API publicly until production settings, rate limiting, account permissions, persistence, and deployment checks are completed.

See `docs/algorithms.md` and `docs/roadmap.md` for implementation details and remaining scope.