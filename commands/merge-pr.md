Найди PR с номером $ARGUMENTS через gh cli.

1. Проверь статус PR: `gh pr view $ARGUMENTS --json state,mergeable,statusCheckRollup`
   - Если PR не MERGEABLE (конфликты) — останови и покажи причину
   - Если checks failed — предупреди и спроси продолжать ли
2. Смержи: `gh pr merge $ARGUMENTS --squash --delete-branch`
3. Переключись на main: `git checkout main`
4. Подтяни изменения: `git pull`
5. Почисти remote refs: `git fetch --prune`
6. Удали локальную ветку если осталась: `git branch -d <branch> 2>/dev/null` (тихо, без ошибки если нет)
7. Если в репо есть `docs/STATE.md` — впиши в самое начало секции `## Current` строку-маркер о только что сделанном мерже. **Без вызова `document-agent`** — это дешёвый append, не полная Phase 3. Используй `Edit` tool, не shell. Формат строки:

   ```
   > ✅ **Merged <YYYY-MM-DD>:** `<short-hash>` — <commit-subject> (PR #<N>)
   ```

   Где `<short-hash>` берётся из `git log -1 --format=%h` (на main, после `git pull`), `<commit-subject>` из `git log -1 --format=%s`, `<N>` — номер PR из аргумента команды. Маркер вставляется **сразу под** заголовком `## Current`, перед остальным контентом секции. Если уже есть предыдущий маркер от прошлого мержа — сдвинь его вниз (оставь, document-agent при следующем `--state-only` подметёт). Если STATE.md нет — пропусти этот шаг тихо.

   Цель: STATE.md, закоммиченный в pre-merge триаде, описывает «pre-merge in flight»; после мержа эта строчка-маркер делает Current честным до следующего полноценного state-refresh, без агентного вызова.
