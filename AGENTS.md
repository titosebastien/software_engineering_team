# Repository Guidelines

## Project Structure & Module Organization
This repo is a Python-based multi-agent system. Core logic lives in `agents/`, `core/`, `communication/`, `memory/`, and `llm/`. Prompts are in `prompts/`, while generated outputs go to `artifacts/` and `workspace/` (both gitignored). The web dashboard is in `dashboard/`. Future automation modules are stubbed in `gitops/` and `tools/`.

## Build, Test, and Development Commands
- `python -m venv venv` and `source venv/bin/activate`: create/activate the virtual environment.
- `pip install -r requirements.txt`: install runtime dependencies.
- `uvicorn dashboard.app:app --reload`: run the dashboard locally.
- `python main.py`: start the agent system with the default demo.
- `python main.py "Your project idea"`: run a custom prompt end-to-end.
- `pytest tests/`: run the test suite (currently minimal/future-facing).

## Coding Style & Naming Conventions
- Python 3.11+; use 4-space indentation and absolute imports (no relative imports).
- Naming: classes `PascalCase`, modules `snake_case`, constants `UPPER_SNAKE_CASE`, private methods `_leading_underscore`.
- Logging uses `logging.getLogger(__name__)` with `exc_info=True` for errors.

## Testing Guidelines
Tests use `pytest` (see `requirements.txt`). Place new tests under `tests/` and name files `test_*.py`. There is no required coverage target yet; add tests for new agents, workflows, or state transitions when possible.

## Commit & Pull Request Guidelines
Commit messages should be descriptive and can include a short body, for example:
```
Add feature: description

- Detail 1
- Detail 2
```
PRs should include a summary, testing notes (`pytest tests/` or manual run via `python main.py`), and screenshots when changing the dashboard.

## Configuration & Runtime Notes
Adjust runtime settings in `config.py` (LLM models, Ollama host, workflow states). Ensure Ollama is running before executing the system.
