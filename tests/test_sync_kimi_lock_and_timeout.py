from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync-kimi.sh"

requires_npx = pytest.mark.skipif(
    shutil.which("npx") is None
    or not any(shutil.which(t) for t in ("timeout", "gtimeout", "perl")),
    reason="without npx or any timeout primitive the script correctly refuses to sync; nothing to assert on",
)

# Tools sync-kimi.sh shells out to for a full import+generate pass (everything
# except the timeout primitive itself, which each test controls deliberately).
_SYNC_TOOLS = (
    "mkdir", "rm", "cp", "ln", "diff", "find", "wc", "mktemp",
    "kill", "sleep", "cat", "readlink", "npx", "node", "sh",
)


@pytest.fixture
def sandbox(tmp_path: Path) -> dict[str, Path]:
    home = tmp_path / "home"
    claude = home / ".claude"
    claude.mkdir(parents=True)
    shutil.copy(ROOT / "CLAUDE.md", claude / "CLAUDE.md")
    for d in ("rules", "agents", "skills"):
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


def _path_minus(names: set[str]) -> str:
    """Real PATH with any directory that would resolve one of `names` dropped.

    Unlike shadowing with an earlier executable, this is the only way to make
    `command -v <name>` genuinely fail for a tool that exists deeper in PATH —
    bash skips non-executable stubs and keeps searching past them.
    """
    kept = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        p = Path(d)
        if any((p / n).is_file() and os.access(p / n, os.X_OK) for n in names):
            continue
        kept.append(d)
    return os.pathsep.join(kept)


def _scoped_bindir(tmp_path: Path, name: str, tools: tuple[str, ...]) -> Path:
    """A single directory symlinking exactly `tools`, resolved from the real PATH.

    Using it as the entire PATH (not prepending it) gives full control over
    which primitives are resolvable, with no risk of a real binary hiding
    further down some inherited directory.
    """
    bindir = tmp_path / name
    bindir.mkdir()
    for tool in tools:
        real = shutil.which(tool)
        if real:
            (bindir / tool).symlink_to(real)
    return bindir


def _env_for(sb: dict[str, Path], path: str) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(sb["home"])
    env["KIMI_CODE_HOME"] = str(sb["kimi"])
    env.pop("CLAUDE_CONFIG_DIR", None)
    env["PATH"] = path
    real_home = Path(os.path.expanduser("~"))
    env.setdefault("npm_config_cache", str(real_home / ".npm"))
    return env


# ── timeout primitive fallback ──────────────────────────────────────────


def test_bails_when_no_timeout_primitive_is_available(sandbox, tmp_path):
    stub_dir = tmp_path / "npx-only"
    stub_dir.mkdir()
    npx_stub = stub_dir / "npx"
    npx_stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    npx_stub.chmod(0o755)

    path = os.pathsep.join([str(stub_dir), _path_minus({"timeout", "gtimeout", "perl"})])
    env = _env_for(sandbox, path)

    result = subprocess.run(["/bin/bash", str(SCRIPT), "--quiet"], capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 0
    assert "none of timeout, gtimeout or perl found" in result.stderr
    assert not (sandbox["kimi"] / "AGENTS.md").exists()

    check = subprocess.run(["/bin/bash", str(SCRIPT), "--check"], capture_output=True, text=True, env=env, timeout=30)
    assert check.returncode == 3


@requires_npx
def test_falls_back_to_perl_when_timeout_and_gtimeout_are_absent(sandbox, tmp_path):
    if shutil.which("perl") is None:
        pytest.skip("perl not available on this host")
    bindir = _scoped_bindir(tmp_path, "perl-only-bin", (*_SYNC_TOOLS, "perl"))
    env = _env_for(sandbox, str(bindir))

    result = subprocess.run(["/bin/bash", str(SCRIPT), "--quiet"], capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    assert (sandbox["kimi"] / "AGENTS.md").exists()


@requires_npx
def test_uses_gtimeout_when_present_and_timeout_is_absent(sandbox, tmp_path):
    bindir = _scoped_bindir(tmp_path, "gtimeout-bin", _SYNC_TOOLS)
    marker = tmp_path / "gtimeout.used"
    shim = bindir / "gtimeout"
    shim.write_text(
        "#!/bin/sh\n"
        f'echo used >> "{marker}"\n'
        "shift\n"
        'exec "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    env = _env_for(sandbox, str(bindir))

    result = subprocess.run(["/bin/bash", str(SCRIPT), "--quiet"], capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, result.stderr
    assert (sandbox["kimi"] / "AGENTS.md").exists()
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() != ""


# ── mkdir-based lock ─────────────────────────────────────────────────────


# NOTE: reclaim-on-stale-pid was deliberately removed from the script (TOCTOU:
# two waiters could both delete the lock and both enter the critical section).
# A held lock, live or stale, now blocks for the full 30s budget and bails
# naming the path and pid — the user removes the directory by hand. Both tests
# below therefore take ~30s of real wall clock; that budget is hardcoded in the
# script and out of scope for this test file to shorten.


@requires_npx
def test_concurrent_run_is_refused_while_lock_is_held(sandbox):
    lock_dir = sandbox["home"] / ".rulesync" / ".sync-kimi.lock.d"
    lock_dir.mkdir(parents=True)
    pid = os.getpid()
    (lock_dir / "pid").write_text(f"{pid}\n", encoding="utf-8")

    start = time.monotonic()
    result = _run(sandbox, "--quiet")
    elapsed = time.monotonic() - start

    assert result.returncode == 0
    assert f"another sync-kimi run holds {lock_dir} (pid {pid})" in result.stderr
    assert "remove that directory and re-run" in result.stderr
    assert elapsed >= 25, f"lock wait returned too quickly ({elapsed:.1f}s) to have exhausted its retries"
    assert not (sandbox["kimi"] / "AGENTS.md").exists()
    assert lock_dir.exists(), "a lock this run does not own must be left alone, not cleaned up"


@requires_npx
def test_stale_lock_blocks_rather_than_being_reclaimed(sandbox):
    lock_dir = sandbox["home"] / ".rulesync" / ".sync-kimi.lock.d"
    lock_dir.mkdir(parents=True)
    dead = subprocess.run(["/bin/sh", "-c", "echo $$"], capture_output=True, text=True, timeout=10)
    dead_pid = dead.stdout.strip()
    (lock_dir / "pid").write_text(dead_pid + "\n", encoding="utf-8")

    start = time.monotonic()
    result = _run(sandbox, "--quiet")
    elapsed = time.monotonic() - start

    assert result.returncode == 0
    assert f"another sync-kimi run holds {lock_dir} (pid {dead_pid})" in result.stderr
    assert elapsed >= 25, f"a stale lock must still consume the full retry budget, not be reclaimed early ({elapsed:.1f}s)"
    assert not (sandbox["kimi"] / "AGENTS.md").exists()
    assert lock_dir.exists(), "a stale lock is left for the user to remove by hand, not auto-reclaimed"


@requires_npx
def test_lock_directory_is_removed_after_successful_sync(sandbox):
    result = _run(sandbox, "--quiet")
    assert result.returncode == 0, result.stderr
    assert not (sandbox["home"] / ".rulesync" / ".sync-kimi.lock.d").exists()


@requires_npx
def test_lock_directory_is_removed_after_bail(sandbox):
    assert _run(sandbox, "--quiet").returncode == 0
    (sandbox["claude"] / "agents" / "debugger.md").write_text(
        "---\nname: debugger\ndescription: broken: colon\n---\nbody\n", encoding="utf-8"
    )
    result = _run(sandbox, "--quiet")
    assert result.returncode == 0
    assert "not syncing" in result.stderr
    assert not (sandbox["home"] / ".rulesync" / ".sync-kimi.lock.d").exists()
