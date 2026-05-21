---
name: max-bot
description: Build chat bots for the Max messenger (РФ) using the maxapi Python library. Trigger when the user mentions Max bot, maxapi, мессенджер Макс, бот для Макса, or asks to create/extend a Max-platform bot. Covers Max-vs-Telegram API differences, architectural patterns, and ready-to-use scaffolding templates.
---

# max-bot — building bots for the Max messenger

Max (мессенджер «Макс», РФ) exposes a Telegram-like bot API via the `maxapi` Python library, but the surface differs in ways that are **not well documented** and easy to get wrong on the first attempt. This skill captures the lessons from a production bot.

## When to apply

- New Max bot from scratch.
- Extending or debugging an existing `maxapi`-based bot.
- Porting a Telegram bot to Max.
- Any time the model is about to write `from maxapi import ...`.

## How to use this skill

1. **Read `references/api-differences.md` first** if writing handlers, callbacks, or keyboards. It enumerates the non-obvious differences from Telegram that cause real bugs.
2. **Read `references/architecture.md`** before designing module structure or state management.
3. **Read `references/pitfalls.md`** as a final pre-commit checklist.
4. **Use `templates/`** as starting point for new bots — copy and adapt, don't write from scratch.

## Core principles (the short version)

- **No `/commands`** in Max. Use Russian text triggers in `message_created` handler.
- **One `message_callback` handler** with payload-prefix routing (no per-pattern decorators like aiogram).
- **30-row inline keyboard limit** → reserve space for pagination/back/skip rows (use `MAX_PER_PAGE = 25`).
- **Three different paths to user_id** depending on event type — see `api-differences.md`.
- **`send_callback(MessageForCallback(...))`** replaces a message in response to a callback; semantics differ from Telegram's `edit_message_text`.
- **Long polling**, not webhooks.
- **Thin client**: keep domain state in your backend API; bot's local SQLite is only for ID mapping and persistent UI sessions.
- **Singleton bot/dp/api** at module level + lazy `from bot.main import ...` inside handlers to avoid circular imports.

## File map

```
references/
  api-differences.md   — Max vs Telegram API surface, gotchas, idioms
  architecture.md      — module layout, state split, background tasks, error handling
  pitfalls.md          — sweep this before commit; sourced from real production grief

templates/
  Dockerfile           — python:3.12-slim base
  docker-compose.yml   — prod profile, named volume
  requirements.txt     — minimal stack
  main.py.tmpl         — entry point with handlers + on_started + background loops
  db.py.tmpl           — aiosqlite with UPSERT mapping pattern
  keyboards.py.tmpl    — paginated inline keyboard builder
```

Templates are starting points — adapt names and add domain logic. The patterns inside (callback routing, pagination row format, lazy imports, `_to_attachment_button` helper) are the actual transferable knowledge.
