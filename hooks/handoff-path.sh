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

# The output must be a pure function of the path bytes. Bash's [^a-zA-Z0-9] matches
# characters under a UTF-8 locale and bytes under C, so "бот-один" sanitizes to 8
# dashes or 15 depending on ambient locale — and the hook (raw process env) and the
# skill (Bash tool, initialized from the user's profile) need not share one.
export LC_ALL=C

dir="${1:-$PWD}"

# Resolve our own location BEFORE cd'ing anywhere: BASH_SOURCE is relative when the
# script is invoked by a relative path, and by then $PWD is the project, not here.
CONFIG_DIR="$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"

# Fail loudly on an unusable dir instead of printing a plausible path for it: the
# callers' guard is "prints nothing / non-zero" (the skill then stops and asks the
# user, the hook exits 0), and an unreachable dir that answered anyway would slip
# straight past it. pwd -P also normalizes the non-git fallback, so a trailing slash
# cannot hash differently from the same path without one.
cd "$dir" 2>/dev/null || exit 1
root="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"

name="$(basename "$root")"
name="${name//[^a-zA-Z0-9]/-}"
hash="$(printf '%s' "$root" | sha1sum | cut -c1-8)"

printf '%s/handoffs/%s-%s.md\n' "$CONFIG_DIR" "$name" "$hash"
