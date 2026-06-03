---
paths: ["**/*.go"]
---

## Code Style — Go

### Project Layout

Standard structure: `cmd/`, `internal/`, `pkg/` (if a library).

### Error Handling

- Always check `error`: `if err != nil { return ..., fmt.Errorf("context: %w", err) }`
- Never `panic()` in business logic — only in `main`/`init` or unrecoverable states

### Naming

- `camelCase` for unexported, `PascalCase` for exported
- Interfaces: `-er` suffix where appropriate (`Reader`, `Handler`)
- Receivers: a short 1–2-letter name (`s` for `Server`)

### Concurrency

- Always pass `context.Context` as the first argument
- Goroutines: make sure there is a cancellation mechanism (context, done channel)
- No `defer` inside a loop — extract into a separate function

### Formatting

- `gofmt` / `goimports` — non-negotiable
- Comments on exported identifiers — required (golint)
