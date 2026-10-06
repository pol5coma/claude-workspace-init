"""Default CLAUDE.md content proposals."""

DEFAULT_SAFETY = [
    "Never perform destructive database operations, irreversible migrations, force resets, "
    "data deletion or infrastructure destruction without explicit user approval.",
    "When a conflict or unexpected state appears, investigate first and ask before taking an "
    "irreversible action.",
]

# Dangerous commands proposed per detected technology (spec 7.1).
DANGEROUS_COMMANDS_BY_TECH: dict[str, list[str]] = {
    "prisma": ["prisma migrate reset", "prisma db push --force-reset"],
    "alembic": ["alembic downgrade base"],
    "django": ["python manage.py flush"],
    "terraform": ["terraform destroy"],
    "mongodb": ["db.dropDatabase()"],
    "postgresql": ["DROP DATABASE / DROP TABLE / TRUNCATE"],
    "mysql": ["DROP DATABASE / DROP TABLE / TRUNCATE"],
    "docker compose": ["docker compose down -v"],
    "kubernetes": ["kubectl delete namespace"],
}
ALWAYS_DANGEROUS = ["git push --force", "git reset --hard", "rm -rf"]
