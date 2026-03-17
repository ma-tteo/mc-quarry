#!/usr/bin/env python3
"""
Validate config.json structure and check for common issues.

Usage:
    python3 scripts/validate_config.py [config.json]
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.config_manager import CONFIG_FILE


def validate_config(config_path: str = CONFIG_FILE) -> bool:
    """Validate configuration file structure."""
    print("=" * 60)
    print(f"Validating {config_path}...")
    print("=" * 60)

    path = Path(config_path)
    if not path.exists():
        print(f"  ❌ Config file not found: {path}")
        return False

    try:
        with path.open('r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON: {e}")
        return False

    print(f"  ✅ Valid JSON structure")

    # Check required fields
    required_fields = [
        "language",
        "mods_folder",
        "resourcepacks_folder",
        "mods",
        "texture_packs",
        "incompatible_mods",
        "survival_qol_mods",
        "install_light_qol",
        "light_qol_mods",
        "install_medium_qol",
        "medium_qol_mods",
    ]

    missing = []
    for field in required_fields:
        if field not in config:
            missing.append(field)

    if missing:
        print(f"  ⚠️  Missing fields: {', '.join(missing)}")
    else:
        print(f"  ✅ All required fields present")

    # Check for empty lists
    list_fields = ["mods", "texture_packs", "survival_qol_mods", "light_qol_mods", "medium_qol_mods"]
    for field in list_fields:
        if field in config and not config[field]:
            print(f"  ⚠️  Empty list: {field}")

    # Check for empty strings
    string_fields = ["mods_folder", "resourcepacks_folder"]
    for field in string_fields:
        if field in config and not config[field]:
            print(f"  ⚠️  Empty path: {field}")

    # Check API key
    if "curseforge_api_key" in config:
        key = config["curseforge_api_key"]
        if not key:
            print(f"  ⚠️  CurseForge API key not set")
        elif len(key) < 30:
            print(f"  ⚠️  CurseForge API key seems too short ({len(key)} chars)")
        else:
            print(f"  ✅ CurseForge API key present ({key[:4]}...{key[-4:]})")

    # Check for incompatible_mods structure
    if "incompatible_mods" in config:
        if not isinstance(config["incompatible_mods"], dict):
            print(f"  ❌ incompatible_mods should be a dict")
        else:
            print(f"  ✅ incompatible_mods: {len(config['incompatible_mods'])} rules defined")

    # Check for conflicts structure
    if "conflicts" in config:
        if not isinstance(config["conflicts"], dict):
            print(f"  ❌ conflicts should be a dict")
        else:
            print(f"  ✅ conflicts: {len(config['conflicts'])} rules defined")

    # Check for requirements structure
    if "requirements" in config:
        if not isinstance(config["requirements"], dict):
            print(f"  ❌ requirements should be a dict")
        else:
            print(f"  ✅ requirements: {len(config['requirements'])} rules defined")

    print("\n" + "=" * 60)
    print("Validation complete!")
    print("=" * 60)

    return True


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else CONFIG_FILE
    success = validate_config(config_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
