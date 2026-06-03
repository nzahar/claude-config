# Architecture patterns for Max bots

Apply by default unless there's a specific reason not to.

## Module layout

```
bot/
  __init__.py
  main.py             # Bot, Dispatcher, api singletons + handler registration + on_started
  config.py           # env vars, intervals, paths
  api_client.py       # backend API wrapper (HTTP)
  db.py               # SQLite (aiosqlite): id mapping + persistent UI sessions
  user_data.py        # in-memory per-user ephemeral state
  messages.py         # Russian message catalog (constants)
  formatters.py       # API response → display text
  keyboards.py        # InlineKeyboardBuilder factories
  handlers/
    __init__.py
    start.py          # bot_started
    errors.py         # error_wrapper decorator
    <feature>.py      # one file per feature/flow
  tasks/
    __init__.py
    notifications.py  # background pollers
```

This is a starting structure, not a law — collapse `tasks/` and `handlers/` into flat files for tiny bots.

## Singleton bot/dp/api with lazy imports

```python
# bot/main.py
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
api = BackendAPI()
```

Handlers import these **inside the function**, not at module top level:

```python
# bot/handlers/start.py
async def handle_bot_started(event):
    from bot.main import bot, api   # lazy — main.py imports this module too
    ...
```

`main.py` registers handlers from submodules; submodules need `bot`/`api`; the cycle is broken by deferring the import to call-time.

## Handler registration

```python
def _register_handlers():
    dp.bot_started()(start.handle_bot_started)
    dp.message_created()(errors.error_wrapper(invoice.handle_message))
    dp.message_callback()(errors.error_wrapper(region.handle_callback))
```

Wrap every handler in `error_wrapper` so a single exception doesn't crash polling.

```python
# bot/handlers/errors.py
def error_wrapper(handler):
    async def wrapped(event, *a, **kw):
        try:
            return await handler(event, *a, **kw)
        except Exception:
            logger.exception("Handler %s failed", handler.__name__)
    return wrapped
```

## State split: ephemeral vs persistent

| Kind                              | Where                       | Survives restart? |
|-----------------------------------|-----------------------------|-------------------|
| Multi-step UI selection (region wizard mid-flow) | `bot/user_data.py` in-memory dict | No |
| `max_user_id ↔ backend_user_id` mapping | SQLite `users` table | Yes |
| Persistent UI session (e.g. invoice awaiting confirmation across restart) | SQLite `*_sessions` table | Yes |
| Domain data (regions, prices, history) | Backend API (not the bot) | Yes — owned by API |

**Rule**: the bot is a thin client. If a fact needs to outlive the bot process AND is part of the domain, it lives in the backend API, not in the bot's SQLite.

### `user_data.py` skeleton

```python
_state: dict[int, dict] = {}

def get(uid: int) -> dict:
    return _state.setdefault(uid, {})

def set_value(uid: int, key: str, value) -> None:
    _state.setdefault(uid, {})[key] = value

def pop(uid: int, key: str) -> None:
    _state.get(uid, {}).pop(key, None)
```

Flat, no expiry, no persistence. If you need any of those, rethink whether it belongs here.

### SQLite UPSERT pattern

```sql
INSERT INTO users (max_user_id, api_user_id, region_name)
VALUES (?, ?, ?)
ON CONFLICT(max_user_id) DO UPDATE SET
    api_user_id = excluded.api_user_id,
    region_name = COALESCE(excluded.region_name, users.region_name)
```

`COALESCE(excluded.x, users.x)` lets you upsert partial updates without overwriting existing fields with NULL. Useful when one code path knows the user_id mapping but not the region, and another knows the region but not (yet) the mapping.

## Background tasks

```python
async def _loop(coro, interval, name):
    await asyncio.sleep(10)  # initial delay — let polling stabilize
    while True:
        try:
            await coro()
        except Exception:
            logger.exception("Background task %s failed", name)
        await asyncio.sleep(interval)

# launched from on_startup():
asyncio.create_task(_loop(poll_notifications, 300, "notifications"))
```

- Always wrap the loop body in try/except so one failure doesn't kill the loop.
- Initial `sleep(10)` avoids racing the polling start.
- Discrete intervals per task (not one big tick).
- Don't `await` the create_task — fire and forget; lifecycle ends with the process.

## Long polling, not webhooks

Use `dp.start_polling(bot)`. Avoid webhooks unless you have a hard reason — they require public HTTPS, certificate management, and reverse-proxy routing. Long polling has zero infra surface.

## Persistent UI session pattern

For multi-step flows where the user might disconnect, restart their client, or the bot might restart between "I uploaded a file" and "I clicked confirm":

1. After the long-running operation completes (e.g. invoice OCR), persist the result to a SQLite session table keyed by `max_user_id`.
2. Mirror it into in-memory `user_data` for fast access.
3. On callback, try in-memory first; on miss, fall back to SQLite (and rehydrate in-memory).
4. On flow completion or cancel, delete from both.

```python
async def _resolve_invoice_id(uid: int) -> str | None:
    invoice_id = user_data.get(uid).get("current_invoice_id")
    if invoice_id:
        return invoice_id
    session = await db.get_invoice_session(uid)
    if session:
        invoice_id, items = session
        user_data.set_value(uid, "current_invoice_id", invoice_id)
        user_data.set_value(uid, "invoice_items", items)
        return invoice_id
    return None
```

If both miss → session expired, show a friendly message and reset.

## Backend API integration (when applicable)

If the bot is a client to your own HTTP API:

- Single `api_client.py` wrapping `httpx.AsyncClient` with `timeout=` always set.
- Pass a `platform="max"` (or equivalent) field on user-creating endpoints, so the backend can distinguish Max users from Telegram/web users sharing the same DB.
- Use `external_id=str(max_user_id)` as the stable identity key from the bot's perspective.
- Define typed exceptions (`RateLimitError`, `APIError`) in the client; handlers catch them and produce user-facing Russian messages.

## Logging

- `logging` module, not `print`.
- `logger = logging.getLogger(__name__)` per module.
- `logger.exception(...)` inside `except` blocks (gets the traceback automatically).
- Log handler entries at INFO level only for state transitions worth replaying; DEBUG for chatty paths.
- No `breakpoint()` / `pdb` in committed code.

## Russian-language UX

- All user-facing strings centralized in `bot/messages.py` as named constants.
- `.format(...)` for parameterized messages, not f-strings (so the catalog stays scannable).
- Always provide both English and Russian forms for text commands (`«помощь»/«help»`).
- Date/time via `datetime.now(tz=UTC)` — never naive.
