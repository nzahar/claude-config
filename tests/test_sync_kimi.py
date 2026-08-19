from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync-kimi.sh"

requires_npx = pytest.mark.skipif(
    shutil.which("npx") is None or shutil.which("timeout") is None,
    reason="without npx/timeout the script correctly refuses to sync; nothing to assert on",
)


def _frontmatter_body(text: str) -> str:
    if text.startswith("---\n"):
        return text.split("---", 2)[2].strip()
    return text.strip()


@pytest.fixture
def sandbox(tmp_path: Path) -> dict[str, Path]:
    home = tmp_path / "home"
    claude = home / ".claude"
    claude.mkdir(parents=True)
    shutil.copy(ROOT / "CLAUDE.md", claude / "CLAUDE.md")
    for d in ("rules", "agents", "lib"):
        shutil.copytree(ROOT / d, claude / d)
    kimi = tmp_path / "kimi"
    kimi.mkdir()
    return {"home": home, "claude": claude, "kimi": kimi}


def _run(sb: dict[str, Path], *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(sb["home"])
    env["KIMI_CODE_HOME"] = str(sb["kimi"])
    env.pop("CLAUDE_CONFIG_DIR", None)
    real_home = Path(os.path.expanduser("~"))
    env.setdefault("npm_config_cache", str(real_home / ".npm"))
    return subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


@requires_npx
def test_sync_generates_agents_md_rules_agents_and_lib(sandbox):
    result = _run(sandbox, "--quiet")
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr

    agents_md = (sandbox["kimi"] / "AGENTS.md").read_text(encoding="utf-8")
    assert _frontmatter_body((sandbox["claude"] / "CLAUDE.md").read_text(encoding="utf-8")) in agents_md
    for rule in sorted((sandbox["claude"] / "rules").glob("*.md")):
        assert _frontmatter_body(rule.read_text(encoding="utf-8")) in agents_md, rule.name

    src_agents = sorted(p.name for p in (sandbox["claude"] / "agents").glob("*.md"))
    out_agents = sorted(p.name for p in (sandbox["kimi"] / "agents").glob("*.md"))
    assert out_agents == src_agents
    for name in src_agents:
        src_body = _frontmatter_body((sandbox["claude"] / "agents" / name).read_text(encoding="utf-8"))
        out_body = _frontmatter_body((sandbox["kimi"] / "agents" / name).read_text(encoding="utf-8"))
        assert out_body == src_body, name

    lib = sandbox["kimi"] / "lib"
    assert lib.is_symlink()
    assert (lib / "state-contract.md").read_text(encoding="utf-8") == (
        sandbox["claude"] / "lib" / "state-contract.md"
    ).read_text(encoding="utf-8")


@requires_npx
def test_second_run_is_idempotent_and_check_reports_drift(sandbox):
    assert _run(sandbox, "--quiet").returncode == 0
    check = _run(sandbox, "--check")
    assert check.returncode == 0, check.stdout + check.stderr
    assert check.stdout == ""
    assert check.stderr == ""

    with (sandbox["claude"] / "rules" / "security.md").open("a", encoding="utf-8") as fh:
        fh.write("\n- Sync-kimi drift marker\n")
    drift = _run(sandbox, "--check")
    assert drift.returncode == 1
    assert "Sync-kimi drift marker" in drift.stdout
    assert "Sync-kimi drift marker" not in (sandbox["kimi"] / "AGENTS.md").read_text(encoding="utf-8")


@requires_npx
def test_stale_agent_is_removed(sandbox):
    assert _run(sandbox, "--quiet").returncode == 0
    (sandbox["claude"] / "agents" / "debugger.md").unlink()
    assert _run(sandbox, "--quiet").returncode == 0
    assert not (sandbox["kimi"] / "agents" / "debugger.md").exists()


def test_refuses_foreign_claude_config_dir(sandbox, tmp_path):
    env = os.environ.copy()
    env["HOME"] = str(sandbox["home"])
    env["KIMI_CODE_HOME"] = str(sandbox["kimi"])
    other = tmp_path / "other-claude"
    other.mkdir()
    env["CLAUDE_CONFIG_DIR"] = str(other)
    result = subprocess.run([str(SCRIPT), "--quiet"], capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 0
    assert "CLAUDE_CONFIG_DIR" in result.stderr
    assert not (sandbox["kimi"] / "AGENTS.md").exists()


def test_same_claude_config_dir_is_accepted_as_default(sandbox):
    env = os.environ.copy()
    env["HOME"] = str(sandbox["home"])
    env["KIMI_CODE_HOME"] = str(sandbox["kimi"])
    env["CLAUDE_CONFIG_DIR"] = str(sandbox["claude"])
    env["PATH"] = "/nonexistent"
    result = subprocess.run(["/bin/bash", str(SCRIPT), "--quiet"], capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 0
    assert "CLAUDE_CONFIG_DIR" not in result.stderr
    assert "not syncing" in result.stderr


def test_unknown_argument_is_rejected(sandbox):
    result = _run(sandbox, "--bogus")
    assert result.returncode == 2


@requires_npx
def test_only_declared_targets_are_touched(sandbox):
    kimi = sandbox["kimi"]
    (kimi / "config.toml").write_text("default_model = \"kimi-code/k3\"\n", encoding="utf-8")
    (kimi / "sessions").mkdir()
    (kimi / "sessions" / "x.jsonl").write_text("{}\n", encoding="utf-8")
    (kimi / "notes.md").write_text("mine\n", encoding="utf-8")
    (kimi / "agents").mkdir()
    (kimi / "agents" / "hand-written.md").write_text("---\nname: hand-written\ndescription: x\n---\n", encoding="utf-8")

    assert _run(sandbox, "--quiet").returncode == 0

    assert (kimi / "config.toml").read_text(encoding="utf-8") == "default_model = \"kimi-code/k3\"\n"
    assert (kimi / "sessions" / "x.jsonl").read_text(encoding="utf-8") == "{}\n"
    assert (kimi / "notes.md").read_text(encoding="utf-8") == "mine\n"
    assert not (kimi / "agents" / "hand-written.md").exists()


@requires_npx
def test_broken_agent_bails_without_touching_live_profile(sandbox):
    assert _run(sandbox, "--quiet").returncode == 0
    before = sorted(p.name for p in (sandbox["kimi"] / "agents").glob("*.md"))
    (sandbox["claude"] / "agents" / "debugger.md").write_text(
        "---\nname: debugger\ndescription: broken: colon\n---\nbody\n", encoding="utf-8"
    )
    result = _run(sandbox, "--quiet")
    assert result.returncode == 0
    assert "not syncing" in result.stderr
    after = sorted(p.name for p in (sandbox["kimi"] / "agents").glob("*.md"))
    assert after == before
    check = _run(sandbox, "--check")
    assert check.returncode == 3


def test_check_exits_3_when_tooling_is_missing(sandbox):
    env = os.environ.copy()
    env["HOME"] = str(sandbox["home"])
    env["KIMI_CODE_HOME"] = str(sandbox["kimi"])
    env.pop("CLAUDE_CONFIG_DIR", None)
    env["PATH"] = "/nonexistent"
    result = subprocess.run(["/bin/bash", str(SCRIPT), "--check"], capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 3
    assert "not syncing" in result.stderr
