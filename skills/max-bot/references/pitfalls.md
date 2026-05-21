# Pitfalls — pre-commit checklist

Sweep this list before declaring a Max bot feature done. Each item is something we got wrong at least once in production.

## API surface

- [ ] No `/command` registration attempts. Text triggers in `message_created` handle help/menu, with Russian + English + slash variants.
- [ ] `user_id` extracted from the right place for the event type (`event.user`, `event.message.sender`, or `event.callback.user`).
- [ ] All callbacks handled in **one** `message_callback` registration that dispatches by payload prefix. No attempt to register multiple per-pattern handlers.
- [ ] Every callback path is matched (no silent drop). Unknown payloads logged at WARNING.
- [ ] `noop` payload handled — usually pagination counter buttons. Acknowledge with empty `send_callback(notification="")`.

## Inline keyboards

- [ ] Keyboard never exceeds 30 rows. Pagination at `MAX_PER_PAGE = 25` to leave room for nav/back/skip.
- [ ] When replacing a message via `send_callback`, `as_markup()` output is converted with `_to_attachment_button()` before stuffing into `MessageForCallback.attachments`.
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
