# Django reference

- Business logic lives in models/managers/services, not in views or templates.
- Use `select_related` / `prefetch_related` to avoid N+1 queries; check with `django-debug-toolbar` or `assertNumQueries`.
- Forms / DRF serializers validate input. Never use `request.POST` values unvalidated.
- Migrations: `python manage.py makemigrations` then review the file; `migrate` applies. Never edit applied migrations; never run `flush` or `reset_db` without approval.
- Settings split per environment; secrets from environment variables.
- Permissions: DRF permission classes or `@permission_required`; check object-level access.
- Tests: `pytest-django` or `manage.py test`; use factories over fixtures for model data.
