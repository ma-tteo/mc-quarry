# 📂 Cartella Modpack

Questa directory contiene i file scaricati dallo script `main.py`, organizzati per versione di Minecraft e tipo (mods o texture packs).

## ⚠️ Avvertenze

*   **Non modificare manualmente i nomi dei file**: Lo script utilizza i nomi dei file e i file `.modinfo` associati per rilevare le versioni installate e gestire gli aggiornamenti.
*   **File .modinfo**: Questi file contengono metadati essenziali (ID progetto, versione, hash). Se li cancelli, lo script potrebbe riscaricare le mod anche se sono già aggiornate.

## 🗂 Struttura

*   `mods X.Y.Z/`: Contiene i file `.jar` delle mod per la versione Minecraft X.Y.Z.
*   `texture_packs X.Y.Z/`: Contiene i file `.zip` dei Resource Pack per la versione Minecraft X.Y.Z.
