#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.ui_manager import get_string

# Category definition: (config_key, title)
MOD_CATEGORIES = [
    ("mods", "💎 CORE MODS"),
    ("curseforge_mods", "🔥 CURSEFORGE MODS"),
    ("light_qol_mods", "💡 LIGHT QOL"),
]


def check_duplicates():
    config_path = Path("config.json")
    if not config_path.exists():
        print(get_string("duplicate_config_not_found"))
        return

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(get_string("duplicate_config_load_error", None, e))
        return

    all_mods = {}  # mod_name -> list of (category_key, category_title)

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

    print(get_string("duplicate_found_summary", None, len(duplicates)))

    modified = False
    for m_low, occurrences in duplicates.items():
        original_name = occurrences[0][2]
        print(
            f"\033[1m{get_string('duplicate_mod_header', None, original_name)}\033[0m"
        )
        print(get_string("duplicate_present_in"))
        for i, (key, title, name) in enumerate(occurrences):
            print(get_string("duplicate_list_entry", None, i + 1, title))

        print(get_string("duplicate_keep_all", None, len(occurrences) + 1))

        try:
            choice = input(
                get_string("duplicate_choice_prompt", None, len(occurrences))
            ).strip()
            if not choice:
                continue

            idx = int(choice) - 1
            if 0 <= idx < len(occurrences):
                keep_key = occurrences[idx][0]
                # Rimuovi da tutti gli altri
                for key, title, name in occurrences:
                    if key != keep_key:
                        config[key].remove(name)
                        print(get_string("duplicate_removed_from", None, title))
                modified = True
            elif idx == len(occurrences):
                print(get_string("duplicate_skipped"))
            else:
                print(get_string("duplicate_invalid_choice"))
        except ValueError:
            print(get_string("duplicate_invalid_choice"))

    if modified:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        print(get_string("duplicate_config_updated"))
    else:
        print(get_string("duplicate_no_changes"))


if __name__ == "__main__":
    check_duplicates()
