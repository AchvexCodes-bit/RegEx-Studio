# Delivery roadmap

## Implemented in this foundation
- Pure Python recursive-descent parser and AST with source spans.
- Thompson NFA, epsilon closure, full-input simulation and trace.
- NFA-to-DFA subset construction over ASCII and partition-refinement minimization.
- Django health, compile, and simulation endpoints with request-size and algorithm limits.
- Browser workspace with native JavaScript tester, SVG NFA, and trace controls.
- Unit tests for representative parser/compiler/matching cases.

## Not yet implemented
- PostgreSQL production configuration and migrations for user workspaces, saved patterns, collections, versions, and shares.
- Full registration/password-reset UI and object-level persistence permissions.
- Full bounded backtracking VM, native regex worker timeout, lessons/challenge evaluation, and account dashboard.
- Full end-to-end browser test suite, comprehensive accessibility audit, and production deployment verification.

These features must not be advertised as complete until implemented and tested.
