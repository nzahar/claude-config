#!/usr/bin/env bash
# Sync the Claude Code framework in ~/.claude into Kimi Code's user profile.
#
# Generated (and fully owned by this script): $KIMI_HOME/AGENTS.md (CLAUDE.md +
# rules/*.md, via rulesync), $KIMI_HOME/agents/*.md (agents/*.md, via rulesync,
# stale files removed), and the symlink $KIMI_HOME/lib -> ~/.claude/lib so the
# agents' ../lib/ links resolve. Skills need no sync: Kimi reads ~/.claude/skills
# natively. config.toml is never touched. Sync is manual: the user runs /sync-kimi
# (skills/sync-kimi/SKILL.md) from either CLI, which calls this script.
#
# Kept hook-safe anyway — the tooling failure paths exit 0 with a line on stderr
# (missing npx, a slow or offline registry, a non-zero rulesync exit); in --check
# mode the same paths exit 3 so a broken run is never read as "no drift". Non-default CLAUDE_CONFIG_DIR is
# refused rather than half-honoured — rulesync resolves the Claude tree from the
# home directory regardless, so the symlink and the generated text would point at
# different trees.
#
#   sync-kimi.sh          sync
#   sync-kimi.sh --quiet  sync, print nothing on success
#   sync-kimi.sh --check  render into a temp profile and diff against the live one;
#                         writes nothing under $KIMI_HOME (the ~/.rulesync scratch
#                         tree is still rebuilt), exits 1 on differences, 3 if the
#                         tooling failed and nothing could be compared
set -euo pipefail

RULESYNC_PKG="rulesync@16.14.0"
PER_CALL_TIMEOUT=25

quiet=0
check=0
for arg in "$@"; do
  case "$arg" in
    --quiet) quiet=1 ;;
    --check) check=1 ;;
    *) echo "sync-kimi: unknown argument: $arg" >&2; exit 2 ;;
  esac
done

bail() {
  echo "sync-kimi: $*" >&2
  [[ $check -eq 1 ]] && exit 3
  exit 0
}

claude_dir="$HOME/.claude"
if [[ -n "${CLAUDE_CONFIG_DIR:-}" ]]; then
  if [[ "$(cd "$CLAUDE_CONFIG_DIR" 2>/dev/null && pwd -P)" != "$(cd "$claude_dir" 2>/dev/null && pwd -P)" ]]; then
    bail "CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR differs from \$HOME/.claude; rulesync reads \$HOME/.claude only — not syncing"
  fi
fi
[[ -d "$claude_dir" ]] || bail "$claude_dir does not exist — nothing to sync"
command -v npx >/dev/null 2>&1 || bail "npx not found — not syncing"
command -v timeout >/dev/null 2>&1 || bail "timeout not found — not syncing"

KIMI_HOME="${KIMI_CODE_HOME:-$HOME/.kimi-code}"

rulesync() {
  local out
  if ! out="$(timeout "$PER_CALL_TIMEOUT" npx -y "$RULESYNC_PKG" "$@" 2>&1)"; then
    echo "$out" >&2
    bail "rulesync $1 failed or timed out after ${PER_CALL_TIMEOUT}s — not syncing"
  fi
  [[ $quiet -eq 1 || -z "$out" ]] || echo "$out"
}

expected_agents=$(find "$claude_dir/agents" -maxdepth 1 -name '*.md' | wc -l)

# rulesync resolves ~/.rulesync from HOME for the import side and ./.rulesync from
# cwd for subagents; cd'ing to HOME collapses both into one intermediate tree.
cd "$HOME"
mkdir -p "$HOME/.rulesync"
exec 9>"$HOME/.rulesync/.sync-kimi.lock"
flock -w 30 9 || bail "another sync-kimi run holds the lock — not syncing"
rm -rf "$HOME/.rulesync/rules" "$HOME/.rulesync/subagents"
rulesync import --global --targets claudecode --features rules,subagents --silent

generate_into() {
  # rulesync's KIMI_CODE_HOME names the profile dir itself (AGENTS.md and agents/
  # land at its root), which matches the KIMI_HOME definition above.
  KIMI_CODE_HOME="$1" rulesync generate --global --targets kimi-code \
    --features rules,subagents --delete --silent
  local got
  got=$(find "$1/agents" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l)
  [[ "$got" -eq "$expected_agents" ]] || bail "rulesync emitted $got agents, expected $expected_agents — an agent failed its strict frontmatter parse; fix it in $claude_dir/agents and re-run"
  [[ -s "$1/AGENTS.md" ]] || bail "rulesync emitted no AGENTS.md"
}

# Always render into a scratch profile first, so a partial or empty rulesync result
# is caught above before anything under $KIMI_HOME is replaced.
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
generate_into "$tmp"

if [[ $check -eq 1 ]]; then
  status=0
  diff -u "$KIMI_HOME/AGENTS.md" "$tmp/AGENTS.md" 2>&1 || status=1
  diff -ru "$KIMI_HOME/agents" "$tmp/agents" 2>&1 || status=1
  [[ "$(readlink "$KIMI_HOME/lib" 2>/dev/null || true)" == "$claude_dir/lib" ]] || { echo "lib symlink missing or wrong"; status=1; }
  exit $status
fi

mkdir -p "$KIMI_HOME"
[[ -e "$KIMI_HOME/lib" && ! -L "$KIMI_HOME/lib" ]] && bail "$KIMI_HOME/lib exists and is not a symlink — not replacing it"
rm -rf "$KIMI_HOME/agents"
cp -R "$tmp/agents" "$KIMI_HOME/agents"
cp "$tmp/AGENTS.md" "$KIMI_HOME/AGENTS.md"
ln -sfn "$claude_dir/lib" "$KIMI_HOME/lib"
[[ $quiet -eq 1 ]] || echo "sync-kimi: wrote $KIMI_HOME/AGENTS.md, $KIMI_HOME/agents/ ($expected_agents agents), $KIMI_HOME/lib -> $claude_dir/lib"
