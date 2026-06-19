# 🚀 MC Quarry

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
[![License](https://img.shields.io/badge/License-GPL--3.0-green.svg)](LICENSE)
[![Modrinth](https://img.shields.io/badge/Source-Modrinth-1bd96a?logo=modrinth)](https://modrinth.com/)
[![CurseForge](https://img.shields.io/badge/Source-CurseForge-f16436?logo=curseforge)](https://curseforge.com/)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Automatic Sync** | Downloads the latest compatible version for your specific MC version. |
| ⚡ **Parallel Engine** | Multi-threaded thread-safe downloads drastically reduce wait times. |
| 💻 **Hardware Aware** | Automatically skips mods like *Nvidium* (if not NVIDIA) or *C2ME* (if low CPU cores). |
| 🛡️ **Config Safety** | Critical protection against corrupted JSON files; automatic backups created. |
| 🔒 **Security First** | Protects against Path Traversal vulnerabilities during file copies. |
| 📦 **Update Logic** | Removes old JARs and keeps metadata in `.modinfo` files. |
| 📂 **Smart Folders** | Supports PrismLauncher, MultiMC, and Vanilla with `<INSTANCE_NAME>` detection. |
| 🕸️ **Web UI** | Real-time progress via Flask + SocketIO web interface. |

---

## 🚀 Usage

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
python3 web_interface.py [--host 0.0.0.0] [--port 5000]
```

---

## ⚙️ Configuration (`config.json`)

A `config.json` file (gitignored) defines mods, texture packs, and hardware rules:

```json
{
    "language": "it",
    "curseforge_api_key": "your-key",
    "mods_folder": "/path/to/mods",
    "install_light_qol": true,
    "mods": [ "Sodium", "Lithium" ],
    "curseforge_mods": [ "Connectivity" ],
    "light_qol_mods": [ "BetterF3" ],
    "texture_packs": [ "Fresh Animations" ],
    "requirements": {
        "Nvidium": { "gpu": "nvidia" },
        "Concurrent Chunk Management Engine (Fabric)": { "min_cpu_cores": 8 }
    }
}
```

A `config_clean.json` template is available in the repository as a safe sharing reference (no API keys or local paths).

---

## 💻 Platform Compatibility

Tested on **Windows**, **macOS**, and **Linux** (Ubuntu, Fedora, Arch, Void).

---

## 📄 Documentation

- **[MODS_INFO.md](MODS_INFO.md)** — Detailed descriptions of every mod in the pack.

---

**Made with ❤️ by Matto244**
