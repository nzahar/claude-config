#!/usr/bin/env bash
# Maps a project directory to its handoff file path. Single source of truth: both
# handoff-inject.sh and the /handoff skill call this and use what it prints. A second
# derivation would have to agree byte-for-byte forever — when it drifted, the hook
# would look where nothing was written and inject nothing, with no visible signal.
#
# Prints the whole path, not just the stem, so handoffs/ is derived here too: callers
# expanding it themselves would disagree under a non-default CLAUDE_CONFIG_DIR.
#
# The stem is basename + a hash of the full path. Sanitizing alone is many-to-one:
# /root/Projects/a-b and /root/Projects/a/b collapse together, and two non-ASCII names
# of equal length collapse entirely (/root/Проекты/бот-один and /root/Проекты/бот-два
# both sanitize to dashes) — which would hand one project another's handoff and
# archive the original undelivered.
set -euo pipefail

dir="${1:-$PWD}"

root="$(cd "$dir" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null || true)"
root="${root:-$dir}"

name="$(basename "$root")"
name="${name//[^a-zA-Z0-9]/-}"
hash="$(printf '%s' "$root" | sha1sum | cut -c1-8)"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf '%s/handoffs/%s-%s.md\n' "$(dirname "$DIR")" "$name" "$hash"
