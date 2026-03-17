Найди PR с номером $ARGUMENTS через gh cli.

1. Проверь статус PR: `gh pr view $ARGUMENTS --json state,mergeable,statusCheckRollup`
   - Если PR не MERGEABLE (конфликты) — останови и покажи причину
   - Если checks failed — предупреди и спроси продолжать ли
2. Смержи: `gh pr merge $ARGUMENTS --squash --delete-branch`
3. Переключись на main: `git checkout main`
4. Подтяни изменения: `git pull`
5. Почисти remote refs: `git fetch --prune`
6. Удали локальную ветку если осталась: `git branch -d <branch> 2>/dev/null` (тихо, без ошибки если нет)
