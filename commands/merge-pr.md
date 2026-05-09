Найди PR с номером $ARGUMENTS и смержи его.

**Mode detection.** В начале определи режим по URL `origin`:

```bash
git remote get-url origin | grep -qE '127\.0\.0\.1|localhost|local_proxy' && echo cloud || echo local
```

Если `cloud` — мерж и проверки идут через GitHub MCP, локальный `git push --delete` запрещён прокси. Если `local` — `gh` cli работает напрямую. Шаги, общие для обоих режимов, идут без префикса; различающиеся помечены **Local:** / **Cloud:**. Имена `owner` и `repo` для MCP-вызовов извлеки из `git remote get-url origin` (последние два сегмента пути без `.git`); если URL — прокси и не парсится, попроси у меня.

1. Проверь статус PR.
   - **Local:** `gh pr view $ARGUMENTS --json state,mergeable,statusCheckRollup`.
   - **Cloud:** перед первым вызовом получи схему через `ToolSearch` с `query: "select:mcp__github__pull_request_read"` и прочитай реальные имена method/action из схемы. Не угадывай значения по названиям из прозы — если в схеме enum не совпадает с ожиданием, используй то, что в схеме. Нужны и общий статус PR (state, mergeable), и состояние checks. Если одним вызовом не получить — сделай два с разными method-значениями.
   - В обоих режимах: если PR не MERGEABLE (конфликты) — останови и покажи причину; если checks failed — предупреди и спроси продолжать ли.
2. Смержи squash + delete branch.
   - **Local:** `gh pr merge $ARGUMENTS --squash --delete-branch`.
   - **Cloud:** перед вызовом — `ToolSearch` с `query: "select:mcp__github__merge_pull_request"`, прочитай схему. Затем вызови с `mergeMethod: "squash"`, `deleteBranch: true`, `pullNumber: $ARGUMENTS`, `owner`, `repo` (имена параметров — из схемы, если отличаются от перечисленных).
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
