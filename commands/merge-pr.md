Найди PR с номером $ARGUMENTS и смержи его.

**Mode detection.** В начале определи режим по URL `origin`:

```bash
git remote get-url origin | grep -qE '127\.0\.0\.1|local_proxy' && echo cloud || echo local
```

Если `cloud` — мерж и проверки идут через GitHub MCP, локальный `git push --delete` запрещён прокси. Если `local` — `gh` cli работает напрямую. Шаги, общие для обоих режимов, идут без префикса; различающиеся помечены **Local:** / **Cloud:**. Имена `owner` и `repo` для MCP-вызовов извлеки из `git remote get-url origin` (последние два сегмента пути без `.git`); если URL — прокси и не парсится, попроси у меня.

1. Проверь статус PR.
   - **Local:** `gh pr view $ARGUMENTS --json state,mergeable,statusCheckRollup`.
   - **Cloud:** `mcp__github__pull_request_read` (через ToolSearch посмотри схему — обычно поле `method` принимает значения вроде `get` / `get_status` / `get_files`; нужны и общий статус PR, и состояние checks). Если в одном вызове и того и другого нет — сделай два.
   - В обоих режимах: если PR не MERGEABLE (конфликты) — останови и покажи причину; если checks failed — предупреди и спроси продолжать ли.
2. Смержи squash + delete branch.
   - **Local:** `gh pr merge $ARGUMENTS --squash --delete-branch`.
   - **Cloud:** `mcp__github__merge_pull_request` с `mergeMethod: "squash"`, `deleteBranch: true`, `pullNumber: $ARGUMENTS`, `owner`, `repo`.
3. Переключись на main.
   - **Local:** `git checkout main`.
   - **Cloud:** `git fetch origin main && (git checkout main 2>/dev/null || git switch -c main origin/main)`. Локальной ветки `main` в свежей сессии может не быть — отсюда fallback через `switch -c`.
4. Подтяни изменения: `git pull origin main` (read-only через прокси, в облаке тоже разрешён).
5. Почисти remote refs.
   - **Local:** `git fetch --prune`.
   - **Cloud:** пропусти — удалением remote-ветки уже занялся MCP-merge с `deleteBranch: true`, локальный `git push --delete` запрещён прокси.
6. Удали локальную feature-ветку если осталась.
   - **Local:** `git branch -d <branch> 2>/dev/null` (тихо, без ошибки если нет).
   - **Cloud:** пропусти — runtime пересоздаёт сессию с новой `claude/<slug>-<hash>`, локальная feature-ветка не нужна.
7. Если в репо есть `docs/STATE.md` — впиши в самое начало секции `## Current` строку-маркер о только что сделанном мерже. **Без вызова `document-agent`** — это дешёвый append, не полная Phase 3. Используй `Edit` tool, не shell. Формат строки:

   ```
   > ✅ **Merged <YYYY-MM-DD>:** `<short-hash>` — <commit-subject> (PR #<N>)
   ```

   Где `<short-hash>` берётся из `git log -1 --format=%h` (на main, после `git pull`), `<commit-subject>` из `git log -1 --format=%s`, `<N>` — номер PR из аргумента команды. Маркер вставляется **сразу под** заголовком `## Current`, перед остальным контентом секции. Если уже есть предыдущий маркер от прошлого мержа — сдвинь его вниз (оставь, document-agent при следующем `--state-only` подметёт). Если STATE.md нет — пропусти этот шаг тихо.

   Цель: STATE.md, закоммиченный в pre-merge триаде, описывает «pre-merge in flight»; после мержа эта строчка-маркер делает Current честным до следующего полноценного state-refresh, без агентного вызова.
