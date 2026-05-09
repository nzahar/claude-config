# /learn - Extract Reusable Patterns

Analyze the current session and extract any patterns worth saving as skills.

## Trigger

Run `/learn` at any point during a session when you've solved a non-trivial problem.

## What to Extract

Look for:

1. **Error Resolution Patterns**
    - What error occurred?
    - What was the root cause?
    - What fixed it?
    - Is this reusable for similar errors?

2. **Debugging Techniques**
    - Non-obvious debugging steps
    - Tool combinations that worked
    - Diagnostic patterns

3. **Workarounds**
    - Library quirks
    - API limitations
    - Version-specific fixes

4. **Project-Specific Patterns**
    - Codebase conventions discovered
    - Architecture decisions made
    - Integration patterns

## Output Format

Create a skill file at `~/.claude/skills/learned/[pattern-name].md` using this exact template:

```markdown
---
name: <Descriptive Pattern Name in Title Case>
description: <one-line summary, ~120 chars max — used to decide relevance in future sessions>
type: feedback
---

# <Descriptive Pattern Name>

**Extracted:** YYYY-MM-DD
**Context:** <one-sentence description of when this applies>

## Problem
<What problem this solves — be specific>

## Solution
<The pattern/technique/workaround>

## Example
<Code example if applicable — keep tight, link out for long code>

## When to Use
<Trigger conditions — what should activate this skill>
```

The YAML frontmatter is mandatory. It has three required fields:

- `name` — pretty title in Title Case, mirrors the H1 heading below
- `description` — one-line summary that future sessions read to decide whether the skill is relevant. Be specific: "X happens, fix is Y" beats "tips for X"
- `type: feedback` — fixed value for learned-skills (matches the auto-memory feedback type: a rule extracted from a past failure or success)

## Process

1. Review the session for extractable patterns
2. Identify the most valuable/reusable insight
3. Draft the skill file with the YAML frontmatter and save it to `~/.claude/skills/learned/`
4. Inform the user what was saved

## Notes

- Don't extract trivial fixes (typos, simple syntax errors)
- Don't extract one-time issues (specific API outages, etc.)
- Focus on patterns that will save time in future sessions
- Keep skills focused — one pattern per skill
- The `description:` field is what future Claude sessions see in skill summaries; treat it as the index entry, not as filler
