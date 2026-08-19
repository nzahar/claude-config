---
name: learn
description: "Save a reusable lesson from the current session as a proper skill under ~/.claude/skills/<topic>/SKILL.md — or extend an existing topic skill — so the native skill loader surfaces it by description in future sessions. Invoke when the user types /learn or asks to save a lesson / pattern from this session (сохрани как skill, запомни паттерн). Never invoke unasked."
---

# /learn — save a lesson as a skill

Bar: would this save a future session real time, and is it non-obvious — an empirical finding, a quirk of a tool or library, a trap that already cost this session? Generic knowledge, one-off project facts and trivial fixes do not qualify; if nothing in the session clears the bar, say so and write nothing.

## 1. Topic first, then file

Skills are per **topic**, not per incident — `skills/clickhouse/`, `skills/ghcr-actions/`, `skills/pytorch-seed-ablation/`. List `~/.claude/skills/*/SKILL.md` descriptions; if the lesson belongs to an existing topic, **append a section** to that skill and extend its `description` so the new trigger is discoverable. Only create a new `skills/<topic>/SKILL.md` when no topic fits. Two lessons on one tool go in one skill.

## 2. Write it

Frontmatter: `name: <topic>` (kebab-case, equals the directory) and `description` — the only thing future sessions see before loading the skill, so it must name the **trigger situation** and the **gist of the answer** ("X happens; fix is Y"), under ~450 chars. No other frontmatter fields.

Body per lesson: a heading, **Context** (one sentence: when this applies), **Problem**, **Solution** (with a tight code example when code is the point), **When to use** (the trigger conditions, concretely). Verbatim error strings, real numbers from measurements. Keep it to what a future session needs to act — history and narrative are cut.

## 3. Report

Tell the user the path and whether it was a new skill or an extension, in one or two lines. Do not commit.
