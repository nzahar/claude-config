---
paths: ["**/*.py"]
---

## Code Style — Python

### Imports

Строгий порядок: `from __future__ import annotations` → stdlib → third-party → local.
Каждая группа разделена пустой строкой. Не используй `import *`.

### Type Hints

- Используй modern syntax: `dict[str, Any]`, `list[int]`, `str | None` (не `Dict`, `List`, `Optional`)
- `Optional` допустим в сигнатурах public-функций для ясности
- `from __future__ import annotations` — всегда первая строка файла
- `TYPE_CHECKING` для тяжёлых импортов которые нужны только для аннотаций

### Naming

- `snake_case` для функций и переменных
- `_private_prefix` для внутренних хелперов, не являющихся частью public API
- `UPPER_CASE` для констант на уровне модуля
- `_UPPER_CASE` для приватных констант (например `_CHUNK`, `_UPDATE_COLS`)

### Module Layout

```
from __future__ import annotations
# stdlib
# third-party
# local

CONSTANTS = ...

# ── Section ──────────────────────────────────────

def _helpers():
    ...

def public_functions():
    ...
```

Используй `# ── Section ───` em-dash разделители для визуальной группировки в длинных файлах.

### Docstrings

- Только для public API и неочевидных функций
- Не пиши docstring если имя функции полностью объясняет что она делает
- Формат: краткое описание + детали если нужны. Без шаблонных `Args:/Returns:` секций, если это не библиотека

### Error Handling

- FastAPI endpoints: `HTTPException` с конкретным status code и detail
- Background tasks: `try/except Exception` + `logger.exception()` + обновление статуса в БД
- Не глотай ошибки молча. Логируй и обновляй состояние

### Async

- `asyncio.to_thread()` для sync CPU-heavy вызовов в async-функциях (pandas, openpyxl, файловый I/O)
- `async with SessionLocal() as session:` — каждая операция в своём контексте
- Не блокируй event loop

### Formatting

- F-strings для строк. `%s` для logging (`logger.info("msg %s", val)`)
- Line length: стремись к <100, но читаемость важнее строгого лимита
- Комментарии — только когда код не объясняет себя сам. Не комментируй очевидное

### Dataclasses

`@dataclass(frozen=True)` с дефолтами. Inline-комментарии для неочевидных параметров.

### Conda Environment

Перед запуском Python через Bash — определи окружение из конфига проекта:

1. Есть `environment.yml` → взять имя из поля `name:`
2. Нет файла → проверить `CLAUDE.md` / `README.md` / спросить пользователя

Использовать полный путь к бинарнику: `/Users/zakharnedashkovskiy/miniforge3/envs/<name>/bin/python`

Никогда не использовать `python`, `python3`, `conda run` — только прямой путь к нужному окружению.