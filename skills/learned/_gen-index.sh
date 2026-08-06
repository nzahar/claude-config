#!/usr/bin/env bash
# SessionStart hook: inject an index of /learn-distilled skill notes so they are
# discoverable in every session. The individual notes live as flat *.md files here
# and are NOT picked up by the native skill loader (that needs <name>/SKILL.md), so
# this hook is the only always-on mechanism that surfaces them (SKILL.md's keyword
# search is the on-demand one).
#
# SKILL.md is the folder's native skill entry point (added for the Codex adapter;
# Claude Code's personal-skill loader picks it up too), not a note — excluded here
# so it does not appear in the index as a self-referential pseudo-note.
#
# Emits SessionStart additionalContext JSON listing each note's name + description.
# Exits 0 with no output when jq/awk are unavailable or the folder is empty, so a
# tool-less box degrades to "no index" silently instead of erroring every session.
# An unreadable note is skipped; a note without line-1 frontmatter falls back to
# its filename.
set -euo pipefail

command -v jq  >/dev/null 2>&1 || exit 0
command -v awk >/dev/null 2>&1 || exit 0

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
shopt -s nullglob
notes=("$DIR"/*.md)
[[ ${#notes[@]} -eq 0 ]] && exit 0

index=""
for f in "${notes[@]}"; do
  base="$(basename "$f")"
  [[ "$base" == "SKILL.md" ]] && continue
  name="$(awk 'NR==1&&/^---/{f=1;next} f&&/^---/{exit} f&&/^name:/{sub(/^name:[ \t]*/,"");print;exit}' "$f")" || continue
  desc="$(awk 'NR==1&&/^---/{f=1;next} f&&/^---/{exit} f&&/^description:/{sub(/^description:[ \t]*/,"");print;exit}' "$f")"
  [[ -z "$name" ]] && name="$base"
  index+="- **$name** — ${desc:-(no description)}  \`learned/$base\`"$'\n'
done

[[ -z "$index" ]] && exit 0

context="# Learned skills index (distilled via /learn)

Cross-project lessons saved in \`~/.claude/skills/learned/\`. Index only — when a task matches one, Read the full note at that path before acting.

$index"

jq -n --arg ctx "$context" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
