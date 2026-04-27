# Global CLAUDE.md

## Language & Communication

- Отвечай на русском если я пишу на русском, на английском если на английском
- Код, коммиты, PR, комментарии в коде — всегда на английском
- Будь кратким. Не повторяй то, что я уже вижу в диффе

## Verification Before Claims

**No completion claim without fresh verification evidence in the current message.**

If you are about to say that tests pass, lint passes, the fix works, the migration ran, the build succeeded, the dependency is installed, the endpoint returns 200, the data loaded, the refactor is equivalent, or anything else of that shape — run the command that proves it *in this message* and include the output (or a concise summary of it).

Evidence from earlier in the session does not count. Output from a previous attempt does not count. "Should work" does not count. Type-check passing is not a substitute for tests passing. Building is not a substitute for running. Running is not a substitute for checking exit code.

This applies equally to:
- Implementation work ("I fixed the bug" → run the failing scenario, show it passes)
- Tests ("tests pass" → run them now, show the count)
- Refactors ("behavior preserved" → run the test suite now)
- Infrastructure ("migration applied" → check the schema)
- Dependencies ("installed successfully" → show exit code 0 and the package actually importable)

If the verification is expensive (long test suite, slow build) and you already ran it recently with no intervening changes — say so explicitly: "Tests last ran successfully at [point in conversation]; no code changed since then; I am not re-running." That is an honest exception. Silently skipping verification is not.

If the verification reveals failure — report the failure, do not paper over it with another attempt disguised as a claim.

## Tool Hygiene

**Никогда не используй `sed`, `cat`, `head`, `tail`, `awk`, `echo` через Bash для работы с файлами.** В моей конфигурации каждый такой вызов провоцирует permission prompt, что замедляет работу и раздражает.

- Чтение файлов (включая фрагменты) — `Read` с параметрами `offset`/`limit`. НЕ `sed -n 'N,Mp'`, `head -N`, `tail -N`, `cat`.
- Изменение файлов — `Edit`/`Write`. НЕ `sed -i`, НЕ `echo > file`, НЕ `cat <<EOF > file`.
- Вывод текста пользователю — прямой текст в ответе. НЕ `echo`/`printf` через Bash.

Bash оставь для того, что `Read`/`Edit`/`Write` не умеют:
- Запуск процессов (`python`, `npm`, `docker`, `uvicorn`, тесты)
- Git (`git status`, `git diff`, `git log`, `git commit`)
- Поиск по дереву (`grep -rn`, `find`) — но не для чтения найденных файлов, только для поиска
- Листинг директорий (`ls`) когда структура неизвестна

Правило простое: если есть специализированный tool — используй его. Bash — последнее средство.

## Long-running sub-agents — всегда в background

**Любой sub-agent, который может работать дольше ~30 секунд — запускай с `run_in_background: true`.** Это правило, а не совет.

- **Обязательно в background**: `code-reviewer`, `test-writer`, `document-agent`, `Explore` (thorough), `Plan`, `debugger`, `general-purpose` для многошаговых задач. Pre-merge триада (reviewer + test-writer + document-agent) — **всегда** три параллельных background-агента в одном сообщении.
- **Можно в foreground**: короткие целевые запросы (Explore quick, targeted grep через general-purpose) где результат нужен для следующего шага *немедленно*.

Почему это базовое правило:
1. Агент работает в изолированном контексте — он ничего не ждёт от main-сессии.
2. Foreground-агент блокирует main-сессию целиком на 5-15 минут. Пользователь не может перебить без cancel'а всего вызова. Контекст расходуется на ожидание.
3. Background освобождает main-сессию для параллельной работы + runtime присылает уведомление о завершении. Не нужно sleep/poll.

Если не уверен — в background. Цена ошибки в обратную сторону (запустил в background задачу, которая нужна немедленно) минимальна: просто ждёшь notification. Цена foreground на долгой задаче — потерянные минуты времени пользователя.

## Task Workflow

See [rules/workflow.md](rules/workflow.md).

## Sub-agent Invocation Policy

Sub-agents are a core part of how work gets done here, not a fallback. Use them fully. Each agent runs in an isolated fresh context — they do not bloat the main session; they offload work from it. The main session stays focused on the task at hand; specialized work happens in agents and returns as a summary.

The unit of review is the **branch** (PR), not the individual commit. Reviewing a half-finished feature or writing tests on code that will change in the next commit produces noise, not signal.

### Pre-merge triad (test-writer + code-reviewer + document-agent)

**Trigger — signal from the user**, not auto-detection. Claude Code cannot distinguish "branch still being worked on" from "branch ready to merge" — they are the same git state. The triad runs when the user signals readiness:

- Explicit: "готовлю к мержу", "прогони проверки", "ready to merge", "run pre-merge checks"
- Implicit: the user asks for one of the triad agents but not the others — in that case, ask whether to run all three together
- The user calls `/merge-pr` without running checks first — pause and confirm whether to run the triad before merging

The triad:

1. **`test-writer`** — generate and verify tests for new/changed public surfaces on this branch
2. **`code-reviewer`** — security, quality, ADR compliance, regression check against follow-up issues
3. **`document-agent`** — if the branch introduced architectural decisions, new routes/schemas, dependency changes, or otherwise affects documented areas

**Run them in parallel, not sequentially.** They operate on read-only or disjoint write targets:
- `code-reviewer` is read-only (no Write/Edit tools)
- `test-writer` writes only to test files (`*_test.go`, `test_*.py`, `*.test.tsx`) — never touches source
- `document-agent` writes only under `docs/` — never touches source or tests

No file conflicts between them. Parallel execution cuts the triad from ~10–15 minutes sequentially to ~5 minutes (bounded by the slowest agent, usually code-reviewer).

**Expected output after the triad:**

- `code-reviewer` report (APPROVED or BLOCKED + findings)
- New test files from `test-writer` as unstaged changes in the working tree
- Updated docs/ADRs from `document-agent` as unstaged changes

The user decides how to commit the tests and docs (separate `test:` / `docs:` commits, amend, or discard). Agents produce work; the user decides what to ship.

### Post-merge `document-agent`

If the triad was skipped before merge and the branch introduced structural changes (routes, DB schema, models, dependencies, architectural decisions), run `document-agent` after the merge to sync docs. This is the fallback, not the primary path — prefer running `document-agent` in the pre-merge triad when possible.

### `debugger` — situational, not lifecycle

Bugs do not care about branch state. Invoke `debugger` on-demand when investigation stalls. Trigger criteria:

- Your first fix attempt failed. A second attempt on the same bug is the trigger — do not guess a third time, hand it off
- You cannot state the root cause in one mechanistic sentence (file:line + mechanism + condition). If your best answer contains "probably", "maybe", "something with" — you do not have a root cause
- Symptom surfaces in module A but the apparent cause is in module B (non-local debugging)
- The bug is intermittent, timing-dependent, or environment-dependent (flaky tests, race conditions, works-on-my-machine)
- The bug contradicts your model of the code ("this should not be possible")
- Regression after a merge/dependency bump, and `git bisect` is not obvious
- The user explicitly says the bug is hard or has already tried fixing themselves

Do NOT invoke `debugger` for: compilation errors, type errors, missing imports, typos visible in the snippet, requirements disputes, or bugs where you already have a one-sentence mechanistic root cause. For those, fix directly.

Calibration signals (weak alone, two or more = trigger): several back-and-forth exchanges without convergence, same file read more than three times, explanations getting longer not shorter, "let me try X" without being able to predict the outcome.

What to pass to `debugger`: exact error, reproduction steps tried (with outcomes), fixes already attempted (with outcomes), relevant file paths. Do NOT pass your hypotheses — the agent is deliberately isolating from your theory.

### Mid-branch explicit invocations

Agents can be invoked mid-branch if the user asks, or before a large internal refactor that benefits from a sanity check. These are manual, not policy-driven. Do not auto-invoke agents on every intermediate commit — that is the anti-pattern this policy exists to prevent.

### Atomicity of commands

Commands (`/commit-push`, `/merge-pr`, others) are atomic — they do exactly what their name says and nothing more. They do NOT invoke review, test, or documentation agents. All quality gates are explicit steps that the user or the main session runs before calling the command. This keeps commands predictable and keeps the user in control of when review happens.

## Git & Workflow

- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Одна ветка на фичу: `feature/short-name` или `fix/short-name`
- Squash merge в main через PR
- Не пушь секреты. Используй `.env` + `.env.example`
- **НИКОГДА не делай `git commit`, `git push` или `docker push` без явной просьбы пользователя.** Реализация задачи не подразумевает автоматический коммит или публикацию. Docker-образы можно собирать локально (`docker build`), но пушить в реестр — только по явной команде.

## Stack Preferences

- **Python 3.12**, conda для envs (`environment.yml`)
- **FastAPI** + `uvicorn` (async, lifespan context manager)
- **Go** для перформанс-критичных сервисов
- **React** + **TypeScript** для фронтенда
- **PostgreSQL** + `asyncpg` + **SQLAlchemy 2.x** async (Python) / `pgx` (Go)
- **Alembic** для миграций (Python), `golang-migrate` (Go)
- **pandas** для data processing
- **Docker Compose** для инфраструктуры