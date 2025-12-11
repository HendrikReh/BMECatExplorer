# Repository Guidelines

## Project Structure & Modules
- `main.py`: BMECat→JSONL streaming converter; keep iterparse cleanup.
- `src/config.py`: Env-driven settings; defaults match `docker-compose.yml`.
- `src/db`: SQLAlchemy models, async DB setup, JSONL importer.
- `src/search`: OpenSearch mapping/client/indexer (embeddings supported).
- `src/api`: FastAPI app, routes, schemas; API docs exposed at `/docs`.
- `data/`: Sample catalogs and generated JSONL; avoid committing large new fixtures.
- `tests/`: `unit/`, `integration/`, `smoke/` suites with pytest markers.

## Build, Test, and Development Commands
- `uv sync`: Install dependencies.
- `just up` / `just down`: Start/stop PostgreSQL + OpenSearch via Docker.
- `just convert data/input.xml data/output.jsonl`: Run the XML → JSONL converter.
- `just import data/products.jsonl`: Load JSONL into PostgreSQL.
- `just index` / `just index-embed`: Sync DB rows to OpenSearch (embeddings require `OPENAI_API_KEY`).
- `just serve`: Start FastAPI dev server on `:9019`.
- `just lint`: Ruff lint pass.
- `just format`: Black formatting pass.
- `just test-unit|test-integration|test-smoke|test`: Run targeted or full pytest suites.
- `just pipeline <xml>`: Convert → import → index in one step.

## Coding Style & Naming Conventions
- Python 3.12; 4-space indent; prefer type hints and concise docstrings (mirror existing modules).
- Keep state in config only.
- File/module names use `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE`.
- Preserve the streaming parse pattern in `main.py` (iterparse + `clear()`) to stay memory-light.

## Linting & Formatting
- Ruff + Black installed; follow PEP 8/Black (88 col); group imports stdlib/third-party/local.
- Run `just lint` (ruff) and `just format` (black) before PRs; `uv run ruff check .` / `uv run black .` also work.

## Testing Guidelines
- Use pytest; mark tests with `unit|integration|smoke` for filtering.
- Name test files `test_<feature>.py` and functions `test_<behavior>`.
- For integration/smoke, `just up` provisions services; clean up test data.
- Cover parsing/DB/query edge cases before new endpoints.

## Commit & Pull Request Guidelines
- Commit messages: short, imperative (e.g., "Add price range filter validation"); one logical change per commit.
- PRs: describe motivation and approach; list `just test-*` commands executed; link issues; add API examples or response snippets when behavior changes.
- Update README/docs when altering workflows, env vars, or `justfile` recipes.

## Security & Configuration Tips
- Keep secrets in environment variables or `.env` (already gitignored); never commit keys (e.g., `OPENAI_API_KEY`, DB passwords).
- Defaults in `docker-compose.yml`/`src/config.py` suit local use only; harden credentials and enable SSL for production OpenSearch/PostgreSQL.
