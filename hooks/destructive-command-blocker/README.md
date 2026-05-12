# Destructive Command Blocker

Claude Code `PreToolUse` hook that blocks destructive Bash commands before they run.

## What It Blocks

- `rm -rf`
- `DROP TABLE`
- `git push --force` and `git push -f`
- `TRUNCATE`
- `DELETE FROM` statements without a `WHERE` clause

Blocked attempts are appended as JSON lines to `~/.claude/hooks/blocked.log` with the UTC timestamp, matched pattern, attempted command, and project path.

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

## Manual Check

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf node_modules","cwd":"/tmp/project"}}' | ~/.claude/hooks/destructive-command-blocker.py
```

Expected output contains `permissionDecision: "deny"` and a clear reason for Claude. Safe Bash commands exit without output so they do not interfere with normal work.
