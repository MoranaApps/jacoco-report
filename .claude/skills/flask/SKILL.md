---
name: flask
description: Practices for Python backends built on Flask - app factory, blueprints or Flask-RESTX namespaces, input validation, auth, SQLAlchemy sessions, background work and pytest. Use when adding or changing Flask endpoints, services or app setup, or reviewing such changes.
---

# Flask

Follow the project first. Read the backend's `CONTEXT.md` and one existing endpoint, and copy its shape: blueprint or namespace, schema library, service layer, error format. The project's conventions win over this list.

## Structure

- The app is built in an app factory (`create_app()`), which registers blueprints, namespaces and extensions. Nothing at import time may need a running app.
- Route handlers parse input, check access, call a service and serialize the result. Business rules live in services: plain functions or classes you can test without a request.
- Use the extensions the project already has (Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-Login and so on). Don't add a second one for the same job.
- Settings come from the config classes and environment variables. Never hard-code secrets, and never run with `debug=True` outside local development.

## Requests

- Validate input with the project's schema library (marshmallow, pydantic, Flask-RESTX models, WTForms). Bad input gets 400 or 422, never a 500.
- Check access on the specific record: load it, then check the current user may act on it. Use the project's auth decorators; don't parse tokens yourself.
- Return errors through `abort()` and the project's error handlers, in its error format. No tracebacks or SQL in responses.
- Keep the API contract accurate. If it is an OpenAPI file, update it in the same step as the endpoint. If Flask-RESTX or flask-smorest generates it from the code, keep the models and schemas complete, so the generated spec matches what the endpoint really does.
- Use `g`, `request` and `current_app` only inside a request or app context. Background threads don't have one.

## SQLAlchemy

- One session per request (`db.session`). Commit once per unit of work in the service, and roll back on error. Low-level helpers don't commit.
- Avoid N+1 queries: `selectinload` or `joinedload` the relationships you loop over.
- Use the ORM, or `text()` with bound parameters. Never build SQL with f-strings or `%`.
- Schema changes are Alembic migrations through Flask-Migrate. That is relational-database work.

## Background work and outbound calls

- Long-running work goes to the project's queue (Celery, RQ) or a CLI command (`@app.cli.command`), not into the request.
- Calls with `requests` or `httpx` always set a `timeout`.

## Tests

- Use pytest with the app factory's testing config and the fixtures in `conftest.py` (`app`, `client`, database).
- Unit-test service rules. Give each new or changed endpoint tests through `client` for success, bad input (400 or 422), no login (401), wrong user (403) and missing record (404).
- Use the project's test database, not a mocked session.

## Stop and report before

- a breaking change to an endpoint's request or response,
- adding a Flask extension or other dependency,
- changing authentication, sessions or token handling,
- a schema change (relational-database-developer's work).
