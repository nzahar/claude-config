from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills" / "learned" / "_gen-index.sh"
BASH = "/bin/bash"


def _make_learned_dir(tmp_path: Path) -> Path:
    d = tmp_path / "learned"
    d.mkdir()
    dest = d / "_gen-index.sh"
    shutil.copy(SCRIPT_PATH, dest)
    dest.chmod(0o755)
    return d


def _write_note(d: Path, filename: str, content: str) -> Path:
    path = d / filename
    path.write_text(content, encoding="utf-8")
    return path


def _run(d: Path, path: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        [BASH, str(d / "_gen-index.sh")],
        capture_output=True,
        text=True,
        env=env,
    )


def _minimal_path(tmp_path: Path, tools: list[str]) -> str:
    bin_dir = tmp_path / "minbin"
    bin_dir.mkdir(exist_ok=True)
    for name in tools:
        src = shutil.which(name, path="/usr/bin:/bin")
        assert src is not None, f"required tool {name} not found on this system"
        link = bin_dir / name
        if not link.exists():
            link.symlink_to(src)
    return str(bin_dir)


NOTE_WITH_FRONTMATTER = """---
name: My Great Note
description: A note about something useful
---

# Body
"""

NOTE_WITHOUT_DESCRIPTION = """---
name: No Description Note
---

# Body
"""

NOTE_WITHOUT_FRONTMATTER = """# Just A Heading

No frontmatter here at all.
"""

SKILL_MD = """---
name: learned-skill-entry
description: Native skill entry point, not a note
---

# SKILL
"""


class TestGenIndex:
    def test_generates_index_json_for_note_with_frontmatter(self, tmp_path):
        d = _make_learned_dir(tmp_path)
        _write_note(d, "my-note.md", NOTE_WITH_FRONTMATTER)

        result = _run(d)

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "My Great Note" in ctx
        assert "A note about something useful" in ctx
        assert "learned/my-note.md" in ctx

    def test_excludes_skill_md_from_index(self, tmp_path):
        d = _make_learned_dir(tmp_path)
        _write_note(d, "SKILL.md", SKILL_MD)
        _write_note(d, "real-note.md", NOTE_WITH_FRONTMATTER)

        result = _run(d)

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        assert "learned/real-note.md" in ctx
        assert "learned/SKILL.md" not in ctx
        assert "learned-skill-entry" not in ctx

    def test_only_skill_md_present_prints_nothing_and_exits_zero(self, tmp_path):
        d = _make_learned_dir(tmp_path)
        _write_note(d, "SKILL.md", SKILL_MD)

        result = _run(d)

        assert result.returncode == 0
        assert result.stdout == ""

    def test_empty_directory_prints_nothing_and_exits_zero(self, tmp_path):
        d = _make_learned_dir(tmp_path)

        result = _run(d)

        assert result.returncode == 0
        assert result.stdout == ""

    def test_missing_jq_degrades_silently(self, tmp_path):
        d = _make_learned_dir(tmp_path)
        _write_note(d, "my-note.md", NOTE_WITH_FRONTMATTER)
        path = _minimal_path(tmp_path, ["awk", "dirname", "basename"])

        result = _run(d, path=path)

        assert result.returncode == 0
        assert result.stdout == ""

    def test_missing_awk_degrades_silently(self, tmp_path):
        d = _make_learned_dir(tmp_path)
        _write_note(d, "my-note.md", NOTE_WITH_FRONTMATTER)
        path = _minimal_path(tmp_path, ["jq", "dirname", "basename"])

        result = _run(d, path=path)

        assert result.returncode == 0
        assert result.stdout == ""

    def test_note_without_frontmatter_falls_back_to_filename(self, tmp_path):
        d = _make_learned_dir(tmp_path)
        _write_note(d, "unnamed-note.md", NOTE_WITHOUT_FRONTMATTER)

        result = _run(d)

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        assert "unnamed-note.md" in ctx
        assert "(no description)" in ctx

    def test_note_missing_description_uses_placeholder(self, tmp_path):
        d = _make_learned_dir(tmp_path)
        _write_note(d, "no-desc.md", NOTE_WITHOUT_DESCRIPTION)

        result = _run(d)

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        assert "No Description Note" in ctx
        assert "(no description)" in ctx

    def test_output_is_valid_json_regardless_of_note_content(self, tmp_path):
        d = _make_learned_dir(tmp_path)
        _write_note(d, "tricky.md", '---\nname: "Quotes & \\"stuff\\""\ndescription: has, commas; and | pipes\n---\n')

        result = _run(d)

        assert result.returncode == 0
        json.loads(result.stdout)
