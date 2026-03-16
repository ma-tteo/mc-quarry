# 🚀 Modrinth Modpack Downloader

Un potente script in Python per automatizzare il download, l'aggiornamento e la gestione di mod e texture pack per Minecraft (Fabric) da Modrinth.

## ✨ Funzionalità

*   **Download Automatico**: Scarica l'ultima versione compatibile di ogni mod/resource pack per la versione di Minecraft specificata.
*   **Download Parallelo**: Utilizza il multithreading per scaricare più file contemporaneamente, riducendo drasticamente i tempi di attesa.
*   **Gestione Aggiornamenti**: Controlla le mod già scaricate e aggiorna solo quelle che hanno una nuova versione disponibile, rimuovendo i vecchi file.
*   **Configurazione Flessibile**: Gestisci la lista delle mod, dei texture pack e i percorsi di installazione tramite il file `config.json`.
*   **Supporto Multilingua**: Disponibile in Inglese, Italiano, Spagnolo e Francese.
*   **Installazione Diretta**: Opzione per copiare automaticamente i file scaricati nella cartella delle mod della tua istanza Minecraft (supporta vanilla, PrismLauncher, MultiMC).
*   **Moduli Separati**: Possibilità di scegliere se installare anche un pacchetto di mod "Survival QoL" aggiuntive o i Texture Pack.
*   **Metadati Locali**: Salva file `.modinfo` per tenere traccia delle versioni installate e velocizzare i controlli futuri.

## 📋 Requisiti

*   Python 3.x
*   Libreria `requests`

Installazione della dipendenza:
```bash
pip install requests
# Oppure su Fedora/Nobara:
sudo dnf install python3-requests
```

## 🚀 Utilizzo

Esegui lo script dalla riga di comando:

### Modalità Interattiva
```bash
python3 main.py
```
Lo script ti guiderà passo dopo passo:
1.  Scelta della lingua (se non configurata).
2.  Inserimento della versione di Minecraft (es. `1.21.1`).
3.  Conferma per scaricare le mod "Survival QoL".
4.  Conferma per copiare le mod nella cartella di gioco.
5.  Conferma per scaricare e copiare i Texture Pack.

### Modalità Non-Interattiva (CLI)
Ideale per script di automazione o aggiornamenti rapidi senza domande.
```bash
python3 main.py --version 1.21.1 --yes
```
*   `--version`: Specifica la versione di Minecraft.
*   `--yes` o `-y`: Risponde automaticamente "Sì" a tutte le conferme e usa i percorsi configurati nel `config.json`.
*   `--lang`: (Opzionale) Forza una lingua specifica (en, it, es, fr).
*   `--threads`: (Opzionale) Specifica il numero di thread per il download (default: 5).

## ⚙️ Configurazione (`config.json`)

Il file `config.json` contiene la lista delle mod e le preferenze. Se non esiste, viene creato parzialmente al primo avvio, ma puoi popolarlo manualmente.

Esempio struttura:
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

*   **mods**: Lista principale delle mod (solitamente ottimizzazione e base).
*   **survival_qol_mods**: Lista secondaria per mod di gameplay/estetica (opzionale durante l'esecuzione).
*   **texture_packs**: Lista dei resource pack.
*   **mods_folder** / **resourcepacks_folder**: Percorsi di destinazione per la copia automatica. Supportano il placeholder `<INSTANCE_NAME>` se si usano launcher come PrismLauncher su Linux.

## 📂 Struttura Cartelle

I file vengono scaricati localmente nella cartella del progetto prima di essere (opzionalmente) copiati:

```
/Modpack creator
├── main.py              # Script principale
├── config.json          # Configurazione
├── MODS_INFO.md         # Documentazione dettagliata delle mod incluse
└── modpack/
    ├── mods 1.21.1/     # Mod "Core" scaricate
    ├── mods_qol 1.21.1/ # Mod "QoL" scaricate (opzionali)
    └── ...
```

## ℹ️ Info sulle Mod
Per una descrizione dettagliata di tutte le mod incluse in questo pacchetto, consulta il file [MODS_INFO.md](MODS_INFO.md).
