# Global CLAUDE.md

## Language & Communication

- Отвечай на русском если я пишу на русском, на английском если на английском
- Код, коммиты, PR, комментарии в коде — всегда на английском
- Будь кратким. Не повторяй то, что я уже вижу в диффе

## Project State Awareness

**At the start of every session in a project, read `docs/STATE.md` if it exists.** This file is maintained by the project's documentation agent (`document-agent` for engineering projects, `experiment-doc-agent` for research projects; project-level `CLAUDE.md` may declare `state_owner` explicitly). It contains the current trajectory of work: what was last shipped, what's blocked, what's planned next — described in terms invariant under merge (PR titles, file-derived statuses), not in terms of branch / working-tree state. Reading it once at session start gives you the orientation a returning collaborator would have.

Rules:

- **Read it before answering the user's first message.** Not lazily on demand — at session start, alongside (or right after) any other project files you check.
- **Read the `## Current` section.** The `## History` section is for deep context on past trajectory; consult it only if the user asks about prior decisions or you need to understand how the project got here.
- **If the file does not exist, do nothing.** Do not ask the user to create it, do not offer to create it. Some projects don't have one yet, that's fine.
- **STATE.md can be stale.** If the user's first message contradicts what STATE.md treats as currently active or planned (e.g. user opens with "let's work on Y" while STATE.md's `Next up:` says Z) — trust the user. STATE.md describes the project's snapshot at the last documentation pass; it does not bind the user's plans for this session. Note the discrepancy briefly if relevant, do not argue.
- **Never edit STATE.md from the main session.** It is owned by the project's documentation agent (`document-agent` Phase 3 for engineering, `experiment-doc-agent` Phase 4 for research; project-level `CLAUDE.md` may declare `state_owner` explicitly). Editing it from the main session causes conflicts. If you think STATE.md should be updated, suggest invoking the appropriate documentation agent with `--state-only`.
- **Do not surface STATE.md content unprompted.** Use it for your own orientation. The user does not need a recap of their own project unless they ask for one.

Аналогично — при работе вне workflow.md (debugging-сессии, ad-hoc вопросы, refactoring без формального плана) читай `docs/CODEMAPS/<area>.md` и релевантные ADR из `docs/ADR/`, если работа касается архитектурных решений или зафиксированных инвариантов. Для тривиальных правок (typo, форматирование, локальный bugfix) это не нужно.

## Verification Before Claims

**No completion claim without fresh verification evidence in the current message.**

If you are about to say that tests pass, lint passes, the fix works, the migration ran, the build succeeded, the dependency is installed, the endpoint returns 200, the data loaded, the refactor is equivalent, or anything else of that shape — run the command that proves it *in this message* and include the output (or a concise summary of it).

Evidence from earlier in the session does not count. Output from a previous attempt does not count. "Should work" does not count. Type-check passing is not a substitute for tests passing. Building is not a substitute for running. Running is not a substitute for checking exit code.

If you catch yourself about to write any of these phrases — stop and verify first:
- "should work" / "должно работать"
- "скорее всего работает" / "probably works"
- "теперь должно" / "now it should"
- "по идее" / "in theory"
- "fix should be sufficient" / "фикс должен закрыть"

These phrases are signals that you are about to claim completion without evidence. Run the verification, paste the output, *then* claim.

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

**Правило по списку агентов, не по таймеру.** Решение foreground/background принимай по конкретному агенту, а не по эвристике "сколько секунд".

- **Обязательно в background**: `code-reviewer`, `test-writer`, `document-agent`, `experiment-doc-agent`, `Explore` (thorough), `Plan`, `debugger`, `general-purpose` для многошаговых задач. Pre-merge триада (reviewer + test-writer + document-agent) — **всегда** три параллельных background-агента в одном сообщении.
- **Можно в foreground**: короткие целевые запросы (Explore quick, targeted grep через general-purpose) где результат нужен для следующего шага *немедленно*. `plan-reviewer` обычно тоже короткий — на усмотрение, но если план большой, запускай в background.

Rule of thumb для агентов вне списка: если ожидаемая работа дольше ~30 секунд — в background.

Почему это базовое правило:
1. Агент работает в изолированном контексте — он ничего не ждёт от main-сессии.
2. Foreground-агент блокирует main-сессию целиком на 5-15 минут. Пользователь не может перебить без cancel'а всего вызова. Контекст расходуется на ожидание.
3. Background освобождает main-сессию для параллельной работы + runtime присылает уведомление о завершении. Не нужно sleep/poll.

Если не уверен — в background. Цена ошибки в обратную сторону (запустил в background задачу, которая нужна немедленно) минимальна: просто ждёшь notification. Цена foreground на долгой задаче — потерянные минуты времени пользователя.

## Task Workflow

See [rules/workflow.md](rules/workflow.md).

## Sub-agent Invocation Policy

Sub-agents run in isolated fresh contexts — they offload work from the main session, not bloat it. The unit of review is the **branch** (PR), not the individual commit. Use them fully; full agent contracts live in `agents/*.md`.

### Agent modes

`plan-reviewer` and `code-reviewer` take `mode: engineering | research` in the invocation prompt. Selection: project's `default_agent_mode` (if declared) → structural inference (active `notebooks/<...>/*.ipynb` without `src/` → research; else engineering) → per-branch override (pass explicitly). If a project declares `default_agent_mode: research` and the call lacks `mode:` with no engineering override, the agent errors out — no silent fallback. Other agents (`document-agent`, `experiment-doc-agent`, `test-writer`, `debugger`) have no modes; `experiment-doc-agent` is research-only.

### Project-level `state_owner`

Project's `CLAUDE.md` may declare `state_owner: document-agent | experiment-doc-agent | split`. Default: `document-agent` for engineering (`src/` present, no `notebooks/`), `experiment-doc-agent` for research-only. `split` is for hybrid projects and uses two files: `docs/STATE.md` (engineering, owned by `document-agent`) + `docs/RESEARCH-STATE.md` (research, owned by `experiment-doc-agent`). Never two owners on one file.

### Plan review (`plan-reviewer`)

Trigger — step 4 of `workflow.md`, after the user approves the plan, before any code is written. Mandatory for non-trivial tasks with a plan file at `docs/plans/<branch-slug>.md`. **No loop with the agent** — one report, the user decides what to fix. **Exception** for framework / governance changes (`rules/`, `CLAUDE.md`, `agents/`, ADRs auto-load every session; `commands/` and `skills/*` excluding `learned/` on contract changes only): iterate review→revise until clean (nits OK). See `rules/workflow.md` "Exception to \"no loop\"". The agent finds the plan automatically from the branch — pass an explicit path only if it lives elsewhere. Do not invoke for one-sentence "plans", mid-implementation, or replanning.

### Pre-merge triad (`test-writer` + `code-reviewer` + `document-agent` or `experiment-doc-agent`)

**Scope.** Branch-level gate before merge. Does **not** cover operation-level pre-execution review (`workflow.md` §4.5, auto-detected per-operation). Both gates can fire on the same branch — §4.5 keeps gating operations launched while preparing for merge.

**Trigger — signal from the user**, not auto-detection. Claude Code cannot distinguish "still working" from "ready to merge" — they are the same git state. Triggers: explicit ("ready to merge", "готовлю к мержу", "прогони проверки"), implicit (the user requests one triad agent but not the others — ask whether to run all three), or `/merge-pr` without prior checks (pause, confirm).

Run the three in **parallel** in one message — disjoint write targets (`code-reviewer` read-only, `test-writer` writes only test files, the documentation agent writes only under `docs/`), no conflicts. Choice between `document-agent` and `experiment-doc-agent` governed by `state_owner`. `document-agent` requires a `scope:` parameter in the invocation prompt — main session maps the branch's `git diff` paths to `docs/CODEMAPS/` area names and passes `scope: <area-list>`. If the branch touched many areas or you want a full repo refresh, pass `scope: full` explicitly. Expected output: `code-reviewer` verdict (APPROVED / BLOCKED), new test files unstaged, doc/ADR/STATE.md updates unstaged. The user decides how to commit.

### Post-merge `document-agent`

Fallback if the triad was skipped and the branch introduced structural changes (routes, schema, models, dependencies, architectural decisions). Prefer the triad path. Pass `scope: <area-list>` derived from the merged branch's diff, or `scope: full` for periodic catch-up.

### End-of-session `--state-only`

If a session ends without merge but produced state worth recording (decisions pending, branch active, blockers identified), and the user signals end ("я заканчиваю на сегодня", "stopping for the day", "wrapping up"), invoke the project's documentation agent (`document-agent` or `experiment-doc-agent` per `state_owner`) with `--state-only`. Skip if purely exploratory.

### `debugger` — situational

On-demand when investigation stalls: first fix failed; you can't state the root cause in one mechanistic sentence (`file:line` + mechanism + condition; "probably/maybe" = not a root cause); symptom and cause in different modules; intermittent / timing-dependent; behavior contradicts your model of the code; regression after merge/bump where `git bisect` isn't obvious; user says it's hard. Full exclusion list and root-cause discipline in `agents/debugger.md`.

Calibration signals (weak alone, two or more = trigger): several back-and-forth exchanges without convergence, same file read more than three times, explanations getting longer not shorter, "let me try X" without being able to predict the outcome.

What to pass: exact error, reproduction steps tried (with outcomes), fixes already attempted (with outcomes), relevant file paths. Do NOT pass your hypotheses — the agent isolates from your theory deliberately.

### Mid-branch explicit invocations

Allowed when the user asks, or before a large internal refactor that benefits from a sanity check. Manual, not policy-driven — do not auto-invoke on every intermediate commit.

### Atomicity of commands

Commands (`/commit-push`, `/merge-pr`, others) are atomic — they do exactly what their name says, no more. They do NOT invoke review/test/documentation agents and do NOT edit documentation files (no STATE.md markers, no codemap fixups, no log entries). All quality gates and doc refresh are explicit steps the user or main session runs before/after.

Post-merge STATE.md remains valid: `## Current` is a post-merge snapshot describing last shipped, open questions, and next up — not in-progress git state. Routine merges do not require state refresh.

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

## Library Documentation

Для вопросов про библиотеки/фреймворки/SDK/CLI (синтаксис API, конфигурация, миграции версий, library-specific дебаг) предпочитай **context7 MCP** (`mcp__plugin_context7_context7__resolve-library-id` → `query-docs`) над тренировочными данными и WebSearch. Тренировочный cutoff может не отражать свежие изменения; context7 ходит в актуальные доки. Не использовать для рефакторинга, общих программных концепций или дебага бизнес-логики.
