---
paths: ["**/*.go"]
---

## Code Style — Go

### Project Layout

Стандартная структура: `cmd/`, `internal/`, `pkg/` (если библиотека).

### Error Handling

- Всегда проверяй `error`: `if err != nil { return ..., fmt.Errorf("context: %w", err) }`
- Wrap errors с контекстом через `fmt.Errorf("doing X: %w", err)`
- Никогда `panic()` в бизнес-логике — только в `main`/`init` или необратимые состояния

### Naming

- `camelCase` для unexported, `PascalCase` для exported
- Interfaces: суффикс `-er` когда уместно (`Reader`, `Handler`)
- Receivers: короткое имя из 1-2 букв (`s` для `Server`, `r` для `Repo`)

### Concurrency

- Всегда передавай `context.Context` первым аргументом
- Goroutines: убедись что есть механизм отмены (context, done channel)
- Не запускай goroutine без способа её остановить
- `defer` внутри цикла — плохо, вынеси в отдельную функцию

### Formatting

- `gofmt` / `goimports` — без вариантов
- Комментарии на exported — обязательны (golint)
