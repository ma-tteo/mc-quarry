#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Category definition: (config_key, title)
MOD_CATEGORIES = [
    ("mods", "💎 CORE MODS"),
    ("curseforge_mods", "🔥 CURSEFORGE MODS"),
    ("light_qol_mods", "💡 LIGHT QOL"),
    ("medium_qol_mods", "🎭 MEDIUM QOL"),
    ("survival_qol_mods", "⚔️ SURVIVAL QOL")
]

def check_duplicates():
    config_path = Path("config.json")
    if not config_path.exists():
        print("❌ config.json non trovato.")
        return

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Errore nel caricamento del config: {e}")
        return

    all_mods = {} # mod_name -> list of (category_key, category_title)
    
    for key, title in MOD_CATEGORIES:
        mods = config.get(key, [])
        for m in mods:
            m_low = m.lower().strip()
            if m_low not in all_mods:
                all_mods[m_low] = []
            all_mods[m_low].append((key, title, m))

    duplicates = {name: info for name, info in all_mods.items() if len(info) > 1}

    if not duplicates:
        return

    print(f"\n⚠️ Trovati {len(duplicates)} duplicati:\n")
    
    modified = False
    for m_low, occurrences in duplicates.items():
        original_name = occurrences[0][2]
        print(f"Mod: \033[1m{original_name}\033[0m")
        print("Presente in:")
        for i, (key, title, name) in enumerate(occurrences):
            print(f"  {i+1}. {title}")
        
        print(f"  {len(occurrences)+1}. Mantieni in tutti (non rimuovere)")
        
        try:
            choice = input(f"\nScegli quale categoria MANTENERE (1-{len(occurrences)}) o premi invio per saltare: ").strip()
            if not choice:
                continue
            
            idx = int(choice) - 1
            if 0 <= idx < len(occurrences):
                keep_key = occurrences[idx][0]
                # Rimuovi da tutti gli altri
                for key, title, name in occurrences:
                    if key != keep_key:
                        config[key].remove(name)
                        print(f"  🗑️ Rimosso da {title}")
                modified = True
            elif idx == len(occurrences):
                print("  ⏩ Saltato.")
            else:
                print("  ❌ Scelta non valida.")
        except ValueError:
            print("  ❌ Scelta non valida.")

    if modified:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print("\n✅ config.json aggiornato con successo.")
    else:
        print("\nℹ️ Nessuna modifica apportata.")

if __name__ == "__main__":
    check_duplicates()
