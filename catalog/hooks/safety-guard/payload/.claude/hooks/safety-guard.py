#!/usr/bin/env python3
"""CWI Safety Guard: a deterministic Claude Code PreToolUse hook.

Blocks clearly destructive shell commands and edits to protected files before they run.
It parses commands (it does not grep raw text), so `echo "do not run terraform destroy"`
is allowed while `terraform destroy` is blocked.

Exit codes (Claude Code hook contract):
  0  allow
  2  block; stderr is shown to Claude as the reason
  1  internal error; non-blocking, the tool call proceeds

Project overrides (optional) live in .claude/safety-guard.json:
  {
    "protected_paths": ["config/production.yml"],
    "allow_paths": [".env.local"],
    "allow_commands": ["^rm -rf \\\\./tmp/"],
    "disabled_rules": ["git-reset-hard"]
  }
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# ---------------------------------------------------------------------------------------------
# Rules (data)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    name: str
    executables: tuple[str, ...]
    reason: str
    subcommand: tuple[str, ...] = ()  # leading positional args, e.g. ("migrate", "reset")
    flags_any: tuple[str, ...] = ()  # at least one of these flags must be present
    flags_none: tuple[str, ...] = ()  # none of these flags may be present


DANGEROUS_RULES: tuple[Rule, ...] = (
    Rule(
        "terraform-destroy",
        ("terraform", "tofu", "terragrunt"),
        "destroys infrastructure managed by Terraform",
        ("destroy",),
    ),
    Rule(
        "terraform-apply-destroy",
        ("terraform", "tofu", "terragrunt"),
        "destroys infrastructure managed by Terraform",
        ("apply",),
        flags_any=("-destroy", "--destroy"),
    ),
    Rule("pulumi-destroy", ("pulumi",), "destroys infrastructure managed by Pulumi", ("destroy",)),
    Rule("cdk-destroy", ("cdk",), "destroys AWS CDK stacks", ("destroy",)),
    Rule(
        "serverless-remove",
        ("serverless", "sls"),
        "removes a deployed Serverless service",
        ("remove",),
    ),
    Rule(
        "prisma-migrate-reset",
        ("prisma",),
        "drops and recreates the database (all data lost)",
        ("migrate", "reset"),
    ),
    Rule(
        "prisma-db-push-reset",
        ("prisma",),
        "can drop data to force the schema",
        ("db", "push"),
        flags_any=("--force-reset", "--accept-data-loss"),
    ),
    Rule("dropdb", ("dropdb",), "drops a PostgreSQL database"),
    Rule(
        "alembic-downgrade-base",
        ("alembic",),
        "reverts every migration (destroys schema and data)",
        ("downgrade", "base"),
    ),
    Rule("django-flush", ("manage.py",), "deletes all data from the database", ("flush",)),
    Rule("django-reset-db", ("manage.py",), "drops and recreates the database", ("reset_db",)),
    Rule("rails-db-drop", ("rails", "rake"), "drops the database", ("db:drop",)),
    Rule("rails-db-reset", ("rails", "rake"), "drops and recreates the database", ("db:reset",)),
    Rule("rails-db-purge", ("rails", "rake"), "empties the database", ("db:purge",)),
    Rule(
        "docker-system-prune-volumes",
        ("docker",),
        "deletes Docker volumes (persistent data)",
        ("system", "prune"),
        flags_any=("--volumes",),
    ),
    Rule(
        "docker-volume-rm",
        ("docker",),
        "deletes Docker volumes (persistent data)",
        ("volume", "rm"),
    ),
    Rule(
        "docker-volume-prune",
        ("docker",),
        "deletes Docker volumes (persistent data)",
        ("volume", "prune"),
    ),
    Rule(
        "docker-compose-down-volumes",
        ("docker",),
        "deletes Compose volumes (persistent data)",
        ("compose", "down"),
        flags_any=("-v", "--volumes"),
    ),
    Rule(
        "docker-compose-v1-down-volumes",
        ("docker-compose",),
        "deletes Compose volumes (persistent data)",
        ("down",),
        flags_any=("-v", "--volumes"),
    ),
    Rule(
        "kubectl-delete-namespace",
        ("kubectl",),
        "deletes a namespace and everything in it",
        ("delete", "namespace"),
    ),
    Rule(
        "kubectl-delete-ns",
        ("kubectl",),
        "deletes a namespace and everything in it",
        ("delete", "ns"),
    ),
    Rule(
        "kubectl-delete-all",
        ("kubectl",),
        "bulk-deletes Kubernetes resources",
        ("delete",),
        flags_any=("--all", "-A", "--all-namespaces"),
    ),
    Rule("helm-uninstall", ("helm",), "removes a deployed release", ("uninstall",)),
    Rule(
        "aws-s3-rb-force",
        ("aws",),
        "deletes an S3 bucket and its contents",
        ("s3", "rb"),
        flags_any=("--force",),
    ),
    Rule(
        "aws-s3-rm-recursive",
        ("aws",),
        "recursively deletes S3 objects",
        ("s3", "rm"),
        flags_any=("--recursive",),
    ),
    Rule(
        "aws-rds-delete-instance",
        ("aws",),
        "deletes an RDS database",
        ("rds", "delete-db-instance"),
    ),
    Rule(
        "aws-rds-delete-cluster", ("aws",), "deletes an RDS cluster", ("rds", "delete-db-cluster")
    ),
    Rule(
        "aws-dynamodb-delete-table",
        ("aws",),
        "deletes a DynamoDB table",
        ("dynamodb", "delete-table"),
    ),
    Rule(
        "aws-cloudformation-delete-stack",
        ("aws",),
        "deletes a CloudFormation stack",
        ("cloudformation", "delete-stack"),
    ),
    Rule(
        "gcloud-projects-delete",
        ("gcloud",),
        "deletes a Google Cloud project",
        ("projects", "delete"),
    ),
    Rule(
        "gcloud-sql-delete",
        ("gcloud",),
        "deletes a Cloud SQL instance",
        ("sql", "instances", "delete"),
    ),
    Rule("az-group-delete", ("az",), "deletes an Azure resource group", ("group", "delete")),
    Rule(
        "git-reset-hard",
        ("git",),
        "discards uncommitted work irreversibly",
        ("reset",),
        flags_any=("--hard",),
    ),
    Rule("git-stash-clear", ("git",), "permanently drops every stash", ("stash", "clear")),
    Rule("supabase-db-reset", ("supabase",), "resets the database", ("db", "reset")),
    Rule(
        "mkfs",
        (
            "mkfs",
            "mkfs.ext4",
            "mkfs.ext3",
            "mkfs.xfs",
            "mkfs.vfat",
            "mkfs.fat",
            "mkfs.btrfs",
            "newfs",
        ),
        "formats a filesystem",
    ),
    Rule("wipefs", ("wipefs",), "erases filesystem signatures"),
    Rule("shred", ("shred",), "irreversibly overwrites files"),
    Rule("diskutil-erase", ("diskutil",), "erases a disk", ("eraseDisk",)),
    Rule("diskutil-erase-volume", ("diskutil",), "erases a volume", ("eraseVolume",)),
)

SQL_CLIENTS = (
    "psql",
    "mysql",
    "mariadb",
    "sqlite3",
    "mongosh",
    "mongo",
    "redis-cli",
    "sqlcmd",
    "clickhouse-client",
    "cockroach",
)
DESTRUCTIVE_SQL = re.compile(
    r"\bdrop\s+(database|schema|table|collection)\b|\btruncate\b|\bdropDatabase\s*\(|\.drop\s*\(\s*\)|\bflushall\b|\bflushdb\b",
    re.IGNORECASE,
)
DELETE_WITHOUT_WHERE = re.compile(r"\bdelete\s+from\s+[\w.\"`]+\s*(;|$)", re.IGNORECASE)

WRAPPERS = {
    "sudo",
    "doas",
    "env",
    "time",
    "nohup",
    "nice",
    "ionice",
    "command",
    "exec",
    "builtin",
    "caffeinate",
    "stdbuf",
    "timeout",
}
RUNNERS = {
    "npx": 0,
    "bunx": 0,
    "pnpx": 0,
    "uvx": 0,
}
RUNNER_SUBCOMMANDS = {
    "pnpm": ("exec", "dlx"),
    "yarn": ("dlx", "exec"),
    "npm": ("exec",),
    "bun": ("x",),
    "uv": ("run",),
    "poetry": ("run",),
    "pipenv": ("run",),
    "pdm": ("run",),
    "hatch": ("run",),
}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
CONTROL = {"&&", "||", ";", "|", "&", "(", ")", "\n", ";;", "|&"}
REDIRECTS = {">", ">>", ">|", "&>", "&>>", "<>"}

DEFAULT_PROTECTED = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    ".git/**",
    ".claude/cwi-state.json",
    ".claude/hooks/safety-guard.py",
    ".claude/safety-guard.json",
)
DEFAULT_ALLOWED = (".env.example", ".env.sample", ".env.template", ".env.dist", "*.env.example")


# ---------------------------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------------------------


@dataclass
class Config:
    project_dir: Path
    protected: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    allow_commands: tuple[re.Pattern[str], ...]
    disabled_rules: frozenset[str]


def load_config(project_dir: Path) -> Config:
    data: dict = {}
    path = project_dir / ".claude" / "safety-guard.json"
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            data = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            data = {}
    patterns = []
    for raw in data.get("allow_commands", []) or []:
        try:
            patterns.append(re.compile(str(raw)))
        except re.error:
            continue
    return Config(
        project_dir=project_dir,
        protected=DEFAULT_PROTECTED + tuple(str(p) for p in data.get("protected_paths", []) or []),
        allowed_paths=DEFAULT_ALLOWED + tuple(str(p) for p in data.get("allow_paths", []) or []),
        allow_commands=tuple(patterns),
        disabled_rules=frozenset(str(r) for r in data.get("disabled_rules", []) or []),
    )


# ---------------------------------------------------------------------------------------------
# Path protection
# ---------------------------------------------------------------------------------------------


def _relative(path_str: str, config: Config, cwd: Path) -> str:
    raw = os.path.expanduser(path_str)
    path = Path(raw) if os.path.isabs(raw) else (cwd / raw)
    try:
        resolved = Path(os.path.normpath(path))
        return resolved.relative_to(Path(os.path.normpath(config.project_dir))).as_posix()
    except ValueError:
        return Path(os.path.normpath(path)).as_posix()


def _matches(rel: str, pattern: str) -> bool:
    name = PurePosixPath(rel).name
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return rel == prefix or rel.startswith(prefix + "/") or f"/{prefix}/" in f"/{rel}/"
    if "/" in pattern:
        return fnmatch.fnmatchcase(rel, pattern)
    return fnmatch.fnmatchcase(name, pattern)


def protected_reason(path_str: str, config: Config, cwd: Path) -> str | None:
    rel = _relative(path_str, config, cwd)
    if any(_matches(rel, p) for p in config.allowed_paths):
        return None
    for pattern in config.protected:
        if _matches(rel, pattern):
            return f"`{rel}` is a protected path (matches `{pattern}`)"
    return None


# ---------------------------------------------------------------------------------------------
# Shell parsing
# ---------------------------------------------------------------------------------------------


def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def split_segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in CONTROL:
            segments.append([])
        else:
            segments[-1].append(token)
    return [s for s in segments if s]


def strip_prefix(segment: list[str]) -> list[str]:
    """Remove env assignments, wrappers (sudo, env, time…) and package runners (npx, uv run…)."""
    tokens = list(segment)
    changed = True
    while tokens and changed:
        changed = False
        while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens.pop(0)
            changed = True
        if not tokens:
            break
        head = os.path.basename(tokens[0])
        if head in WRAPPERS:
            tokens.pop(0)
            while tokens and tokens[0].startswith("-"):
                flag = tokens.pop(0)
                if (
                    flag in ("-u", "-g", "-n", "-c", "-s", "-k")
                    and tokens
                    and head in ("sudo", "nice", "timeout", "ionice")
                ):
                    tokens.pop(0)
            if head == "timeout" and tokens and re.fullmatch(r"\d+[smhd]?", tokens[0]):
                tokens.pop(0)
            changed = True
        elif head in RUNNERS:
            tokens.pop(0)
            while tokens and tokens[0].startswith("-"):
                tokens.pop(0)
            changed = True
        elif (
            head in RUNNER_SUBCOMMANDS and len(tokens) > 1 and tokens[1] in RUNNER_SUBCOMMANDS[head]
        ):
            tokens = tokens[2:]
            while tokens and tokens[0].startswith("-"):
                tokens.pop(0)
            changed = True
        elif head in ("python", "python3") and len(tokens) > 2 and tokens[1] == "-m":
            tokens = tokens[2:]
            changed = True
    return tokens


def executable_and_args(tokens: list[str]) -> tuple[str, list[str]]:
    exe = os.path.basename(tokens[0])
    args = tokens[1:]
    if exe in ("python", "python3") and args and os.path.basename(args[0]) == "manage.py":
        return "manage.py", args[1:]
    return exe, args


def _positionals(args: list[str]) -> list[str]:
    return [a for a in args if not a.startswith("-")]


def _has_flag(args: list[str], flag: str) -> bool:
    for arg in args:
        if arg == flag or arg.startswith(flag + "="):
            return True
        # Combined short flags: -fd contains -f
        if (
            len(flag) == 2
            and flag.startswith("-")
            and re.fullmatch(r"-[A-Za-z]+", arg)
            and flag[1] in arg[1:]
        ):
            return True
    return False


# ---------------------------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------------------------


def check_rules(exe: str, args: list[str], config: Config) -> str | None:
    positionals = _positionals(args)
    for rule in DANGEROUS_RULES:
        if rule.name in config.disabled_rules or exe not in rule.executables:
            continue
        if rule.subcommand and tuple(positionals[: len(rule.subcommand)]) != rule.subcommand:
            continue
        if rule.flags_any and not any(_has_flag(args, f) for f in rule.flags_any):
            continue
        if rule.flags_none and any(_has_flag(args, f) for f in rule.flags_none):
            continue
        return f"{rule.name}: {rule.reason}"
    return None


def check_git(exe: str, args: list[str], config: Config) -> str | None:
    if exe != "git":
        return None
    # Skip global options such as -C <dir>, -c key=value
    rest = list(args)
    while rest and rest[0].startswith("-"):
        opt = rest.pop(0)
        if opt in ("-C", "-c") and rest:
            rest.pop(0)
    if not rest:
        return None
    sub, sub_args = rest[0], rest[1:]
    if sub == "push" and "git-push-force" not in config.disabled_rules:
        forced = any(a in ("--force", "-f", "--force-if-includes") for a in sub_args) or any(
            re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", a) for a in sub_args
        )
        plus_refspec = any(a.startswith("+") for a in _positionals(sub_args))
        if (forced or plus_refspec) and not any(
            a.startswith("--force-with-lease") for a in sub_args
        ):
            return "git-push-force: rewrites remote history and can destroy collaborators' work (use --force-with-lease after approval)"
        if any(a in ("--delete", "-d") for a in sub_args) or any(
            a.startswith(":") for a in _positionals(sub_args)[1:]
        ):
            return "git-push-delete: deletes a remote branch or tag"
    if sub == "clean" and "git-clean" not in config.disabled_rules:
        forced = any(a == "--force" or re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", a) for a in sub_args)
        if forced and not any(a in ("-n", "--dry-run") for a in sub_args):
            return "git-clean: permanently deletes untracked files"
    if sub in ("checkout", "restore") and "git-discard-all" not in config.disabled_rules:
        if (
            sub == "restore"
            and "--staged" in sub_args
            and "--worktree" not in sub_args
            and "-W" not in sub_args
        ):
            return None
        paths = [a for a in sub_args if not a.startswith("-")]
        if "--" in sub_args:
            paths = sub_args[sub_args.index("--") + 1 :]
        if any(p in (".", "*", ":/") for p in paths) and (
            sub == "restore" or "--" in sub_args or paths == ["."]
        ):
            return "git-discard-all: discards every uncommitted change in the working tree"
    if (
        sub == "branch"
        and any(a in ("-D",) for a in sub_args)
        and "git-branch-force-delete" not in config.disabled_rules
    ):
        return "git-branch-force-delete: deletes a branch even if it is not merged"
    return None


TEMP_ROOTS = {Path("/tmp"), Path("/private/tmp"), Path("/var/tmp"), Path("/private/var/tmp")}


def _is_temp(path: Path) -> bool:
    roots = set(TEMP_ROOTS)
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        roots.add(Path(os.path.normpath(tmpdir)))
    roots.add(Path("/private/var/folders"))
    roots.add(Path("/var/folders"))
    return any(path == r or r in path.parents for r in roots)


def _dangerous_rm_target(target: str, config: Config, cwd: Path) -> str | None:
    raw = target.rstrip("/") or "/"
    if raw in (
        "/",
        "/*",
        "~",
        "~/*",
        "$HOME",
        "${HOME}",
        "$HOME/*",
        ".",
        "./",
        "./*",
        "..",
        "../*",
        "*",
        ".*",
    ):
        return f"recursive deletion of `{target}`"
    if raw in (".git", "./.git") or raw.endswith("/.git"):
        return f"recursive deletion of the git repository (`{target}`)"
    expanded = os.path.expanduser(os.path.expandvars(raw))
    path = Path(expanded) if os.path.isabs(expanded) else cwd / expanded
    normalized = Path(os.path.normpath(path))
    project = Path(os.path.normpath(config.project_dir))
    if normalized == project:
        return "recursive deletion of the whole project"
    if _is_temp(normalized) and normalized not in TEMP_ROOTS:
        return None
    if project not in normalized.parents:
        return f"recursive deletion outside the project (`{target}`)"
    return None


def check_rm(exe: str, args: list[str], config: Config, cwd: Path) -> str | None:
    if exe != "rm" or "rm-recursive-dangerous" in config.disabled_rules:
        return None
    if "--no-preserve-root" in args:
        return "rm-recursive-dangerous: --no-preserve-root"
    recursive = any(
        a in ("-r", "-R", "--recursive") or re.fullmatch(r"-[A-Za-z]*[rR][A-Za-z]*", a)
        for a in args
        if a != "--"
    )
    targets = (
        args[args.index("--") + 1 :] if "--" in args else [a for a in args if not a.startswith("-")]
    )
    for target in targets:
        reason = protected_reason(target, config, cwd)
        if reason:
            return f"protected-path: deleting {reason}"
    if not recursive:
        return None
    for target in targets:
        why = _dangerous_rm_target(target, config, cwd)
        if why:
            return f"rm-recursive-dangerous: {why}"
    return None


def check_sql(exe: str, args: list[str], config: Config) -> str | None:
    if exe not in SQL_CLIENTS or "destructive-sql" in config.disabled_rules:
        return None
    text = " ".join(args)
    if DESTRUCTIVE_SQL.search(text) or DELETE_WITHOUT_WHERE.search(text):
        return f"destructive-sql: {exe} statement drops, truncates or wipes data"
    if exe == "redis-cli" and any(a.lower() in ("flushall", "flushdb") for a in args):
        return "destructive-sql: wipes Redis data"
    return None


def check_misc(exe: str, args: list[str], config: Config) -> str | None:
    if (
        exe == "dd"
        and any(a.startswith("of=/dev/") for a in args)
        and "dd-device" not in config.disabled_rules
    ):
        return "dd-device: writes directly to a block device"
    if (
        exe in ("chmod", "chown", "chgrp")
        and any(a in ("-R", "--recursive") for a in args)
        and "/" in _positionals(args)
    ):
        return "recursive-permission-root: changes ownership/permissions of the whole filesystem"
    if (
        exe == "find"
        and "-delete" in args
        and any(p in ("/", "~", "$HOME") for p in _positionals(args)[:1])
    ):
        return "find-delete-root: deletes files across the filesystem"
    return None


def check_file_writes(exe: str, args: list[str], config: Config, cwd: Path) -> str | None:
    targets: list[str] = []
    if exe in ("mv", "truncate", "shred"):
        targets = _positionals(args)
    elif exe in ("cp", "install", "ln") and _positionals(args):
        targets = _positionals(args)[-1:]
    elif exe == "tee":
        targets = _positionals(args)
    elif exe == "sed" and any(a == "-i" or a.startswith("-i") or a == "--in-place" for a in args):
        targets = _positionals(args)[1:]
    for target in targets:
        reason = protected_reason(target, config, cwd)
        if reason:
            return f"protected-path: modifying {reason}"
    return None


def check_redirects(tokens: list[str], config: Config, cwd: Path) -> str | None:
    for i, token in enumerate(tokens[:-1]):
        if token in REDIRECTS:
            target = tokens[i + 1]
            if target.isdigit() or target in ("&", "/dev/null"):
                continue
            reason = protected_reason(target, config, cwd)
            if reason:
                return f"protected-path: redirecting output into {reason}"
    return None


def check_segment(segment: list[str], config: Config, cwd: Path, depth: int) -> str | None:
    redirect = check_redirects(segment, config, cwd)
    if redirect:
        return redirect
    # Drop redirections before analysing the command itself.
    cleaned: list[str] = []
    skip = False
    for token in segment:
        if skip:
            skip = False
            continue
        if token in REDIRECTS or token in ("<", "<<", "<<<", ">&", "<&"):
            skip = True
            continue
        cleaned.append(token)
    tokens = strip_prefix(cleaned)
    if not tokens:
        return None
    exe, args = executable_and_args(tokens)
    if exe in SHELLS and "-c" in args:
        index = args.index("-c")
        if index + 1 < len(args):
            return check_command(args[index + 1], config, cwd, depth + 1)
    if exe == "eval" and args:
        return check_command(" ".join(args), config, cwd, depth + 1)
    if exe == "xargs":
        inner = strip_prefix([a for a in args if not a.startswith("-")])
        if inner:
            return check_segment(inner, config, cwd, depth + 1)
    for check in (check_rules, check_git, check_sql, check_misc):
        reason = check(exe, args, config)
        if reason:
            return reason
    return check_rm(exe, args, config, cwd) or check_file_writes(exe, args, config, cwd)


FORK_BOMB = re.compile(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:")
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


def check_command(command: str, config: Config, cwd: Path, depth: int = 0) -> str | None:
    if depth > 4:
        return None
    if FORK_BOMB.search(command):
        return "fork-bomb: exhausts system resources"
    for pattern in config.allow_commands:
        if pattern.search(command):
            return None
    for match in SUBSTITUTION.finditer(command):
        inner = match.group(1) or match.group(2) or ""
        reason = check_command(inner, config, cwd, depth + 1)
        if reason:
            return reason
    try:
        tokens = tokenize(command)
    except ValueError:
        # Unbalanced quotes: fall back to a conservative scan of each line.
        tokens = command.replace("'", " ").replace('"', " ").split()
    for segment in split_segments(tokens):
        reason = check_segment(segment, config, cwd, depth)
        if reason:
            return reason
    return None


def check_tool(payload: dict, config: Config) -> str | None:
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or config.project_dir)
    if tool == "Bash":
        return check_command(str(tool_input.get("command", "")), config, cwd)
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if path:
            reason = protected_reason(str(path), config, cwd)
            if reason:
                return f"protected-path: editing {reason}"
    return None


def block_message(reason: str, tool: str) -> str:
    rule, _, detail = reason.partition(": ")
    return (
        "CWI Safety Guard blocked this " + ("command" if tool == "Bash" else "edit") + ".\n"
        f"Rule: {rule}\nWhy: {detail}\n\n"
        "Do not retry it or work around the guard. Investigate the current state, explain to the user "
        "why this irreversible operation seems necessary, and ask for explicit approval. The user can run it "
        "themselves or allow it in .claude/safety-guard.json."
    )


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        print(f"safety-guard: invalid hook input ({exc}); allowing", file=sys.stderr)
        return 1
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
    config = load_config(project_dir)
    reason = check_tool(payload, config)
    if reason:
        print(block_message(reason, payload.get("tool_name", "")), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - never crash Claude's tool loop
        print(f"safety-guard: internal error ({exc}); allowing", file=sys.stderr)
        sys.exit(1)
