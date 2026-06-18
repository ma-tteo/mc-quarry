# mc-quarry — AGENTS.md

## Entrypoints

- `python3 main.py [--version 1.21.1] [--yes] [--verbose] [--threads 5]`
- `python3 web_interface.py [--host 0.0.0.0] [--port 5000]` — Flask + SocketIO web UI

## Commands

```sh
pip install -e ".[test]"          # install with dev + test deps
ruff check mc_quarry/ tests/      # lint (no violations expected)
pytest tests/ -v                  # 184 tests
pytest tests/ -v --cov=mc_quarry --cov-report=term-missing  # 93% coverage
pytest tests/test_processor.py -v # single file
```

## Architecture

| Module | Role |
|---|---|
| `main.py` | CLI entrypoint — parses args, loads config, dispatches categories |
| `web_interface.py` | Flask + SocketIO web UI entrypoint |
| `mc_quarry/api_client.py` | HTTP client for Modrinth & CurseForge APIs (retry, caching) |
| `mc_quarry/config_manager.py` | JSON config load/save with corruption backup |
| `mc_quarry/downloader.py` | execute_download, filter_mods, read_all_mod_info, compare_versions |
| `mc_quarry/processor.py` | _process_mod_wrapper — dispatches to _handle_modrinth / _handle_curseforge |
| `mc_quarry/ui_manager.py` | TerminalUI with progress bars, hardware detection |
| `mc_quarry/translations.py` | i18n (en/it) — extracted from ui_manager |
| `mc_quarry/utils.py` | BColors, DownloadStats, BOX_WIDTH, sanitize_filename |

## Gotchas

### Modrinth search API is broken (mid-2026+)
- **`/v2/search` returns 0 hits for all queries.**
- Workaround in `processor.py:_generate_slug_candidates()`: infers slug from mod name, does direct `GET /v2/project/{slug}`.
- Slug inference: lowercase, spaces→hyphens, CamelCase→hyphens, apostrophe/paren stripping, no-hyphens variant, first-word fallback.
- Search kept as fallback (`_handle_modrinth` → `search_modrinth`) in case API recovers.

### Config sections
- `config.json` has **4 mod categories** with different project types:
  - `core_mods` / `utility_mods` / `light_qol_mods` → provider=modrinth, project_type=mod
  - `curseforge_mods` → provider=curseforge (needs CF API key)
  - `texture_packs` / `curseforge_texture_packs` → project_type=resourcepack
- `config.json` is **gitignored**. The file must exist at runtime.
- Incompatible mods are filtered by MC version rules (`incompatible_mods`) + hardware requirements (`requirements` key).
- Duplicate mods between categories are caught by `scripts/check_duplicates.py` on startup.

### Testing
- HTTP mocking via `responses` library (not unittest.mock or pytest-mock for HTTP).
- Conftest fixtures: `stats` (fresh DownloadStats), `temp_dir` (tmpdir), `empty_config`, `sample_config`.
- Tests use `responses.activate` decorator or context manager — unmocked URLs raise ConnectionError.
- No external API calls in tests. Everything is mocked.

### Linting
- ruff target: py38, line-length=100, double quotes.
- Per-file-ignore for E501 in ui_manager.py, translations.py, downloader.py, config_manager.py (intentionally long lines).
- `scripts/*` ignores N806 (snake_case naming in scripts).
- No type checker (basedpyright not installed).

### Threading
- `ThreadPoolExecutor(max_workers=threads)` with `as_completed` for parallel mod downloads.
- `DownloadStats` is thread-safe (internal lock).
- `APIClient._version_cache` has `threading.Lock` for thread-safe caching.

### Web UI
- Flask + Flask-SocketIO for real-time progress.
- Templates in `mc_quarry/web/templates/`, static files in `mc_quarry/web/static/`.

### Logging
- Logs go to `mc-quarry.log` **file only** (not console). Console = UI output.
- Logger name: `"mc-quarry"`.

### CurseForge
- API key sourced from `CURSEFORGE_API_KEY` env var (preferred) or `config.json`.
- Without a key, CurseForge mods silently skipped (no download).
