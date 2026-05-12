# Destructive Command Blocker

Claude Code `PreToolUse` hook that blocks destructive Bash commands before they run.

## What It Blocks

- Recursive forced deletion through `rm -rf`, `rm -fr`, `rm --recursive --force`, and wrapper commands such as `sudo rm -rf`, `bash -lc "rm -rf ..."`, or `find ... -exec rm -rf`.
- Forced Git pushes through `git push --force`, `git push -f`, `git push --force-with-lease`, and forced refspecs such as `git push origin +main`.
- Destructive SQL sent to common database clients such as `psql`, `mysql`, `mariadb`, `sqlite3`, `duckdb`, and `sqlcmd`:
  - `DROP TABLE`, `DROP DATABASE`, and `DROP SCHEMA`
  - `TRUNCATE`
  - `DELETE FROM` statements without a `WHERE` clause

The detector tokenizes the shell command before matching, so documentation/search commands such as `echo "rm -rf build"` and `grep -R "DROP TABLE" docs` are not blocked.

Blocked attempts are appended as JSON lines to `~/.claude/hooks/blocked.log` with the UTC timestamp, severity, rule, reason, evidence, attempted command, and project path.

## Install

```bash
python hooks/destructive-command-blocker/install.py
python hooks/destructive-command-blocker/test_destructive_command_blocker.py
```

The installer copies `destructive-command-blocker.py` into `~/.claude/hooks/` and adds an equivalent Claude Code hook configuration to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/destructive-command-blocker.py"
          }
        ]
      }
    ]
  }
}
```

On Windows, the installer writes a command that invokes the current Python executable explicitly. On macOS/Linux, it writes the copied hook path and marks it executable. Re-running the installer updates the existing hook entry instead of duplicating it.

## Manual Check

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf node_modules","cwd":"/tmp/project"}}' | ~/.claude/hooks/destructive-command-blocker.py
```

Expected output contains `permissionDecision: "deny"` and a clear reason for Claude. Safe Bash commands exit without output so they do not interfere with normal work.

The included tests cover the required acceptance criteria plus wrapper commands, nested shell commands, Git forced refspecs, SQL clients, piped SQL input, false-positive strings, non-Bash tool payloads, invalid input, logging, and installer idempotency.
