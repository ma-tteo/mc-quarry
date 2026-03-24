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

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPL--3.0-green.svg)](LICENSE)
[![Modrinth](https://img.shields.io/badge/Source-Modrinth-1bd96a?logo=modrinth)](https://modrinth.com/)
[![CurseForge](https://img.shields.io/badge/Source-CurseForge-f16436?logo=curseforge)](https://curseforge.com/)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Automatic Sync** | Downloads the latest compatible version for your specific MC version. |
| ⚡ **Parallel Engine** | Multi-threaded downloads drastically reduce wait times. |
| 💻 **Hardware Aware** | Automatically skips mods like *Nvidium* (if not NVIDIA) or *C2ME* (if low CPU cores). |
| 🛡️ **Config Safety** | Critical protection against corrupted JSON files; automatic backups created. |
| 🧹 **Duplicate Check** | Interactive startup check to remove the same mod from multiple categories. |
| 📦 **Update Logic** | Intelligently removes old JARs and keeps metadata in `.modinfo` files. |
| 📂 **Smart Folders** | Supports PrismLauncher, MultiMC, and Vanilla with `<INSTANCE_NAME>` detection. |

---

## 📋 Requirements

- **Python 3.x**
- **Dependencies**: `requests`, `packaging` (`pip install -r requirements.txt`)

---

## 🚀 Usage

### Standard Run
```bash
python3 main.py
```
The script will guide you through:
1. **Duplicate Cleanup**: Ensuring your `config.json` is clean.
2. **Version Selection**: Choosing your target Minecraft version (e.g., `1.21.1`).
3. **Category Choice**: Choosing which QoL levels to install (Light, Medium, Survival).
4. **Direct Installation**: Copying files directly to your Minecraft instance.

### CLI / Batch Mode
```bash
python3 main.py --version 1.21.11 --yes --threads 8
```

| Flag | Description |
|------|-------------|
| `--version` | Target Minecraft version (required for batch mode). |
| `--yes`, `-y` | Auto-accept all prompts (best for scripts). |
| `--verbose`, `-v` | Show detailed logs (updates, skipped, and "not found" details). |
| `--threads` | Parallel download threads (default: 5). |

---

## ⚙️ Configuration (`config.json`)

The configuration is now organized logically for better management:

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

---

## 🛠️ Utility Scripts

Located in the `scripts/` folder:
- `check_duplicates.py`: Manual check for redundant mods.
- `clean_config.py`: Generates a clean `config_clean.json` without private data.
- `test_connection.py`: Validates API access to Modrinth/CurseForge.
- `test_hardware.py`: Shows what the script "sees" regarding your GPU/CPU.

---

## 💻 Platform Compatibility

Tested and supported on **Windows**, **macOS**, and **Linux** (Ubuntu, Fedora, Arch, Void).

---

## 📄 Documentation

- **[MODS_INFO.md](MODS_INFO.md)** — Detailed descriptions of every mod in the pack.

---

**Made with ❤️ by Matto244**
