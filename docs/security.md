# Security notes

- Pattern length is limited to 512 characters, repetition bounds to 32, NFA/DFA states to 1,200, simulation input to 4,096 characters, and HTTP JSON bodies to 16 KiB.
- The API uses POST for compile/simulation, rejects malformed types, and applies Django REST Framework's anonymous throttle defaults to DRF endpoints. The current plain Django views do not inherit DRF throttling automatically; deploy behind a reverse proxy rate limiter until these views are moved to DRF throttled APIViews.
- Do not expose the development settings to production. Set a strong SECRET_KEY, DEBUG=false, ALLOWED_HOSTS, HTTPS, secure cookies, CSRF trusted origins, and a production database before deployment.
- Native JavaScript regular expressions may consume excessive CPU on pathological patterns. This initial UI does not yet isolate native matching in a Web Worker, so only test trusted patterns and bounded input.
- Authentication, persistent private workspaces, sharing permissions, and production data-retention controls are not implemented yet. Do not store confidential patterns in a server deployment until those controls exist.
