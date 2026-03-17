Собери проект, определив тип по файлам в корне:

1. Определи что за проект:
   - Есть `docker-compose.yml` → Docker-проект
   - Есть `go.mod` (без compose) → Go-проект
   - Есть `package.json` (без compose) → Node/React-проект
   - Комбинация → собери все компоненты

2. Сборка по типу:
   - **Docker**: `docker compose build --no-cache` → `docker compose up -d` → подожди healthcheck → `docker compose ps`
   - **Go**: `go build ./...` → покажи размер бинаря
   - **Node/React**: `npm ci` → `npm run build` → покажи содержимое dist/build
   - **Combo**: собери каждый компонент, потом compose

3. После сборки:
   - Покажи статус (контейнеры / размер артефактов / ошибки)
   - Если есть healthcheck endpoint — дёрни его и покажи ответ
   - Если сборка упала — покажи логи последних 30 строк
