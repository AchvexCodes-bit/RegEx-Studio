# RegEx Studio

**See every state. Understand every match.**

RegEx Studio is a regex workbench with a native JavaScript tester and a separate bounded ASCII automata engine. Its workspace supports accounts and a private, persistent library of saved patterns.

## Features

- **Native regex tester:** ECMAScript flags, global matches, capture groups, named groups, offsets, match highlighting, and replacement preview.
- **Automata compiler:** supported patterns parse into an AST, compile to a Thompson NFA, convert to DFA, and minimize. The models remain separate from the browser's JavaScript regex engine.
- **Visual debugger:** SVG NFA/DFA/minimized DFA graphs, selectable states, full-string simulation, and trace stepping.
- **User accounts:** create an account, sign in, view session status, and sign out. Passwords are handled by Django's password hashing.
- **Private saved-pattern workspace:** create, list, search, load, favorite, rename, and delete saved patterns. A saved item preserves the expression, flags, replacement, and test input. Names are unique per account and each account can store up to 100 patterns.
- **Responsive UI:** animated panels and controls, startup/scroll reveals, and reduced-motion support.
- **API safeguards:** bounded JSON payloads, explicit validation, CSRF protection on account/workspace endpoints, and owner-scoped pattern access.
- **Regression checks:** engine algorithms, API behavior, account flows, ownership/privacy, CSRF behavior, frontend DOM references and JavaScript syntax are covered by tests or CI checks.

## Quick start

Use Python 3.11 or newer. Django's default SQLite database is used for local development.

~~~bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
~~~

Open http://127.0.0.1:8000, create an account, and save a pattern from the workspace panel. Account and saved-pattern records persist in the local database. Run the server for automaton APIs and account functions; a static file server alone only supports the browser-native tester.

## Tests and checks

~~~bash
# Core regex engine tests
python -m unittest discover -s tests -p 'test_engine.py' -v

# Django API, account, workspace, and frontend smoke tests
python manage.py test tests -v 2

# Schema and framework checks
python manage.py makemigrations --check --dry-run
python manage.py check

# Frontend JavaScript syntax and DOM reference check (requires Node.js)
python scripts/check_frontend.py
~~~

GitHub Actions runs these checks on pushes and pull requests to main.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | /api/v1/health/ | Service health |
| POST | /api/v1/automata/compile/ | AST, NFA, DFA, minimized DFA |
| POST | /api/v1/automata/simulate/ | Full-match result and step trace |
| GET | /api/v1/auth/csrf/ | Initialize a CSRF cookie |
| GET | /api/v1/auth/me/ | Current session account |
| POST | /api/v1/auth/register/ | Register and sign in |
| POST | /api/v1/auth/login/ | Sign in |
| POST | /api/v1/auth/logout/ | Sign out |
| GET, POST | /api/v1/patterns/ | List/search or save own patterns |
| PATCH, DELETE | /api/v1/patterns/{id}/ | Update/favorite or delete an owned pattern |

Account and saved-pattern mutations use Django session authentication and require the X-CSRFToken header from the csrftoken cookie. Saved pattern lookups are always scoped to the authenticated owner.

## Automaton grammar and limitations

Supports literals, escaped punctuation, groups, alternation, concatenation, ., character classes/ranges/negation, \d \D \w \W \s \S, \n \r \t, and * + ? {m} {m,} {m,n}. Automaton mode is ASCII-only and performs **full-string recognition**. Outer ^ and $ are accepted as redundant full-match anchors; multiline/context-dependent anchors, lookarounds, backreferences, captures, and flavor-specific Unicode behavior are not implemented. Use Native Tester for browser-supported JavaScript syntax.

The browser-native regex tester uses JavaScript's built-in RegExp engine. This project does not promise that arbitrary expressions have bounded execution time. Avoid running untrusted expressions against sensitive or very large inputs.

## Production readiness

This is an application foundation, not a reviewed production deployment. Before public deployment, configure a strong SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, HTTPS and secure cookies, operational database backups, rate limiting for account/automata endpoints, error monitoring, and a production database. Review the deployment and security notes in docs.
