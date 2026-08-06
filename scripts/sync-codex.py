#!/usr/bin/env python3
"""Sync this Claude framework into Codex-facing configuration files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"
LOCAL_CODEX_DIR = ROOT / ".codex"
LOCAL_AGENT_DIR = LOCAL_CODEX_DIR / "agents"
LOCAL_COMMAND_SKILL_DIR = LOCAL_CODEX_DIR / "skills" / "commands"

MANAGED_BEGIN = "# BEGIN managed by ~/.claude/scripts/sync-codex.py"
MANAGED_END = "# END managed by ~/.claude/scripts/sync-codex.py"
FRAMEWORK_REFERENCE_ROOT = Path("~/.claude")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_if_changed(path: Path, content: str, dry_run: bool) -> bool:
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == content:
        return False
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return True


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    frontmatter = text[4:end]
    result: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        result[key.strip()] = value
    return result


def toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def framework_reference(path: Path) -> str:
    return str(FRAMEWORK_REFERENCE_ROOT / path.relative_to(ROOT))


def generate_agent_wrappers(dry_run: bool) -> list[tuple[str, str, Path, bool]]:
    generated: list[tuple[str, str, Path, bool]] = []
    for source in sorted((ROOT / "agents").glob("*.md")):
        text = read_text(source)
        meta = parse_frontmatter(text)
        name = meta.get("name", source.stem)
        description = meta.get("description", f"Codex wrapper for {source.name}")
        target = LOCAL_AGENT_DIR / f"{name}.toml"
        source_reference = framework_reference(source)
        content = "\n".join(
            [
                f"name = {toml_string(name)}",
                f"description = {toml_string(description)}",
                'developer_instructions = """',
                f"Before acting, read `{source_reference}` completely and follow it as this agent's role contract.",
                "Treat Claude-specific tool names as intent: use the closest available Codex tools.",
                "If the source contract conflicts with higher-priority Codex runtime instructions, follow the higher-priority instruction and report the conflict.",
                '"""',
                "",
            ]
        )
        changed = write_if_changed(target, content, dry_run)
        generated.append((name, description, target, changed))
    return generated


def command_description(source: Path, text: str) -> str:
    meta = parse_frontmatter(text)
    if "description" in meta:
        return meta["description"]
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    fallback = first_line.rstrip(".") if first_line else f"Run the {source.stem} workflow"
    aliases = {
        "commit-push": "Use when the user asks to commit and push, invokes /commit-push, or says commit-push.",
        "learn": "Use when the user invokes /learn or asks to save a reusable learned pattern from the session.",
        "merge-pr": "Use when the user invokes /merge-pr, asks to merge a PR, or gives a PR number to merge.",
        "ship": "Use when the user invokes /ship, says ship, шипай, зашипай, or asks to commit, open a PR, and merge immediately.",
    }
    return aliases.get(source.stem, fallback)


def generate_command_skill_wrappers(dry_run: bool) -> list[tuple[str, str, Path, bool]]:
    generated: list[tuple[str, str, Path, bool]] = []
    for source in sorted((ROOT / "commands").glob("*.md")):
        text = read_text(source)
        name = source.stem
        description = command_description(source, text)
        target = LOCAL_COMMAND_SKILL_DIR / name / "SKILL.md"
        source_reference = framework_reference(source)
        content = "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "---",
                "",
                f"# {name}",
                "",
                f"This is the Codex adapter for `{source_reference}`.",
                "",
                "When this skill is selected:",
                "",
                f"1. Read `{source_reference}` completely before taking action.",
                "2. Treat the user's text after the command name as `$ARGUMENTS`.",
                "3. Follow the command contract as the source of truth.",
                "4. Treat Claude-specific tool names as intent and use the closest available Codex tools.",
                "5. If the command asks for a capability that is unavailable in Codex, stop and report the missing capability instead of reconstructing a weaker workflow silently.",
                "",
            ]
        )
        changed = write_if_changed(target, content, dry_run)
        generated.append((name, description, target.parent, changed))
    return generated


def skill_dirs() -> list[Path]:
    framework_skills = [path.parent for path in (ROOT / "skills").glob("*/SKILL.md")]
    command_skills = [path.parent for path in LOCAL_COMMAND_SKILL_DIR.glob("*/SKILL.md")]
    return sorted(framework_skills + command_skills)


def managed_config_block(agents: list[tuple[str, str, Path, bool]]) -> str:
    lines = [MANAGED_BEGIN, ""]
    for name, description, path, _ in agents:
        lines.extend(
            [
                f"[agents.{name}]",
                f"description = {toml_string(description)}",
                f"config_file = {toml_string(str(path))}",
                "",
            ]
        )
    for path in skill_dirs():
        lines.extend(
            [
                "[[skills.config]]",
                f"path = {toml_string(str(path))}",
                "enabled = true",
                "",
            ]
        )
    lines.append(MANAGED_END)
    lines.append("")
    return "\n".join(lines)


def replace_managed_block(existing: str, block: str) -> str:
    pattern = re.compile(
        re.escape(MANAGED_BEGIN) + r".*?" + re.escape(MANAGED_END) + r"\n?",
        re.DOTALL,
    )
    if pattern.search(existing):
        return pattern.sub(block, existing).rstrip() + "\n"
    return existing.rstrip() + "\n\n" + block


def install_global_agents(dry_run: bool) -> bool:
    source = ROOT / "AGENTS.md"
    target = CODEX_HOME / "AGENTS.md"
    header = "<!-- Generated from ~/.claude/AGENTS.md by scripts/sync-codex.py. Do not edit directly. -->\n\n"
    return write_if_changed(target, header + read_text(source), dry_run)


def install_global_config(agents: list[tuple[str, str, Path, bool]], dry_run: bool) -> bool:
    target = CODEX_HOME / "config.toml"
    existing = read_text(target) if target.exists() else ""
    updated = replace_managed_block(existing, managed_config_block(agents))
    return write_if_changed(target, updated, dry_run)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="also update ~/.codex/AGENTS.md and ~/.codex/config.toml")
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()

    dry_run = args.check
    agents = generate_agent_wrappers(dry_run=dry_run)
    command_skills = generate_command_skill_wrappers(dry_run=dry_run)
    changed: list[str] = []

    for _, _, path, did_change in agents:
        if did_change:
            changed.append(str(path))
    for _, _, path, did_change in command_skills:
        if did_change:
            changed.append(str(path / "SKILL.md"))

    if args.install:
        if install_global_agents(dry_run=dry_run):
            changed.append(str(CODEX_HOME / "AGENTS.md"))
        if install_global_config(agents, dry_run=dry_run):
            changed.append(str(CODEX_HOME / "config.toml"))

    if args.check and changed:
        for path in changed:
            print(f"stale: {path}")
        return 1

    print(f"agents: {len(agents)}")
    print(f"skills: {len(skill_dirs())}")
    print(f"command skills: {len(command_skills)}")
    if args.install:
        verb = "checked" if args.check else "installed"
        print(f"{verb}: {CODEX_HOME / 'AGENTS.md'}")
        print(f"{verb}: {CODEX_HOME / 'config.toml'}")
    else:
        print(f"generated: {LOCAL_AGENT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
