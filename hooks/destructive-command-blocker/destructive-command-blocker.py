#!/usr/bin/env python3
"""Claude Code PreToolUse hook that blocks destructive Bash commands."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOOK_EVENT_NAME = "PreToolUse"

BLOCKERS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "rm -rf",
        re.compile(r"(?i)(?:^|[\s;&|()])rm\s+-(?=[A-Za-z-]*r)(?=[A-Za-z-]*f)[A-Za-z-]*\b"),
        "Recursive forced deletion can remove large parts of the project or home directory.",
    ),
    (
        "DROP TABLE",
        re.compile(r"(?is)\bdrop\s+table\b"),
        "DROP TABLE deletes an entire database table.",
    ),
    (
        "TRUNCATE",
        re.compile(r"(?is)\btruncate(?:\s+table)?\b"),
        "TRUNCATE removes all rows from a table.",
    ),
    (
        "git push --force",
        re.compile(r"(?is)\bgit\s+push\b[^;&|\n]*?(?:--force\b|\s-f(?:\s|$))"),
        "Force pushing can overwrite remote history.",
    ),
]

DELETE_FROM_RE = re.compile(r"(?is)\bdelete\s+from\b")
WHERE_RE = re.compile(r"(?is)\bwhere\b")


def main() -> int:
    payload = read_json(sys.stdin.read())
    if payload is None:
        return 0

    tool_name = str(payload.get("tool_name", ""))
    if tool_name.lower() != "bash":
        return 0

    command = extract_command(payload)
    if not command:
        return 0

    match = first_blocking_match(command)
    if match is None:
        return 0

    pattern_name, reason = match
    project_path = extract_project_path(payload)
    log_blocked_attempt(command, project_path, pattern_name)
    print(deny_response(pattern_name, reason))
    return 0


def read_json(raw: str) -> dict[str, Any] | None:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def extract_command(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""

    command = tool_input.get("command")
    return command if isinstance(command, str) else ""


def first_blocking_match(command: str) -> tuple[str, str] | None:
    for pattern_name, pattern, reason in BLOCKERS:
        if pattern.search(command):
            return pattern_name, reason

    if delete_from_without_where(command):
        return (
            "DELETE FROM without WHERE",
            "DELETE FROM without a WHERE clause can delete every row in the table.",
        )

    return None


def delete_from_without_where(command: str) -> bool:
    for statement in command.split(";"):
        match = DELETE_FROM_RE.search(statement)
        if not match:
            continue

        after_delete = statement[match.end() :]
        if not WHERE_RE.search(after_delete):
            return True

    return False


def extract_project_path(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("cwd", "project_path"):
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                return value

    for key in ("cwd", "project_path"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def hook_dir() -> Path:
    override = os.environ.get("CLAUDE_HOOKS_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude" / "hooks"


def log_blocked_attempt(command: str, project_path: str, pattern_name: str) -> None:
    log_path = hook_dir() / "blocked.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pattern": pattern_name,
            "command": command,
            "project_path": project_path,
        }
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        # Blocking should not depend on logging success.
        pass


def deny_response(pattern_name: str, reason: str) -> str:
    message = (
        f"Blocked potentially destructive Bash command ({pattern_name}). "
        f"{reason} Use a narrower, reversible, or explicitly reviewed command instead."
    )
    response = {
        "hookSpecificOutput": {
            "hookEventName": HOOK_EVENT_NAME,
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }
    }
    return json.dumps(response)


if __name__ == "__main__":
    raise SystemExit(main())
