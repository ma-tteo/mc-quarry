import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .utils import BColors

CONFIG_FILE = "config.json"
CLEAN_CONFIG_FILE = "config_clean.json"

logger = logging.getLogger("mc-quarry")

def load_config(config_path: str = CONFIG_FILE) -> Dict[str, Any]:
    """
    Carica la configurazione da config.json. 
    Se manca, prova a ripristinarla da config_clean.json.
    """
    path = Path(config_path)
    clean_path = Path(CLEAN_CONFIG_FILE)
    
    # Se il file principale manca ma esiste quello pulito, ripristiniamo
    if not path.exists() and clean_path.exists():
        try:
            shutil.copyfile(str(clean_path), str(path))
            logger.info(f"Restored {CONFIG_FILE} from {CLEAN_CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to restore {CONFIG_FILE}: {e}")
    default_config = {
        "language": None,
        "curseforge_api_key": "",
        "mods_folder": "",
        "resourcepacks_folder": "",
        "mods": [],
        "texture_packs": [],
        "incompatible_mods": {},
        "survival_qol_mods": [],
        "install_light_qol": True,
        "light_qol_mods": [],
        "install_medium_qol": False,
        "medium_qol_mods": []
    }

    if path.exists():
        try:
            with path.open('r') as f:
                user_config = json.load(f)
            final_config = default_config.copy()
            final_config.update(user_config)
            return final_config
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Config file {config_path} is corrupted. Error: {e}")
            try:
                shutil.copyfile(str(path), f"{config_path}.bak")
                logger.info(f"Backup of corrupted config created at {config_path}.bak")
            except Exception as backup_err:
                logger.error(f"Could not back up corrupted file: {backup_err}")
    else:
        logger.info(f"Config file {config_path} not found. Creating a new one.")

    save_config(default_config, str(path))
    return default_config

def save_config(data: Dict[str, Any], config_path: str = CONFIG_FILE):
    """Salva le modifiche alla configurazione su disco."""
    path = Path(config_path)
    try:
        with path.open('w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        logger.error(f"Could not save config to {config_path}: {e}")
