## Security Defaults

- Secrets — via env vars, never hardcoded. `os.environ["KEY"]` / `os.Getenv("KEY")`
- UUID / ID path params — always validate, return 400
- File uploads — always enforce a size limit
- Do not return internal paths (filesystem, output_path) in API responses
- SQL — parameterised queries, even if the query contains only hardcoded columns
