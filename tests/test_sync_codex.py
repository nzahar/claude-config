from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync-codex.py"


def load_sync_codex():
    spec = importlib.util.spec_from_file_location("sync_codex", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SyncCodexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sync_codex = load_sync_codex()
        self.root = Path(self.tmp.name) / "framework"
        self.codex_home = Path(self.tmp.name) / "codex-home"
        (self.root / "agents").mkdir(parents=True)
        (self.root / "commands").mkdir(parents=True)
        (self.root / "skills" / "framework-skill").mkdir(parents=True)
        (self.root / "skills" / "framework-skill" / "SKILL.md").write_text("# Framework skill\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")

        patches = [
            mock.patch.object(self.sync_codex, "ROOT", self.root),
            mock.patch.object(self.sync_codex, "CODEX_HOME", self.codex_home),
            mock.patch.object(self.sync_codex, "LOCAL_CODEX_DIR", self.root / ".codex"),
            mock.patch.object(self.sync_codex, "LOCAL_AGENT_DIR", self.root / ".codex" / "agents"),
            mock.patch.object(
                self.sync_codex,
                "LOCAL_COMMAND_SKILL_DIR",
                self.root / ".codex" / "skills" / "commands",
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_command_description_prefers_frontmatter_over_alias(self):
        source = self.root / "commands" / "ship.md"
        text = "---\ndescription: Custom command trigger\n---\n\nCommit and merge.\n"

        self.assertEqual(self.sync_codex.command_description(source, text), "Custom command trigger")

    def test_command_description_uses_known_alias_for_command_without_frontmatter(self):
        source = self.root / "commands" / "ship.md"

        description = self.sync_codex.command_description(
            source,
            "Commit changes, open a PR, and merge it immediately.\n",
        )

        self.assertEqual(
            description,
            "Use when the user invokes /ship, says ship, шипай, зашипай, or asks to commit, open a PR, "
            "and merge immediately.",
        )

    def test_generate_command_skill_wrappers_writes_skill_adapters_idempotently(self):
        (self.root / "commands" / "ship.md").write_text(
            "Commit changes, open a PR, and merge it immediately.\n",
            encoding="utf-8",
        )
        (self.root / "commands" / "statusbar.md").write_text(
            "---\ndescription: Show status details\n---\n\n# Status\n",
            encoding="utf-8",
        )

        first_result = self.sync_codex.generate_command_skill_wrappers(dry_run=False)

        self.assertEqual(
            [(name, changed) for name, _, _, changed in first_result],
            [("ship", True), ("statusbar", True)],
        )
        ship_skill = self.root / ".codex" / "skills" / "commands" / "ship" / "SKILL.md"
        status_skill = self.root / ".codex" / "skills" / "commands" / "statusbar" / "SKILL.md"
        ship_text = ship_skill.read_text(encoding="utf-8")
        status_text = status_skill.read_text(encoding="utf-8")
        self.assertIn("name: ship", ship_text)
        self.assertIn("description: Use when the user invokes /ship, says ship, шипай, зашипай", ship_text)
        self.assertIn("Read `~/.claude/commands/ship.md` completely", ship_text)
        self.assertNotIn(str(self.root), ship_text)
        self.assertIn("description: Show status details", status_text)
        self.assertEqual(
            self.sync_codex.generate_command_skill_wrappers(dry_run=False),
            [
                ("ship", first_result[0][1], first_result[0][2], False),
                ("statusbar", first_result[1][1], first_result[1][2], False),
            ],
        )

    def test_main_check_reports_stale_command_skills_without_writing(self):
        command = self.root / "commands" / "learn.md"
        command.write_text("# /learn - Extract Reusable Patterns\n", encoding="utf-8")
        expected_skill = self.root / ".codex" / "skills" / "commands" / "learn" / "SKILL.md"

        with mock.patch.object(sys, "argv", ["sync-codex.py", "--check"]):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = self.sync_codex.main()

        self.assertEqual(result, 1)
        self.assertIn(f"stale: {expected_skill}", output.getvalue())
        self.assertFalse(expected_skill.exists())

    def test_generate_agent_wrappers_uses_portable_framework_reference(self):
        (self.root / "agents" / "reviewer.md").write_text(
            "---\nname: reviewer\ndescription: Review changes\n---\n",
            encoding="utf-8",
        )

        self.sync_codex.generate_agent_wrappers(dry_run=False)

        wrapper = self.root / ".codex" / "agents" / "reviewer.toml"
        text = wrapper.read_text(encoding="utf-8")
        self.assertIn("read `~/.claude/agents/reviewer.md` completely", text)
        self.assertNotIn(str(self.root), text)

    def test_managed_config_block_includes_generated_command_skill_dirs(self):
        (self.root / "commands" / "ship.md").write_text("Ship it.\n", encoding="utf-8")
        self.sync_codex.generate_command_skill_wrappers(dry_run=False)

        block = self.sync_codex.managed_config_block([])

        self.assertIn(f'path = "{self.root / "skills" / "framework-skill"}"', block)
        self.assertIn(f'path = "{self.root / ".codex" / "skills" / "commands" / "ship"}"', block)


if __name__ == "__main__":
    unittest.main()
