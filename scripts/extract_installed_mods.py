#!/usr/bin/env python3
"""Extract installed mod names from .modinfo files."""
import json
from pathlib import Path

modpack_dir = Path("/home/matteo/Documenti/mc-quarry/modpack/mods_core_1.21.11")
mods = set()

for info_file in modpack_dir.glob("*.modinfo"):
    try:
        with info_file.open('r') as f:
            data = json.load(f)
            slug = data.get('project_slug', '')
            if slug:
                mods.add(slug)
    except Exception as e:
        print(f"Error reading {info_file}: {e}")

# Print as JSON array
print(json.dumps(sorted(mods), indent=2))
