Закоммить изменения, открой PR и сразу его смержи.

**Pre-merge gates check.** Для каждого из трёх gate'ов ответь: (а) применим ли он к диффу ветки? (б) если применим — вернул ли APPROVED на актуальное состояние (не на старый снапшот)?

Критерии применимости:

- **`code-reviewer`** — есть код, конфиг, framework-артефакты (`rules/`, `agents/`, `CLAUDE.md`, `commands/`, `skills/` кроме `learned/`, `docs/ADR/`, `lib/`) — включая правки существующих ADR и `lib/`-документов, а не только новые. **НЕ** применим: микро-правки документации (≲10 строк прозы — эвристика; правки, меняющие контракт или семантику, требуют review независимо от размера), опечатки, переформулировки.
- **`test-writer`** — есть изменения в коде с тестируемой логикой. **НЕ** применим: чистая документация, конфиг без поведенческих эффектов, переименования.
- **`document-agent` / `experiment-doc-agent`** — в репо есть `docs/CODEMAPS/`, `docs/STATE.md` или `experiments/` с REPORT.md. **НЕ** применим: репо без этих артефактов (например, сам framework `~/.claude/`).

Решение:

- Все применимые gate'ы вернули APPROVED → молча переходи к шагу 1.
- Какой-то применимый gate не прошёл или прошёл на устаревший снапшот → остановись, назови пропущенное, предложи запустить, дождись явного "продолжай".
- Ни один критерий применимости и ни один критерий неприменимости явно не подходит для конкретного gate'а → спроси пользователя про этот gate, не обобщай. (Это узкий случай — не дефолт-путь "вообще сомневаюсь".)

**Mode detection.** Определи режим один раз:

```bash
git remote get-url origin | grep -qE '127\.0\.0\.1|localhost|local_proxy' && echo cloud || echo local
```

Дальше шаги общие для обоих режимов; различающиеся помечены **Local:** / **Cloud:**.

**Cloud-quirks для всех MCP-вызовов ниже.** Перед каждым `mcp__github__*` вызовом — `ToolSearch` с указанным `query`. Имена параметров, method/action, enum-значения — строго из реальной схемы, **не угадывай** по названиям из прозы. `owner`/`repo` — последние два сегмента `git remote get-url origin` без `.git`; если URL прокси-формата не парсится — попроси у пользователя.

**Шаги:**

1. Покажи `git status`. Если изменений нет — останови.

2. Проверь среди изменённых файлов наличие секретов (`.env`, `credentials`, `*.pem`, private keys). Есть — останови и предупреди.

3. Подготовь ветку.
   - **Local:** на `main`/`master` создай новую (`feature/<slug>` или `fix/<slug>`); на feature/fix-ветке — коммить в текущую.
   - **Cloud:** новую не создавай — коммитим в текущую `claude/<slug>-<hash>` (прокси разрешает push только в неё; любая другая → 403).

4. Стейдж файлы **явно по именам** (не `git add .` / `-A`). Если файлов больше десяти — спроси, какие коммитить.

5. Коммит conventional message на английском (`feat:` / `fix:` / `refactor:` / `docs:` / `chore:`), затем push.
   - **Local:** `git push -u origin <branch>`.
   - **Cloud:** `git push -u origin HEAD`.

6. Создай PR. Body: **Summary** (буллеты — что), **Motivation** (зачем), **Changed files** (таблица). Запомни номер созданного PR как `<N>`.
   - **Local:** `gh pr create --title ... --body ...` через HEREDOC; `<N>` — последний сегмент URL вывода. Нет `gh` — скажи мне.
   - **Cloud:** `mcp__github__create_pull_request` (query: `select:mcp__github__create_pull_request`). Параметры: `head` = `git rev-parse --abbrev-ref HEAD`, `base` = `main`; `<N>` — поле `number` в ответе.

7. Проверь статус PR.
   - **Local:** `gh pr view <N> --json state,mergeable,statusCheckRollup`.
   - **Cloud:** `mcp__github__pull_request_read` (query: `select:mcp__github__pull_request_read`). Нужны `state`, `mergeable`, состояние checks. Если одним вызовом не получить — сделай два.
   - Не MERGEABLE (конфликты) → останови, покажи причину. Checks failed → предупреди и спроси, продолжать ли.

8. Смержи squash + delete branch.
   - **Local:** `gh pr merge <N> --squash --delete-branch`. **Не добавляй `--repo`** — с явным `--repo` gh уходит в чисто-API режим и пропускает local git-операции (включая удаление local-ветки), оставляя мусор для шага 10.
   - **Cloud:** `mcp__github__merge_pull_request` (query: `select:mcp__github__merge_pull_request`). Параметры: `mergeMethod: "squash"`, `deleteBranch: true`, `pullNumber: <N>`.

9. Переключись на main и подтяни.
   - **Local:** `git checkout main && git pull origin main && git fetch --prune`.
   - **Cloud:** `git fetch origin main && (git checkout main 2>/dev/null || git switch -c main origin/main) && git pull origin main` (без `fetch --prune`: remote-ветку уже удалил MCP-merge, локальный `git push --delete` запрещён прокси).

10. Удали локальную feature-ветку.
    - **Local:** `git branch -d <branch> 2>/dev/null` (тихо, без ошибки если нет). Обычно `gh pr merge --delete-branch` уже удалил local на шаге 8 — этот шаг страхует случай, когда не справился.
    - **Cloud:** пропусти — runtime создаст новую сессионную ветку.

**Recovery после частичного падения.**
- Шаги 1–5 упали → fix причину, перезапусти `/ship` (PR ещё не создан).
- Шаги 6–10 упали → PR уже на remote'е. **Не перезапускай `/ship`** (повторный commit/PR-create приведут к 422 / confusion). Восстановись: `gh pr view <N>` (или MCP-эквивалент) → разрули причину → продолжи с шага 7 или вызови `/merge-pr <N>`.

---

_Канонические одношаговые версии — `commands/commit-push.md` и `commands/merge-pr.md`. При их изменении (новая safety-проверка, изменение MCP-схемы, обновление proxy-правил) проверь, что `/ship` всё ещё корректен._
