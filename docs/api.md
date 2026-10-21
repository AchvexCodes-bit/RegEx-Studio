# API reference

The current API is intentionally small and unauthenticated. It does not persist data.

## GET /api/v1/health/
Returns {"status":"ok","service":"regex-studio"}.

## POST /api/v1/automata/compile/
JSON request: {"pattern":"(ab|c)+\\d{2}"}.

Returns AST nodes with source offsets, NFA state/transition records, and DFA/minimized-DFA state counts, accepting state IDs, and transition maps. Invalid syntax returns HTTP 400 with an error and source position. Request bodies over 16 KiB return HTTP 413.

## POST /api/v1/automata/simulate/
JSON request: {"pattern":"a+","input":"aaa"}.

Returns full-string acceptance, a bounded trace with active state sets at each input position, and state count. Input is limited to 4,096 characters. Unsupported patterns return HTTP 400.

## Operational notes
The compute endpoints are stateless and CSRF-exempt because they do not mutate session or database state. Add infrastructure-level rate limiting before public deployment. Authentication, saved workspaces, share links, and persistent account data are not part of the current API.
