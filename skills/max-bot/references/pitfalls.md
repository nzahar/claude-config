# Pitfalls — pre-commit checklist

Sweep this list before declaring a Max bot feature done.

## API surface

- [ ] No `/command` registration attempts. Text triggers in `message_created` handle help/menu, with Russian + English + slash variants.
- [ ] `user_id` extracted from the right place for the event type (`event.user`, `event.message.sender`, or `event.callback.user`).
- [ ] **`chat_id ≠ user_id` even in DIALOG** chats. `recipient.chat_id` is the dialog room ID; `sender.user_id` is the user. They are independent integers (e.g. `chat_id=271170814` vs `user_id=11004847` from real prod data). Do NOT mirror the TG pattern of `external_user_id = str(chat_id)` — TG's invariant `chat.id == from_user.id` in private DMs is a Telegram-side feature, not Max. Use `str(user_id)` for cross-channel identity. Tests MUST use distinct integers for `chat_id` and `user_id` in fixtures, otherwise the bug is invisible. The two paths to watch: message handler (chat_id-keyed debouncer flush) and callback handler (`event.callback.user.user_id`) MUST resolve to the same `external_user_id` or Core will treat them as two separate users → confirm tokens land in empty conversations → `confirm_stale` loop.
- [ ] All callbacks handled in **one** `message_callback` registration that dispatches by payload prefix. No attempt to register multiple per-pattern handlers.
- [ ] Every callback path is matched (no silent drop). Unknown payloads logged at WARNING.
- [ ] `noop` payload handled — usually pagination counter buttons. Acknowledge with empty `send_callback(notification="")`.
- [ ] Outbound messages get only ONE checkmark (✓) in Max client, not two (✓✓). maxapi 0.4 has no `markAsRead`-equivalent for inbound messages; the second tick is a maxapi feature, not a bug. Note for UX expectation management — users may interpret single-check as "bot didn't see the message". Surface in `help` text or docs if it confuses real users.

## Inline keyboards

- [ ] Keyboard never exceeds 30 rows. Pagination at `MAX_PER_PAGE = 25` to leave room for nav/back/skip.
- [ ] When replacing a message via `send_callback`, `as_markup()` output is converted with `_to_attachment_button()` before stuffing into `MessageForCallback.attachments`.
- [ ] **`MessageForCallback(attachments=None)` PRESERVES the existing inline keyboard** in maxapi 0.4. To REMOVE the keyboard after a confirm/cancel callback (so user can't double-press), pass `attachments=[]` explicitly. Easy to miss — the field is typed `list[AttachmentInput] | None = None` and reads like "no attachments to add" but actually means "no change". Symptom of getting it wrong: button stays live after confirm; second press fires the callback again; Core returns `confirm_replay` idempotently but UX looks broken.
- [ ] `Intent.POSITIVE/NEGATIVE` used only for confirm/cancel/destructive — not decoration.
- [ ] If the handler needs the button's text (not just payload), `_find_button_text(event, payload)` is used to recover it from the original message attachments.
- [ ] Pagination payload format consistent: `page_{prefix}_{page}_{parent_id}`.

## File handling

- [ ] Forwarded messages handled: empty `body.attachments` + `link.type == FORWARD` → look in `event.message.link.message.attachments`.
- [ ] File downloaded via `aiohttp` from `attachment.payload.url`, not via a (non-existent) `bot.get_file()`.
- [ ] MIME type derived from extension (for `AttachmentType.FILE`) or hardcoded `image/jpeg` (for `AttachmentType.IMAGE`).
- [ ] Unsupported MIME → user-facing Russian message, not a crash.
- [ ] Empty file bytes → handled, not assumed.

## Long messages

- [ ] Texts that may exceed Max's per-message limit are chunked. Last chunk carries the keyboard; earlier chunks are plain text.

## State

- [ ] Anything stored in `user_data` is acceptable to lose on restart. If not, it's in SQLite.
- [ ] SQLite UPSERT uses `COALESCE(excluded.x, table.x)` for fields that may be partially updated.
- [ ] `bot_started` handler is idempotent — works for first-time AND returning users.
- [ ] Persistent UI session (invoice/order/etc.) is cleaned up on completion AND cancellation, in both in-memory and SQLite.
- [ ] `_resolve_*` helpers fall back from in-memory to SQLite, rehydrate in-memory, return None on full miss.

## Architecture

- [ ] `bot`, `dp`, `api` declared once at module level in `main.py`.
- [ ] Handler modules import them with `from bot.main import ...` **inside functions**, never at module top.
- [ ] **Entry point is `python -m <package>`, NOT `python -m <package>.main`.** The package dir has `__main__.py` that does `from <package>.main import main; asyncio.run(main())`. Why: `python -m <package>.main` loads `main.py` as `__main__` module; handler imports `from <package>.main import bot` triggers a SEPARATE load as `<package>.main` (different module object). `main()`'s `global bot = Bot(...)` lands in `__main__.bot`; handlers see `<package>.main.bot` which is still `None`. Symptom: bot silently ignores all events; only proves the bug on prod with real polling, because tests that import the module once (under its name, not as `__main__`) accidentally hide the alias. SAME bug as classic Python's "circular import / two module copies" — but here triggered by the entry-point flag, not by user code. The `__main__.py` indirection makes `__main__` a tiny launcher and lets `<package>.main` load exactly once under its proper name.
- [ ] All handlers wrapped in `error_wrapper` — one bad handler doesn't crash polling.
- [ ] Background tasks: launched from `@dp.on_started()`, looped with try/except inside, initial `sleep(10)` before first iteration.
- [ ] DB init (`init_db()`) called from `on_startup()`, awaited, before background tasks.

## Backend integration

- [ ] `httpx.AsyncClient` always has `timeout=` set.
- [ ] Bot sends `platform="max"` (or your project's equivalent) on user-creating endpoints.
- [ ] `external_id=str(max_user_id)` as stable identity key.
- [ ] Typed exceptions (`RateLimitError`, `APIError`) raised by client and caught by handlers; each one produces a Russian user-facing message.

## Hygiene

- [ ] `logging` everywhere, no `print`. `logger.exception(...)` inside `except`.
- [ ] No `breakpoint()` / `pdb.set_trace()` / debug prints left behind.
- [ ] All `datetime` calls use `tz=UTC` (or other explicit tz). No naive `datetime.now()`.
- [ ] `.env` not committed. `.env.example` lists all required keys with placeholder values.
- [ ] Russian user-facing strings live in `messages.py`, not inlined.

## Deploy (if Docker-based)

- [ ] Container has `restart: unless-stopped`.
- [ ] Persistent SQLite path is on a named volume, not in the image.
- [ ] No host port mapping unless webhook-mode (long polling needs none).
- [ ] If deploying multiple environments to the same host with limited Docker network pool, fix the subnet explicitly in `docker-compose.test.yml` (`networks.<name>.ipam.config[0].subnet`).
