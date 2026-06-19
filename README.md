# MC Quarry

```
    __  _________     ____                             
   /  |/  / ____/    / __ \__  ______ _____________  __
  / /|_/ / /  ______/ / / / / / / __ `/ ___/ ___/ / / /
 / /  / / /__/_____/ /_/ / /_/ / /_/ / /  / /  / /_/ / 
/_/  /_/\____/     \___\_\__,_/\__,_/_/  /_/   \__, /  
                                               /____/   
```

**Modrinth & CurseForge Modpack Downloader** — Automate downloading and managing Minecraft (Fabric) mods and texture packs with advanced filtering and hardware detection.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPL--3.0_only-green.svg)](LICENSE)
[![Modrinth](https://img.shields.io/badge/Source-Modrinth-1bd96a?logo=modrinth)](https://modrinth.com/)
[![CurseForge](https://img.shields.io/badge/Source-CurseForge-f16436?logo=curseforge)](https://curseforge.com/)

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Automatic Sync** | Downloads the latest compatible version for your specific MC version. |
| **Parallel Engine** | Multi-threaded thread-safe downloads drastically reduce wait times. |
| **Hardware Aware** | Automatically skips mods like *Nvidium* (if not NVIDIA) or *C2ME* (if low CPU cores). |
| **Config Safety** | Critical protection against corrupted JSON files; automatic backups created. |
| **Security First** | Protects against Path Traversal vulnerabilities during file copies. |
| **Update Logic** | Removes old JARs and keeps metadata in `.modinfo` files. |
| **Smart Folders** | Supports PrismLauncher, MultiMC, and Vanilla with `<INSTANCE_NAME>` detection. |
| **Web UI** | Real-time progress via Flask + SocketIO web interface. |

---

## Usage

### CLI
```bash
python3 main.py [--version 1.21.1] [--yes] [--threads 5]
```

| Flag | Description |
|------|-------------|
| `--version` | Target Minecraft version (required for batch mode). |
| `--yes`, `-y` | Auto-accept all prompts. |
| `--verbose`, `-v` | Show detailed logs. |
| `--threads` | Parallel download threads (default: 5). |

### Web UI
```bash
python3 web_interface.py [--host 127.0.0.1] [--port 5000]
```

Opens a browser interface at `http://127.0.0.1:5000` with real-time progress via WebSocket.

---

## Configuration (`config.json`)

A `config.json` file (gitignored) defines mods, texture packs, and hardware rules:

```json
{
    "language": "it",
    "curseforge_api_key": "your-key",
    "mods_folder": "/path/to/mods",
    "install_light_qol": true,
    "core_mods": [ "Sodium", "Lithium" ],
    "utility_mods": [],
    "curseforge_mods": [ "Connectivity" ],
    "light_qol_mods": [ "BetterF3" ],
    "texture_packs": [ "Fresh Animations" ],
    "curseforge_texture_packs": [],
    "requirements": {
        "Nvidium": { "gpu": "nvidia" },
        "Concurrent Chunk Management Engine (Fabric)": { "min_cpu_cores": 8 }
    },
    "incompatible_mods": {},
    "conflicts": {}
}
```

A `config_clean.json` template is available in the repository as a safe sharing reference (no API keys or local paths).

### Mod Categories

| Category | Provider | Type |
|----------|----------|------|
| `core_mods` | Modrinth | mod |
| `utility_mods` | Modrinth | mod |
| `light_qol_mods` | Modrinth | mod |
| `curseforge_mods` | CurseForge | mod |
| `texture_packs` | Modrinth | resourcepack |
| `curseforge_texture_packs` | CurseForge | resourcepack |

---

## Installation

```sh
pip install -e ".[test]"    # install with test deps
ruff check mc_quarry/ tests/  # lint (no violations expected)
pytest tests/ -v           # 219 tests
```

---

## Architecture

| Module | Role |
|---|---|
| `main.py` | CLI entrypoint — parses args, loads config, dispatches categories |
| `web_interface.py` | Flask + SocketIO web UI entrypoint |
| `mc_quarry/constants.py` | Shared category definitions (single source of truth) |
| `mc_quarry/exceptions.py` | Custom exceptions (`ConfigError`) |
| `mc_quarry/api_client.py` | HTTP client for Modrinth & CurseForge APIs (retry, caching) |
| `mc_quarry/config_manager.py` | JSON config load/save with corruption backup |
| `mc_quarry/downloader.py` | `execute_download`, `filter_mods`, `read_all_mod_info`, `compare_versions` |
| `mc_quarry/processor.py` | `_process_mod_wrapper` — dispatches to Modrinth / CurseForge handlers |
| `mc_quarry/ui_manager.py` | TerminalUI with progress bars, hardware detection |
| `mc_quarry/translations.py` | i18n (en/it) |
| `mc_quarry/utils.py` | `BColors`, `DownloadStats`, `BOX_WIDTH`, `sanitize_filename` |

---

## Changelog

### v6.0.0+

- **Security**: CORS restricted to localhost origins only
- **Security**: `sys.exit()` removed from library code — `ConfigError` exception used instead
- **Security**: Broad `except Exception` handlers tightened to specific exception types
- **Refactor**: Category definitions consolidated into `mc_quarry/constants.py` (single source of truth, no more DRY violations across 3 files)
- **Refactor**: Dead `__getattr__` forwarder removed from `ui_manager.py`
- **Fix**: Web UI `_reset_state()` now mutates dict in-place (eliminates race condition)
- **Fix**: `.gitignore` no longer lists tracked files
- **Fix**: License metadata matches LICENSE file (GPL-3.0-only)
- **Tests**: 219 tests, all passing

---

## Platform Compatibility

Tested on **Windows**, **macOS**, and **Linux** (Ubuntu, Fedora, Arch, Void).

---

## Documentation

- **[MODS_INFO.md](MODS_INFO.md)** — Detailed descriptions of every mod in the pack.
- **[AGENTS.md](AGENTS.md)** — Developer guide with entrypoints, commands, and gotchas.

---

**Made with ❤️ by Matto244** — Licensed under GNU GPL v3.
