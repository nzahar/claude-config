# Max API — differences from Telegram and non-obvious behavior

The `maxapi` Python library is loosely modeled on Telegram bot libraries (aiogram, python-telegram-bot), but the API surface differs. This file enumerates the differences.

## Commands and triggers

Max **does not support** the `/command` UI menu Telegram users expect.

Pattern: handle commands as text inside `message_created`, accepting Russian + English + slash variants:

```python
text = (body.text or "").strip().lower()
if text in ("помощь", "help", "/help"):
    await handle_help(chat_id)
    return
if text in ("регион", "region", "/region", "/start"):
    ...
```

Always document the available text commands in the `«помощь»` response — there's no other discovery surface.

## Three paths to user_id

`user_id` lives in different places depending on the event type:

| Event                 | Path                                  |
|-----------------------|---------------------------------------|
| `bot_started`         | `event.user.user_id`                  |
| `message_created`     | `event.message.sender.user_id`        |
| `message_callback`    | `event.callback.user.user_id`         |

Easy to copy-paste the wrong one. Add a tiny helper if you reach for it more than twice.

### chat_id vs user_id — they're different even in DIALOG

In Max DIALOG chats `event.message.recipient.chat_id` is the **dialog room ID** and `event.message.sender.user_id` is the **user ID** — they are independent integers (real prod: `chat_id=271170814`, `user_id=11004847`). This breaks the Telegram intuition where `chat.id == from_user.id` in private DMs (TG-side invariant). For any external mapping / cross-channel identity in Max, use `user_id`. Use `chat_id` only as the destination of `bot.send_message(chat_id=...)`. Tests MUST use distinct integers for the two fields — fixtures like `chat_id=7, user_id=7` mask the bug entirely. The pattern bites hardest when message-handling code keys conversation state on `chat_id` and callback-handling code keys on `user_id`: same physical user generates two parallel conversations server-side.

## Callback routing

Telegram libraries (aiogram) let you decorate handlers per callback pattern. **Max does not.** You register **one** `message_callback` handler and dispatch by payload prefix yourself:

```python
async def handle_callback(event: MessageCallback):
    payload = event.callback.payload or ""
    if payload == "select_region":
        await _handle_select_region(event)
    elif payload.startswith("fd_"):
        await _handle_fd_selected(event)
    elif payload.startswith("page_"):
        await _handle_page(event)
    elif payload == "noop":
        await _handle_noop(event)
    else:
        logger.warning("Unknown callback payload: %s", payload)
```

**Convention**: pick payload prefixes per feature (`fd_`, `reg_`, `dist_`, `inv:`, `mute_sub_`) and a sentinel `noop` for non-clickable buttons (page counters etc.). Keep prefixes short — payload is bandwidth-limited.

## Inline keyboards

### Building

```python
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.enums.intent import Intent

builder = InlineKeyboardBuilder()
builder.row(CallbackButton(text="Подтвердить", payload="ok", intent=Intent.POSITIVE))
builder.row(CallbackButton(text="Отмена", payload="cancel", intent=Intent.NEGATIVE))
markup = builder.as_markup()  # returns Attachment
```

### 30-row hard limit

Max rejects keyboards with more than ~30 rows. **Reserve rows** for pagination (1) + back (1) + skip (1) = 3 overhead. Practical `ITEMS_PER_PAGE = 25`.

### `Intent` enum

`Intent.POSITIVE` (green-ish) and `Intent.NEGATIVE` (red-ish) visually color buttons. No analog in Telegram. Use sparingly: confirm/cancel, destructive actions.

### Pagination row format

Convention that works:

```
page_{prefix}_{page_num}_{parent_id}      # nav arrows
noop                                       # the page counter button
```

The counter button uses payload `"noop"`; the dispatcher acknowledges it with empty `send_callback(notification="")` so the client doesn't show a loading spinner.

### Sending vs replacing

- **Send fresh message with keyboard**: `bot.send_message(chat_id=..., text=..., attachments=[markup])`.
- **Replace message in response to a callback** (analog of `edit_message_text`):

  ```python
  from maxapi.types.updates.message_callback import MessageForCallback
  from maxapi.types.attachments.buttons.attachment_button import AttachmentButton

  def _to_attachment_button(markup) -> AttachmentButton:
      return AttachmentButton(type=markup.type, payload=markup.payload)

  msg = MessageForCallback(text=text, attachments=[_to_attachment_button(markup)])
  await bot.send_callback(callback_id=event.callback.callback_id, message=msg)
  ```

  **`as_markup()` returns `Attachment`, not `AttachmentButton`.** `MessageForCallback` requires `AttachmentButton`. The conversion helper is mandatory — without it you'll get cryptic validation errors.

### Recovering button text from callback

Callback events carry the **payload only**, not the button text the user saw. To remember the human-readable label (e.g. region name), look it up in the original message attachments:

```python
def _find_button_text(event: MessageCallback, payload: str) -> str:
    if not event.message or not event.message.body or not event.message.body.attachments:
        return ""
    for att in event.message.body.attachments:
        if hasattr(att, "payload") and hasattr(att.payload, "buttons"):
            for row in att.payload.buttons:
                for btn in row:
                    if hasattr(btn, "payload") and btn.payload == payload:
                        return btn.text
    return ""
```

## File attachments

Max sends attachments with a download URL in `attachment.payload.url`. There is no `bot.get_file()` style helper — fetch with `aiohttp` directly:

```python
async with aiohttp.ClientSession() as session:
    async with session.get(att.payload.url) as resp:
        data = await resp.read()
```

### Attachment types

Inspect `att.type`:
- `AttachmentType.IMAGE` — payload has `.url`, no filename. Assume jpeg.
- `AttachmentType.FILE` — payload has `.url`; filename available via `getattr(att, "filename", None)`. Determine MIME from extension yourself.

### Forwarded messages

When a user **forwards** a file (rather than uploading), `event.message.body.attachments` is **empty**. The original attachment lives at:

```python
from maxapi.enums.message_link_type import MessageLinkType

attachments = body.attachments or []
if not attachments and event.message.link and event.message.link.type == MessageLinkType.FORWARD:
    forwarded = event.message.link.message
    if forwarded:
        attachments = forwarded.attachments or []
```

Easy to miss — users will forward invoices/photos and report "bot ignores me".

## Sending messages

`bot.send_message` is overloaded on the recipient kwarg:
- `chat_id=...` — when you have a chat context (e.g. from `event.message.recipient.chat_id`).
- `user_id=...` — when sending direct/private (e.g. notifications without an active chat event).

These are not interchangeable. Pick deliberately based on context.

## Message length

Max enforces a per-message text length limit (similar order of magnitude to Telegram's 4096). For long content (invoice summaries, analytics blocks), implement chunking. A simple block-by-block accumulator with a length cap works fine.

## `bot_started` event

Fires when a user opens the bot for the first time **or** clicks "Start" again later. It's not a one-time onboarding — handle it idempotently:

```python
@dp.bot_started()
async def handle_bot_started(event: BotStarted):
    user_id = event.user.user_id
    # upsert user, check existing state, decide between welcome / welcome_back
```

## Polling lifecycle

```python
dp = Dispatcher()

@dp.on_started()
async def on_startup():
    # init DB, launch background tasks here — runs once after polling starts
    await init_db()
    asyncio.create_task(_loop(...))

asyncio.run(dp.start_polling(bot))
```

`@dp.on_started()` is the right place for one-time async init. Don't try to run init synchronously before `start_polling`.
