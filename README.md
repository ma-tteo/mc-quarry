# 🚀 MC Quarry

**Modrinth Modpack Downloader** — Automate downloading and managing Minecraft (Fabric) mods and texture packs from Modrinth.

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPL--3.0-green.svg)](LICENSE)
[![Modrinth](https://img.shields.io/badge/Source-Modrinth-1bd96a?logo=modrinth)](https://modrinth.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](README.md)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Automatic Download** | Downloads the latest compatible version for your Minecraft version |
| ⚡ **Parallel Download** | Multi-threading to drastically reduce wait times |
| 📦 **Update Management** | Updates only mods with new versions, removing old files |
| 🎛️ **Flexible Configuration** | Manage mods, texture packs, and paths via `config.json` |
| 🌍 **Multi-language** | Italian, English, Spanish, French |
| 📂 **Direct Installation** | Automatic copy to your instance folder (PrismLauncher, MultiMC, vanilla) |
| 📊 **Local Metadata** | `.modinfo` files to track installed versions |
| 💻 **Cross-Platform** | Windows, macOS, Linux (Ubuntu, Fedora, Arch, Gentoo, Void) |

---

## 📋 Requirements

- **Python 3.x**
- **requests** (`pip install requests` or `sudo dnf install python3-requests` on Fedora/Nobara)

---

## 🚀 Usage

### Interactive Mode
```bash
python3 main.py
```
The script will guide you step by step:
1. Language selection (if not configured)
2. Minecraft version (e.g., `1.21.1`)
3. Download "Survival QoL" mods (optional)
4. Copy mods to game folder
5. Download texture packs (optional)

### CLI Mode (Non-Interactive)
```bash
python3 main.py --version 1.21.1 --yes
```

| Flag | Description |
|------|-------------|
| `--version` | Minecraft version (required) |
| `--yes`, `-y` | Answer "Yes" to all confirmations |
| `--lang` | Force a language: `en`, `it`, `es`, `fr` |
| `--threads` | Number of download threads (default: 5) |

---

## ⚙️ Configuration (`config.json`)

```json
{
    "language": "en",
    "curseforge_api_key": "your-api-key-here",
    "mods_folder": "/path/to/your/instance/mods",
    "resourcepacks_folder": "/path/to/your/instance/resourcepacks",
    "mods": [
        "Sodium",
        "Fabric API",
        "Iris Shaders"
    ],
    "survival_qol_mods": [
        "Falling Leaves",
        "Ambient Sounds"
    ],
    "texture_packs": [
        "Fresh Animations"
    ]
}
```

| Field | Description |
|-------|-------------|
| `mods` | Main list (optimization and base mods) |
| `survival_qol_mods` | Gameplay/aesthetic mods (optional) |
| `texture_packs` | List of resource packs |
| `mods_folder` | Destination path for mods (supports `<INSTANCE_NAME>`) |
| `resourcepacks_folder` | Destination path for texture packs |
| `curseforge_api_key` | **Optional**: CurseForge API key (or use `CURSEFORGE_API_KEY` env var) |

### 🔐 Environment Variables

| Variable | Description |
|----------|-------------|
| `CURSEFORGE_API_KEY` | Override CurseForge API key from config (recommended for security) |

---

## 📂 Folder Structure

```
mc-quarry/
├── main.py                 # Main script
├── config.json             # User configuration (git-ignored)
├── config_clean.json       # Example configuration
├── requirements.txt        # Python dependencies
├── MODS_INFO.md            # Detailed mod documentation
├── mc-quarry.log           # Operation logs
├── mc_quarry/              # Python module
│   ├── __init__.py
│   ├── api_client.py       # Modrinth API client
│   ├── config_manager.py   # Configuration management
│   ├── downloader.py       # Download logic
│   ├── ui_manager.py       # UI and translations
│   └── utils.py            # Various utilities
└── modpack/                # Local downloads
    ├── mods 1.21.1/
    ├── mods_qol 1.21.1/
    └── texture_packs 1.21.1/
```

---

## 💻 Platform Compatibility

MC Quarry works on all major operating systems:

| Platform | Supported | Notes |
|----------|-----------|-------|
| **Windows** | ✅ Yes | Tested on Windows 10/11 |
| **macOS** | ✅ Yes | Intel and Apple Silicon |
| **Linux** | ✅ Yes | Ubuntu, Fedora, Arch, Gentoo, Void, and others |

### Linux Distro Support

| Distro | Package Manager | Tested |
|--------|-----------------|--------|
| Ubuntu/Debian | apt | ✅ |
| Fedora/RHEL | dnf | ✅ |
| Arch Linux | pacman | ✅ |
| Gentoo | portage | ✅ |
| Void Linux | xbps | ✅ |

**Requirements:** Python 3.x and `pip install requests packaging`

---

## 📄 Documentation

- **[MODS_INFO.md](MODS_INFO.md)** — Detailed description of all included mods

---

## 🛠️ Development

```bash
# Clone the repository
git clone https://github.com/ma-tteo/mc-quarry.git
cd mc-quarry

# Install dependencies
pip install -r requirements.txt

# Run
python3 main.py
```

---

## 📝 License

GNU General Public License v3.0 — see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

**Made with ❤️ by Matto244**
