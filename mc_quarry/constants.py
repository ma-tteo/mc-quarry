"""Shared constants for mc-quarry.

Single source of truth for category definitions used across
main.py (CLI), web_interface.py (web UI), and scripts/.
"""

CATEGORIES = {
    "core_mods": {
        "project_type": "mod",
        "subdir": "mods_core",
        "title": "\U0001f48e CORE MODS",
        "provider": "modrinth",
        "config_flag": None,
    },
    "utility_mods": {
        "project_type": "mod",
        "subdir": "mods_utility",
        "title": "\U0001f6e0\ufe0f UTILITY MODS",
        "provider": "modrinth",
        "config_flag": None,
    },
    "curseforge_mods": {
        "project_type": "mod",
        "subdir": "mods_curseforge",
        "title": "\U0001f525 CURSEFORGE MODS",
        "provider": "curseforge",
        "config_flag": None,
    },
    "light_qol_mods": {
        "project_type": "mod",
        "subdir": "mods_light_qol",
        "title": "\U0001f4a1 LIGHT QOL",
        "provider": "modrinth",
        "config_flag": "install_light_qol",
    },
    "texture_packs": {
        "project_type": "resourcepack",
        "subdir": "texture_packs",
        "title": "\U0001f3a8 TEXTURE PACKS",
        "provider": "modrinth",
        "config_flag": None,
    },
    "curseforge_texture_packs": {
        "project_type": "resourcepack",
        "subdir": "texture_packs_cf",
        "title": "\U0001f525 CURSEFORGE TEXTURE PACKS",
        "provider": "curseforge",
        "config_flag": None,
    },
}

# Derived list matching main.py's MOD_CATEGORIES format:
# (category_key, project_type, subdir, title, config_flag, provider) — mods only.
MOD_CATEGORIES_LIST = [
    (
        key,
        info["project_type"],
        info["subdir"],
        info["title"],
        info["config_flag"],
        info["provider"],
    )
    for key, info in CATEGORIES.items()
    if info["project_type"] == "mod"
]

# Derived list matching scripts/check_duplicates.py format:
# (category_key, title) — mods only.
CATEGORY_TITLES = [
    (key, info["title"])
    for key, info in CATEGORIES.items()
    if info["project_type"] == "mod"
]
