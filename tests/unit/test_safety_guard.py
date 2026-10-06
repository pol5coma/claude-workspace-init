"""Allow/deny matrix for the Safety Guard hook, executed as Claude Code would run it."""

import json
import subprocess
import sys

import pytest

from tests.helpers import REAL_CATALOG

GUARD = (
    REAL_CATALOG / "hooks" / "safety-guard" / "payload" / ".claude" / "hooks" / "safety-guard.py"
)


def run_guard(project, tool_name, tool_input, env_extra=None):
    payload = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "cwd": str(project),
        "hook_event_name": "PreToolUse",
    }
    env = {
        "CLAUDE_PROJECT_DIR": str(project),
        "PATH": "/usr/bin:/bin",
        "HOME": str(project / "home"),
    }
    env.update(env_extra or {})
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return result.returncode, result.stderr


def bash(project, command):
    return run_guard(project, "Bash", {"command": command})


BLOCKED = [
    "terraform destroy",
    "terraform destroy -auto-approve",
    "tofu destroy",
    "terraform apply -destroy",
    "pulumi destroy --yes",
    "prisma migrate reset",
    "npx prisma migrate reset --force",
    "pnpm exec prisma db push --force-reset",
    "prisma db push --accept-data-loss",
    "dropdb production",
    "psql -c 'DROP DATABASE app'",
    'psql $DATABASE_URL -c "drop table users"',
    "mysql -e 'TRUNCATE orders'",
    "psql -c 'DELETE FROM users'",
    "mongosh --eval 'db.dropDatabase()'",
    "redis-cli FLUSHALL",
    "alembic downgrade base",
    "uv run alembic downgrade base",
    "python manage.py flush --noinput",
    "./manage.py reset_db",
    "rails db:drop",
    "docker compose down -v",
    "docker-compose down --volumes",
    "docker volume rm pgdata",
    "docker system prune -a --volumes",
    "kubectl delete namespace prod",
    "kubectl delete pods --all",
    "aws s3 rb s3://bucket --force",
    "aws s3 rm s3://bucket --recursive",
    "git push --force",
    "git push -f origin main",
    "git push origin +main",
    "git reset --hard HEAD~3",
    "git clean -fdx",
    "git checkout -- .",
    "git restore .",
    "git stash clear",
    "rm -rf /",
    "rm -rf ~",
    "rm -rf $HOME",
    "rm -rf .",
    "rm -rf ..",
    "rm -rf *",
    "rm -rf .git",
    "rm -fr /usr/local/lib",
    "sudo rm -rf /var/lib/postgresql",
    "rm --recursive --force /",
    "rm -rf --no-preserve-root /",
    "ls && terraform destroy",
    "echo ok; rm -rf /",
    "true || dropdb x",
    "ls\nterraform destroy",
    "bash -c 'terraform destroy'",
    'sh -c "git push --force"',
    "eval 'rm -rf /'",
    "echo $(dropdb prod)",
    "FOO=1 terraform destroy",
    "env AWS_PROFILE=prod terraform destroy",
    "timeout 60 terraform destroy",
    "mkfs.ext4 /dev/sda1",
    "dd if=/dev/zero of=/dev/disk2",
    "echo SECRET=1 > .env",
    "cat x >> .env.production",
    "rm .env",
    "mv .env /tmp/env-backup",
    "sed -i 's/a/b/' .env",
    ":(){ :|:& };:",
]

ALLOWED = [
    "git status",
    "git push",
    "git push --force-with-lease",
    "git reset --soft HEAD~1",
    "git clean -n",
    "git restore --staged .",
    "git checkout main",
    'echo "do not run terraform destroy"',
    "echo 'prisma migrate reset is dangerous'",
    "grep -r 'DROP TABLE' migrations/",
    "terraform plan",
    "terraform apply",
    "prisma migrate dev",
    "prisma db push",
    "alembic upgrade head",
    "alembic downgrade -1",
    "python manage.py migrate",
    "docker compose down",
    "docker compose up -d",
    "kubectl get pods",
    "rm -rf node_modules",
    "rm -rf ./dist build",
    "rm -rf /tmp/cwi-scratch",
    "rm file.txt",
    "rm .env.example",
    "cat .env.example",
    "cp README.md docs/README.md",
    "psql -c 'SELECT 1'",
    "psql -c 'DELETE FROM users WHERE id = 1'",
    "npm test",
    "uv run pytest -x",
    "ls -la > listing.txt",
    "python3 script.py 2>&1 | tee out.log",
]


@pytest.mark.parametrize("command", BLOCKED)
def test_blocks_destructive_commands(tmp_path, command):
    code, stderr = bash(tmp_path, command)
    assert code == 2, f"expected block for {command!r}"
    assert "CWI Safety Guard blocked" in stderr
    assert "explicit approval" in stderr


@pytest.mark.parametrize("command", ALLOWED)
def test_allows_safe_commands(tmp_path, command):
    code, stderr = bash(tmp_path, command)
    assert code == 0, f"unexpected block for {command!r}: {stderr}"


def test_rm_outside_project_blocked_inside_allowed(tmp_path):
    project = tmp_path / "project"
    (project / "generated").mkdir(parents=True)
    assert bash(project, f"rm -rf {project}/generated")[0] == 0
    assert bash(project, f"rm -rf {project}")[0] == 2
    assert bash(project, "rm -rf /srv/other-project")[0] == 2


@pytest.mark.parametrize(
    "path,blocked",
    [
        (".env", True),
        (".env.local", True),
        ("config/.env.production", True),
        (".env.example", False),
        ("certs/server.pem", True),
        ("deploy/id_rsa", True),
        (".git/config", True),
        (".claude/cwi-state.json", True),
        (".claude/hooks/safety-guard.py", True),
        ("src/app.py", False),
        (".claude/settings.json", False),
    ],
)
def test_edit_protection(tmp_path, path, blocked):
    code, stderr = run_guard(tmp_path, "Write", {"file_path": str(tmp_path / path), "content": "x"})
    assert (code == 2) is blocked, stderr
    code, _ = run_guard(tmp_path, "Edit", {"file_path": path, "old_string": "a", "new_string": "b"})
    assert (code == 2) is blocked


def test_project_overrides(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "safety-guard.json").write_text(
        json.dumps(
            {
                "protected_paths": ["config/production.yml"],
                "allow_paths": [".env.local"],
                "disabled_rules": ["git-reset-hard"],
                "allow_commands": ["^terraform destroy -target=module\\.scratch"],
            }
        )
    )
    assert run_guard(tmp_path, "Write", {"file_path": "config/production.yml"})[0] == 2
    assert run_guard(tmp_path, "Write", {"file_path": ".env.local"})[0] == 0
    assert bash(tmp_path, "git reset --hard")[0] == 0
    assert bash(tmp_path, "terraform destroy -target=module.scratch")[0] == 0
    assert bash(tmp_path, "terraform destroy")[0] == 2


def test_other_tools_pass_through(tmp_path):
    assert run_guard(tmp_path, "Read", {"file_path": ".env"})[0] == 0
    assert run_guard(tmp_path, "WebFetch", {"url": "https://example.com"})[0] == 0


def test_invalid_input_is_non_blocking(tmp_path):
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input="{broken",
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(tmp_path)},
    )
    assert result.returncode == 1


def test_unbalanced_quotes_still_checked(tmp_path):
    assert bash(tmp_path, "terraform destroy 'unterminated")[0] == 2


def test_rules_are_data():
    import importlib.util

    spec = importlib.util.spec_from_file_location("cwi_safety_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    sys.modules["cwi_safety_guard"] = module
    spec.loader.exec_module(module)
    names = [r.name for r in module.DANGEROUS_RULES]
    assert len(names) == len(set(names))
    assert "terraform-destroy" in names
