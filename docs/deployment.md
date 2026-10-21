# Setup and deployment

## Local development

1. Install Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run `python manage.py migrate`.
5. Run `python manage.py check`.
6. Run `python -m unittest discover -s tests -p 'test_engine.py' -v`.
7. Run `python manage.py test tests.test_api -v 2`.
8. Start with `python manage.py runserver` and open http://127.0.0.1:8000.

The Django server serves the UI at / and the API at /api/v1/. A static server can run the native tester, but automata compilation and trace simulation require the Django API.

## Production readiness

This repository is not production-ready. Before deployment:
- Set a cryptographically random SECRET_KEY, DEBUG=false, and strict ALLOWED_HOSTS.
- Configure a production database, backups, migration automation, and static asset strategy.
- Terminate TLS at a trusted reverse proxy and configure HTTPS and CSRF trusted origins.
- Add request-rate limiting to the stateless compute endpoints at the proxy or application layer.
- Configure structured logging, monitoring, error reporting, and security headers.
- Implement authentication, private workspace ownership, sharing authorization, and data-retention controls before storing user data.
- Move native regex evaluation into a worker with a timeout strategy before allowing untrusted large inputs.
- Run the CI workflow and verify deployment health before announcing a release.

Do not use the development SECRET_KEY or DEBUG=true in production.
