#!/usr/bin/env python3
"""PreToolUse hook — block `cd <path> && git ...` (and `; git ...`) chains.

Reason this exists: chaining `cd` before `git` triggers Claude Code's
"untrusted hooks" security prompt every time, slowing down a routine
operation. Worse, the assistant has a memory note about avoiding the
pattern and still sometimes generates it. A hook enforces the rule
mechanically — the harness blocks the command before it reaches the user
prompt, and the message in stderr tells the assistant why.

CWD is already the repo root in normal sessions, so just running `git ...`
directly works. For multi-repo work, use `git -C <path> ...` instead.
"""
from __future__ import annotations

import json
import re
import sys

# Matches:
#   `cd <path> && git ...`
#   `cd <path>; git ...`
#   `cd <path> ; git ...`
#   `cd <path> && FOO=bar git ...`
# Does NOT match a `cd` that is itself preceded by another command (so a
# legitimate `pushd ... && cd ... && something` is unaffected unless it ends
# in git).
_PATTERN = re.compile(
    r"\bcd\s+\S+\s*(?:&&|;)\s*(?:[A-Z_][A-Z0-9_]*=\S+\s+)*git\b"
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # malformed input — don't block by accident
    tool_input = data.get("tool_input") or {}
    cmd = tool_input.get("command", "")
    if not isinstance(cmd, str):
        return 0
    if _PATTERN.search(cmd):
        sys.stderr.write(
            "Blocked: 'cd <path> && git ...' is forbidden.\n"
            "It triggers an untrusted-hooks security prompt every time and "
            "changes git's operating environment. CWD is already the repo "
            "root in this session; just run `git ...` directly. For a "
            "different repo, use `git -C <path> ...`.\n"
        )
        return 2  # exit 2 = block; stderr is forwarded to the assistant
    return 0


if __name__ == "__main__":
    sys.exit(main())
