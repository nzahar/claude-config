## Security Defaults

- Секреты — через env vars, никогда хардкод. `os.environ["KEY"]` / `os.Getenv("KEY")`
- UUID / ID path params — всегда валидируй, возвращай 400
- File uploads — всегда лимит на размер
- Не возвращай internal paths (filesystem, output_path) в API responses
- SQL — параметризованные запросы, даже если query содержит только hardcoded колонки
