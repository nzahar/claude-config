---
paths: ["**/*.go"]
---

## Code Style — Go

### Project Layout

Standard structure: `cmd/`, `internal/`, `pkg/` (if a library).

### Error Handling

- Always check `error`: `if err != nil { return ..., fmt.Errorf("context: %w", err) }`
- Wrap errors with context via `fmt.Errorf("doing X: %w", err)`
- Never `panic()` in business logic — only in `main`/`init` or unrecoverable states

### Naming

- `camelCase` for unexported, `PascalCase` for exported
- Interfaces: `-er` suffix where appropriate (`Reader`, `Handler`)
- Receivers: a short 1–2-letter name (`s` for `Server`, `r` for `Repo`)

### Concurrency

- Always pass `context.Context` as the first argument
- Goroutines: make sure there is a cancellation mechanism (context, done channel)
- Do not start a goroutine without a way to stop it
- `defer` inside a loop is bad — extract into a separate function

### Formatting

- `gofmt` / `goimports` — non-negotiable
- Comments on exported identifiers — required (golint)
