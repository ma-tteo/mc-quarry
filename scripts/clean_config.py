import json
import os
import shutil
from pathlib import Path

def sanitize_config(input_file="config.json", output_file="config_clean.json"):
    if not os.path.exists(input_file):
        print(f"Errore: Il file {input_file} non esiste.")
        return

    # Chiavi da rimuovere o resettare
    keys_to_remove = [
        "curseforge_api_key",
        "language",
        "mods_folder",
        "resourcepacks_folder"
    ]

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Rimuoviamo le chiavi sensibili
        for key in keys_to_remove:
            if key in config:
                print(f"Rimosso: {key}")
                del config[key]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        print(f"\n✅ Configurazione pulita salvata in: {output_file}")
        print("Questo file è sicuro per essere caricato su GitHub.")

    except Exception as e:
        print(f"Errore durante la pulizia: {e}")

if __name__ == "__main__":
    sanitize_config()
