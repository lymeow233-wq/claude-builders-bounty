#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("destructive-command-blocker.py")


class DestructiveCommandBlockerTests(unittest.TestCase):
    def run_hook(self, command: str, hooks_dir: Path) -> subprocess.CompletedProcess[str]:
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": command, "cwd": "/tmp/example-project"},
        }
        env = os.environ.copy()
        env["CLAUDE_HOOKS_DIR"] = str(hooks_dir)
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def assert_blocked(self, command: str, expected_pattern: str) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir)
            result = self.run_hook(command, hooks_dir)

            self.assertEqual(result.returncode, 0)
            response = json.loads(result.stdout)
            hook_output = response["hookSpecificOutput"]
            self.assertEqual(hook_output["hookEventName"], "PreToolUse")
            self.assertEqual(hook_output["permissionDecision"], "deny")
            self.assertIn(expected_pattern, hook_output["permissionDecisionReason"])

            log_path = hooks_dir / "blocked.log"
            self.assertTrue(log_path.exists())
            log_event = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(log_event["command"], command)
            self.assertEqual(log_event["project_path"], "/tmp/example-project")
            self.assertEqual(log_event["pattern"], expected_pattern)

    def test_blocks_rm_rf(self) -> None:
        self.assert_blocked("rm -rf build", "rm -rf")

    def test_blocks_drop_table(self) -> None:
        self.assert_blocked('psql -c "DROP TABLE users"', "DROP TABLE")

    def test_blocks_force_push(self) -> None:
        self.assert_blocked("git push origin main --force", "git push --force")

    def test_blocks_truncate(self) -> None:
        self.assert_blocked('mysql -e "TRUNCATE TABLE sessions"', "TRUNCATE")

    def test_blocks_delete_without_where(self) -> None:
        self.assert_blocked('psql -c "DELETE FROM users"', "DELETE FROM without WHERE")

    def test_allows_normal_bash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir)
            result = self.run_hook("git status --short", hooks_dir)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertFalse((hooks_dir / "blocked.log").exists())

    def test_allows_delete_with_where(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir)
            result = self.run_hook('psql -c "DELETE FROM users WHERE id = 1"', hooks_dir)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertFalse((hooks_dir / "blocked.log").exists())


if __name__ == "__main__":
    unittest.main()
