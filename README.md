# 🚀 MC Quarry

**Modrinth Modpack Downloader** — Automatizza il download e la gestione di mod e texture pack per Minecraft (Fabric) da Modrinth.

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Modrinth](https://img.shields.io/badge/Source-Modrinth-1bd96a?logo=modrinth)](https://modrinth.com/)

---

## ✨ Funzionalità

| Feature | Descrizione |
|---------|-------------|
| 🔄 **Download Automatico** | Scarica l'ultima versione compatibile per la tua versione di Minecraft |
| ⚡ **Download Parallelo** | Multithreading per ridurre drasticamente i tempi di attesa |
| 📦 **Gestione Aggiornamenti** | Aggiorna solo le mod con nuove versioni, rimuovendo i vecchi file |
| 🎛️ **Configurazione Flessibile** | Gestisci mod, texture pack e percorsi tramite `config.json` |
| 🌍 **Multilingua** | Italiano, Inglese, Spagnolo, Francese |
| 📂 **Installazione Diretta** | Copia automatica nella cartella della tua istanza (PrismLauncher, MultiMC, vanilla) |
| 📊 **Metadati Locali** | File `.modinfo` per tracciare le versioni installate |

---

## 📋 Requisiti

- **Python 3.x**
- **requests** (`pip install requests` o `sudo dnf install python3-requests` su Fedora/Nobara)

---

## 🚀 Utilizzo

### Modalità Interattiva
```bash
python3 main.py
```
Lo script ti guiderà passo dopo passo:
1. Scelta della lingua (se non configurata)
2. Versione di Minecraft (es. `1.21.1`)
3. Download mod "Survival QoL" (opzionale)
4. Copia delle mod nella cartella di gioco
5. Download texture pack (opzionale)

### Modalità CLI (Non-Interattiva)
```bash
python3 main.py --version 1.21.1 --yes
```

| Flag | Descrizione |
|------|-------------|
| `--version` | Versione di Minecraft (obbligatorio) |
| `--yes`, `-y` | Risponde "Sì" a tutte le conferme |
| `--lang` | Forza una lingua: `en`, `it`, `es`, `fr` |
| `--threads` | Numero di thread per il download (default: 5) |

---

## ⚙️ Configurazione (`config.json`)

```json
{
    "language": "it",
    "mods_folder": "/percorso/della/tua/istanza/mods",
    "resourcepacks_folder": "/percorso/della/tua/istanza/resourcepacks",
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

| Campo | Descrizione |
|-------|-------------|
| `mods` | Lista principale (ottimizzazione e base) |
| `survival_qol_mods` | Mod di gameplay/estetica (opzionali) |
| `texture_packs` | Lista dei resource pack |
| `mods_folder` | Percorso destinazione mod (supporta `<INSTANCE_NAME>`) |
| `resourcepacks_folder` | Percorso destinazione texture pack |

---

## 📂 Struttura Cartelle

```
mc-quarry/
├── main.py                 # Script principale
├── config.json             # Configurazione utente (ignorato da git)
├── config_clean.json       # Configurazione di esempio
├── requirements.txt        # Dipendenze Python
├── MODS_INFO.md            # Documentazione dettagliata mod
├── mc-quarry.log           # Log delle operazioni
├── mc_quarry/              # Modulo Python
│   ├── __init__.py
│   ├── api_client.py       # Client API Modrinth
│   ├── config_manager.py   # Gestione configurazione
│   ├── downloader.py       # Logica di download
│   ├── ui_manager.py       # Interfaccia e traduzioni
│   └── utils.py            # Utility varie
└── modpack/                # Download locali
    ├── mods 1.21.1/
    ├── mods_qol 1.21.1/
    └── texture_packs 1.21.1/
```

---

## 📄 Documentazione

- **[MODS_INFO.md](MODS_INFO.md)** — Descrizione dettagliata di tutte le mod incluse

---

## 🛠️ Sviluppo

```bash
# Clona la repository
git clone https://github.com/ma-tteo/mc-quarry.git
cd mc-quarry

# Installa dipendenze
pip install -r requirements.txt

# Esegui
python3 main.py
```

---

## 📝 License

MIT License — vedi file [LICENSE](LICENSE) per dettagli.

---

## 🤝 Contributing

1. Fork la repository
2. Crea un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. Commit delle modifiche (`git commit -m 'Add AmazingFeature'`)
4. Push sul branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

---

**Made with ❤️ by Matto244**
