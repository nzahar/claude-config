---
name: learned-patterns
description: Use this when a task resembles a recurring failure mode or technical pattern captured in the local learned knowledge base under skills/learned.
---

# Learned Patterns

This skill exposes the local learned-pattern knowledge base to Codex.

Use it when the user asks about a known pitfall, debugging pattern, deployment
pattern, data-processing gotcha, or when the current task resembles one of the
entries under this directory.

Workflow:

1. Search `skills/learned/*.md` by task keywords.
2. Read only the matching learned entry or entries.
3. Apply the entry as guidance, not as a blind rule.
4. If no entry matches, proceed normally and do not invent a learned pattern.

Do not load every learned entry into context. The individual files are the
source of truth.
