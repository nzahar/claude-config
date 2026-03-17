# Global CLAUDE.md

## Language & Communication

- Отвечай на русском если я пишу на русском, на английском если на английском
- Код, коммиты, PR, комментарии в коде — всегда на английском
- Будь кратким. Не повторяй то, что я уже вижу в диффе

## Git & Workflow

- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Одна ветка на фичу: `feature/short-name` или `fix/short-name`
- Squash merge в main через PR
- Не пушь секреты. Используй `.env` + `.env.example`

## Stack Preferences

- **Python 3.12**, conda для envs (`environment.yml`)
- **FastAPI** + `uvicorn` (async, lifespan context manager)
- **Go** для перформанс-критичных сервисов
- **React** + **TypeScript** для фронтенда
- **PostgreSQL** + `asyncpg` + **SQLAlchemy 2.x** async (Python) / `pgx` (Go)
- **Alembic** для миграций (Python), `golang-migrate` (Go)
- **pandas** для data processing
- **Docker Compose** для инфраструктуры