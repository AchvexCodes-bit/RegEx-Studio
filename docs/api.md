# API reference

The API serves the browser workbench and its session-backed user workspace. JSON body limits are enforced by the API handlers.

## GET /api/v1/health/

Returns the service health payload, for example {"status":"ok","service":"regex-studio"}.

## POST /api/v1/automata/compile/

JSON request: {"pattern":"(ab|c)+\\d{2}"}.

Returns AST nodes with source offsets, NFA state/transition records, and DFA/minimized-DFA state counts, accepting state IDs, transition maps, and minimization groups. Invalid syntax returns HTTP 400 with an error and source position. Request bodies over 16 KiB return HTTP 413.

## POST /api/v1/automata/simulate/

JSON request: {"pattern":"a+","input":"aaa"}.

Returns full-string acceptance, a trace with active state sets at each input position, and state count. Input is limited to 4,096 characters. Unsupported patterns return HTTP 400.

## Account/session endpoints

Account mutations require Django's CSRF protection. First request GET /api/v1/auth/csrf/ and send the csrftoken cookie value in the X-CSRFToken header on later POSTs. Session cookies must be retained by the client.

- GET /api/v1/auth/csrf/ — initializes the CSRF cookie.
- GET /api/v1/auth/me/ — returns the current account or authenticated=false.
- POST /api/v1/auth/register/ — accepts username, optional email, and a password of at least eight characters; creates the account and signs in.
- POST /api/v1/auth/login/ — accepts username and password.
- POST /api/v1/auth/logout/ — ends the session.

Passwords are hashed through Django's user model. Account data is stored in the configured database.

## Saved pattern workspace

Saved patterns belong to a single account; list, update, and delete operations always filter by the authenticated owner. Anonymous workspace calls return HTTP 401. Account/workspace state-changing requests require a valid CSRF token.

- GET /api/v1/patterns/ — list the current user's patterns. Optional q searches both name and expression; favorites=1 filters favorites. The response includes at most 100 patterns.
- POST /api/v1/patterns/ — create an item with name, pattern, flags, replacement, test_input, and optional is_favorite. Names are unique case-insensitively per user; an account may store at most 100 items.
- PATCH /api/v1/patterns/<id>/ — update one or more saved fields, including is_favorite.
- DELETE /api/v1/patterns/<id>/ — delete an owned saved item.

Names are limited to 80 characters, patterns and replacement text to 512 characters, test input to 4,096 characters, flags to the JavaScript flag alphabet with duplicate and u/v-combination checks, and request bodies to 16 KiB. A resource owned by another user is reported as not found.

## Security and deployment notes

The automata compute endpoints are stateless and CSRF-exempt; account and workspace endpoints are not exempt. Configure HTTPS, a strong SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, durable storage, operational backups, and explicit rate limiting before public deployment. The native JavaScript regex tester uses the browser's RegExp engine, and arbitrary expressions are not guaranteed to have bounded execution time.
