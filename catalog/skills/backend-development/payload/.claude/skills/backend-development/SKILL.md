---
name: backend-development
description: Conventions for backend work (API endpoints, request validation, error handling, persistence, migrations, background jobs). Use when adding or changing endpoints, services, models, queries or migrations.
---

# Backend development

## Before changing code

- Find an existing endpoint or service that does something similar and follow its structure, naming and error handling.
- Read the project's architecture pointer in CLAUDE.md (if any) before adding a new layer, module or dependency.
- Load the framework reference only when needed:
  - FastAPI: [references/fastapi.md](references/fastapi.md)
  - Django: [references/django.md](references/django.md)
  - Express / Node: [references/express.md](references/express.md)

## Endpoints

- Validate every input at the boundary with the project's schema tool (Pydantic, serializers, zod…). Never trust client data.
- Keep handlers thin: parse → call a service/function → map the result to a response.
- Return consistent error shapes and correct status codes (400 validation, 401/403 auth, 404 missing, 409 conflict, 422 semantic). Never leak stack traces or internal identifiers.
- Enforce authorization on the server for every resource access, not only authentication.
- Paginate list endpoints. Bound every query.

## Persistence

- Use the ORM / query builder already in the project. Parameterize all raw SQL.
- Avoid N+1 queries: eager-load relations used in loops.
- Wrap multi-step writes in a transaction.
- Schema changes go through migrations (Alembic, Django, Prisma…). Generate them, read the generated file, and never edit an applied migration.
- **Never** run destructive database commands (reset, drop, truncate, force push of schema) without explicit user approval.

## Reliability

- Make external calls with timeouts and handle failure explicitly.
- Background jobs must be idempotent and safe to retry.
- Log with context (request id, entity id), never secrets or personal data.
- Read configuration from environment/config modules; never hard-code credentials.

## Done means

- Tests cover the happy path, validation failures and authorization for the changed endpoint.
- New configuration or environment variables are documented where the project documents them.
