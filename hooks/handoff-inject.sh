#!/usr/bin/env bash
# SessionStart hook: inject the handoff written by /handoff into a fresh session,
# then consume it so it is never injected twice.
#
# The file is moved into _archive/ BEFORE it is read: mv is atomic, so two sessions
# starting in one project cannot both consume it. The loser of that race exits 0 and
# gets nothing — reading the original path as a fallback would reintroduce exactly
# the double-inject this ordering exists to prevent.
#
# Every failure path exits 0 silently. This runs at the start of every session in
# every project, so a non-zero exit here would break startup everywhere. Three
# commands are deliberately unguarded because they cannot fail here: the DIR lookup
# below (this script is executing, so its directory exists), and date + the final
# `jq -n` (neither fails on the valid input they are given).
set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

input="$(cat)" || exit 0
src="$(jq -r '.source // empty' <<<"$input" 2>/dev/null || true)"
cwd="$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null || true)"

# resume/compact already carry the handoff in their restored context; consuming
# there would burn the file for nothing.
case "$src" in
  startup|clear) ;;
  *) exit 0 ;;
esac

handoff="$("$DIR/handoff-path.sh" "${cwd:-$PWD}" 2>/dev/null)" || exit 0
[[ -n "$handoff" ]] || exit 0

ARCHIVE="$(dirname "$handoff")/_archive"
mkdir -p "$ARCHIVE" 2>/dev/null || exit 0

# Ahead of the early exit below: retention that only ran after a successful consume
# would never sweep a project whose handoff is never claimed again.
find "$ARCHIVE" -maxdepth 1 -name '*.md' -mtime +7 -delete 2>/dev/null || true

[[ -f "$handoff" ]] || exit 0

stem="$(basename "$handoff" .md)"
archived="$ARCHIVE/$stem-$(date -u +%Y-%m-%dT%H-%M-%SZ).md"
mv "$handoff" "$archived" 2>/dev/null || exit 0

body="$(cat "$archived" 2>/dev/null || true)"
[[ -n "$body" ]] || exit 0

context="# Session handoff (single-use — already consumed)

Written by \`/handoff\` in an earlier session and injected once. The file has been
moved to \`$archived\` and will not be injected again; nothing further reads it.

Treat § Verification status as claims, not facts — re-run the commands listed there
before relying on them. Continue from § Next steps.

$body"

jq -n --arg ctx "$context" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
