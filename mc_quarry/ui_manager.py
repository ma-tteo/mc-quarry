import sys
import os
import locale
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .utils import BColors, BOX_WIDTH, get_visual_length

logger = logging.getLogger("mc-quarry")

translations: Dict[str, Dict[str, str]] = {
    'script_title': {
        'en': "🚀 Modrinth & CurseForge Modpack Downloader v6",
        'it': "🚀 Downloader Modpack Modrinth & CurseForge v6",
    },
    'enter_mc_version': {
        'en': "❓ Please enter the Minecraft version (e.g., 1.21.1): ",
        'it': "❓ Inserisci la versione di Minecraft (es. 1.21.1): ",
    },
    'invalid_version': {
        'en': "❌ Invalid version. Exiting.",
        'it': "❌ Versione non valida. Esco.",
    },
    'target_mc_version': {
        'en': "🎯 Target MC version: {}",
        'it': "🎯 Versione MC di destinazione: {}",
    },
    'mods_output_folder': {
        'en': "📂 Mods output folder: {}",
        'it': "📂 Cartella di output delle mod: {}",
    },
    'reading_installed_mods': {
        'en': "📦 Reading installed mods...",
        'it': "📦 Lettura delle mod installate...",
    },
    'found_valid_mods': {
        'en': "Found {} mods with valid metadata.",
        'it': "Trovate {} mod con metadati validi.",
    },
    'processing_mod': {
        'en': "✨ Processing: {}",
        'it': "✨ Elaborazione: {}",
    },
    'project_not_found': {
        'en': "  ❌ Project not found for '{}'. Skipping.",
        'it': "  ❌ Progetto non trovato per '{}'. Salto.",
    },
    'found_project': {
        'en': "  Found project: {}",
        'it': "  Trovato progetto: {}",
    },
    'no_compatible_version_mod': {
        'en': "  ❌ No compatible version found for this mod. Skipping.",
        'it': "  ❌ Nessuna versione compatibile trovata per questa mod. Salto.",
    },
    'mod_up_to_date': {
        'en': "  ✅ '{}' is already up to date (Version: {}). Skipping.",
        'it': "  ✅ '{}' è già aggiornato (Versione: {}). Salto.",
    },
    'update_available': {
        'en': "  🔄 Update available for '{}'.",
        'it': "  🔄 Aggiornamento disponibile per '{}'.",
    },
    'installed_vs_found': {
        'en': "    Installed: {} -> Found: {}",
        'it': "    Installata: {} -> Trovata: {}",
    },
    'removing_old_file': {
        'en': "    🗑️ Removing old file: {}",
        'it': "    🗑️ Rimozione del vecchio file: {}",
    },
    'latest_version': {
        'en': "  Version: {}",
        'it': "  Versione: {}",
    },
    'no_downloadable_file': {
        'en': "  ❌ No downloadable file found in this version. Skipping.",
        'it': "  ❌ Nessun file scaricabile trovato in questa versione. Salto.",
    },
    'file_exists': {
        'en': "  ⚠️ File '{}' already exists. Skipping.",
        'it': "  ⚠️ Il file '{}' esiste già. Salto.",
    },
    'missing_metadata': {
        'en': "    💾 Missing metadata, creating it now.",
        'it': "    💾 Metadati mancanti, li creo ora.",
    },
    'downloading_file': {
        'en': "  📥 Downloading '{}'...",
        'it': "  📥 Download di '{}'...",
    },
    'download_complete': {
        'en': "  ✅ Download complete.",
        'it': "  ✅ Download completato."
    },
    'download_failed': {
        'en': "  ❌ Download failed.",
        'it': "  ❌ Download fallito."
    },
    'error_processing': {
        'en': "❌ An error occurred while processing {}: {}",
        'it': "❌ Si è verificato un errore durante l\'elaborazione di {}: {}"
    },
    'mods_operation_complete': {
        'en': "📦 Mods operation complete!",
        'it': "📦 Operazione mod completata!"
    },
    'copy_mods_prompt': {
        'en': "❓ Do you want to copy the .jar files to a Minecraft mods folder? (y/n): ",
        'it': "❓ Vuoi copiare i file .jar in una cartella di mod di Minecraft? (s/n): "
    },
    'suggested_path': {
        'en': "📂 Suggested path: {}",
        'it': "📂 Percorso suggerito: {}"
    },
    'enter_path_prompt': {
        'en': "➡️  Enter the path (leave empty to use the suggested one): ",
        'it': "➡️  Inserisci il percorso (lascia vuoto per usare quello suggerito): "
    },
    'enter_instance_name': {
        'en': "➡️  Enter the launcher instance name: ",
        'it': "➡️  Inserisci il nome dell\'istanza del launcher: "
    },
    'destination_not_exist': {
        'en': "❌ The destination folder '{}' does not exist. Please create it and try again.",
        'it': "❌ La cartella di destinazione '{}' non esiste. Creala e riprova."
    },
    'delete_existing_files_prompt': {
        'en': "🗑️ Do you want to delete existing files in the destination folder before copying? (y/n): ",
        'it': "🗑️ Vuoi eliminare i file esistenti nella cartella di destinazione prima di copiare? (s/n): "
    },
    'copied_file': {
        'en': "  ✅ Copied: {}",
        'it': "  ✅ Copiato: {}"
    },
    'deleted_file': {
        'en': "  🗑️ Deleted: {}",
        'it': "  🗑️ Eliminato: {}"
    },
    'copying_files_to': {
        'en': "📥 Copying files to: {}",
        'it': "📥 Copia dei file in: {}"
    },
    'deleting_files_from': {
        'en': "🗑️ Deleting files from: {}",
        'it': "🗑️ Eliminazione dei file da: {}"
    },
    'download_texture_packs_prompt': {
        'en': "❓ Do you want to download texture packs as well? (y/n): ",
        'it': "❓ Vuoi scaricare anche i texture pack? (s/n): "
    },
    'script_finished': {
        'en': "🎉 Script finished. Have fun!",
        'it': "🎉 Script terminato. Buon divertimento!"
    },
    'start_texture_pack_download': {
        'en': "🎨 Starting texture pack download...",
        'it': "🎨 Inizio download texture pack..."
    },
    'texture_packs_output_folder': {
        'en': "📂 Texture packs output folder: {}",
        'it': "📂 Cartella di output dei texture pack: {}"
    },
    'no_compatible_version_tp': {
        'en': "  ⚠️ No compatible version found. Trying to download the latest one.",
        'it': "  ⚠️ Nessuna versione compatibile trovata. Tento di scaricare la più recente."
    },
    'cannot_find_any_version': {
        'en': "  ❌ Could not find any version. Skipping.",
        'it': "  ❌ Impossibile trovare alcuna versione. Salto."
    },
    'texture_pack_download_complete': {
        'en': "🎨 Texture pack download complete!",
        'it': "🎨 Download dei texture pack completato!"
    },
    'copy_texture_packs_prompt': {
        'en': "❓ Do you want to copy the texture packs to a Minecraft folder? (y/n): ",
        'it': "❓ Vuoi copiare i texture pack in una cartella di Minecraft? (s/n): "
    },
    'lang_saved': {
        'en': "🌍 Language preference saved.",
        'it': "🌍 Preferenza lingua salvata."
    },
    'start_parallel': {
        'en': "🚀 Starting parallel download with {} threads...",
        'it': "🚀 Avvio download parallelo con {} thread..."
    },
    'use_configured_path_mods': {
        'en': "Use configured path for mods ({})? (Y/n): ",
        'it': "Vuoi usare il percorso configurato per le mod ({})? (S/n): "
    },
    'use_configured_path_tps': {
        'en': "Use configured path for texture packs ({})? (Y/n): ",
        'it': "Vuoi usare il percorso configurato per i texture pack ({})? (S/n): "
    },
    'no_path_provided_mods': {
        'en': "No destination path provided for mods. Copying mods skipped.",
        'it': "Nessun percorso di destinazione fornito per le mod. Copia mod saltata."
    },
    'no_path_provided_tps': {
        'en': "No destination path provided for texture packs. Copying texture packs skipped.",
        'it': "Nessun percorso di destinazione fornito per i texture pack. Copia texture pack saltata."
    },
    'copying_mods_skipped': {
        'en': "Copying mods skipped.",
        'it': "Copia mod saltata."
    },
    'copying_tps_skipped': {
        'en': "Copying texture packs skipped.",
        'it': "Copia texture pack saltata."
    },
    'install_survival_qol_prompt': {
        'en': "❓ Do you want to install survival QoL mods? (y/n): ",
        'it': "❓ Vuoi installare le qol mods per survival? (s/n): "
    },
    'no_survival_qol_found': {
        'en': "⚠️ No survival QoL mods found in config.",
        'it': "⚠️ Nessuna mod QoL survival trovata nel config."
    },
    'no_medium_qol_found': {
        'en': "⚠️ No medium-light QoL mods found in config.",
        'it': "⚠️ Nessuna mod QoL medio-leggera trovata nel config."
    },
    'no_light_qol_found': {
        'en': "⚠️ No light QoL mods found in config.",
        'it': "⚠️ Nessuna mod QoL leggera trovata nel config."
    },
    'install_medium_qol_prompt': {
        'en': "❓ Do you want to install medium-light QoL mods (visual/audio)? (y/n): ",
        'it': "❓ Vuoi installare le mod QoL medio-leggere (grafica/audio)? (s/n): "
    },
    'starting_light_qol_download': {
        'en': "ℹ️ Starting download of light QoL mods. To disable, set 'install_light_qol' to false in config.json",
        'it': "ℹ️ Inizio download delle mod QoL leggere. Per disabilitare, imposta 'install_light_qol' a false in config.json"
    },
    'config_not_found': {
        'en': "⚠️ {} not found. Creating a new default config file.",
        'it': "⚠️ {} non trovato. Creo un nuovo file di configurazione predefinito."
    },
    'config_corrupted': {
        'en': "⚠️ {} is corrupted. Backing it up and creating a new default config.",
        'it': "⚠️ {} è corrotto. Eseguo il backup e creo una nuova configurazione predefinita."
    },
    'backup_failed': {
        'en': "Could not back up corrupted file: {}",
        'it': "Impossibile eseguire il backup del file corrotto: {}"
    },
    'switching_to_cf': {
        'en': "  ⚠️ Not found on Modrinth. Switching to CurseForge...",
        'it': "  ⚠️ Non trovato su Modrinth. Passo a CurseForge..."
    },
    'cf_key_missing': {
        'en': "  ❌ CurseForge API Key missing in config.json. Skipping CurseForge search.",
        'it': "  ❌ Chiave API CurseForge mancante in config.json. Salto la ricerca su CurseForge."
    },
    'hardware_info': {
        'en': "💻 Detected Hardware: GPU={}, CPU Cores={}",
        'it': "💻 Hardware Rilevato: GPU={}, Core CPU={}",
    },
}

selected_lang = 'en'

def detect_language() -> str:
    """Tentativo di rilevare la lingua di sistema."""
    try:
        sys_lang = locale.getlocale()[0]
        return 'it' if sys_lang and sys_lang.startswith('it') else 'en'
    except:
        return 'en'

def set_selected_language(lang: str):
    global selected_lang
    selected_lang = lang

def get_string(key: str, lang: Optional[str] = None, *args) -> str:
    """Recupera una stringa tradotta dal dizionario, con fallback all'inglese."""
    use_lang = lang if lang else selected_lang
    s = translations.get(key, {}).get(use_lang, translations.get(key, {}).get('en', key))
    if args:
        return s.format(*args)
    return s

def print_banner():
    """Print ASCII art banner."""
    banner = rf"""{BColors.OKCYAN}
    __  _________     ____                             
   /  |/  / ____/    / __ \__  ______ _____________  __
  / /|_/ / /  ______/ / / / / / / __ `/ ___/ ___/ / / /
 / /  / / /__/_____/ /_/ / /_/ / /_/ / /  / /  / /_/ / 
/_/  /_/\____/     \___\_\__,_/\__,_/_/  /_/   \__, /  
                                              /____/   
{BColors.ENDC}"""
    print(banner)
def print_section_header(title: str, icon: str = "", color: str = BColors.OKCYAN):
    """Print a section header with Unicode borders."""
    inner_width = BOX_WIDTH - 2
    content = f" {icon}  {title}" if icon else f" {title}"
    v_len = get_visual_length(content)
    padding = inner_width - v_len
    if padding < 0: padding = 0

    print(f"\n{color}╔{'═' * inner_width}╗{BColors.ENDC}")
    print(f"{color}║{BColors.ENDC}{BColors.BOLD}{content}{BColors.ENDC}{' ' * padding}{color}║{BColors.ENDC}")
    print(f"{color}╚{'═' * inner_width}╝{BColors.ENDC}")


def print_progress_bar(current: int, total: int, width: int = 30, label: str = ""):
    """Print a progress bar with percentage. (Currently unused)"""
    if total == 0:
        return
    ratio = current / total
    filled = int(width * ratio)
    bar = '█' * filled + '░' * (width - filled)
    pct = int(ratio * 100)

    if pct < 33:
        bar_color = BColors.FAIL
    elif pct < 66:
        bar_color = BColors.WARNING
    else:
        bar_color = BColors.OKGREEN

    line = f"\r  {bar_color}{bar}{BColors.ENDC}  {BColors.BOLD}{current}{BColors.ENDC}/{total}  {BColors.DIM}[{pct}%]{BColors.ENDC}"
    if label:
        line += f"  {BColors.DIM}{label}{BColors.ENDC}"
    sys.stdout.write(line + ' ' * 10)
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write('\n')
        sys.stdout.flush()

def detect_hardware() -> Dict[str, Any]:
    """
    Detect system hardware (GPU and CPU).
    
    Returns:
        Dict with 'gpu' (nvidia/amd/intel/apple/generic) and 'cpu_cores'
    """
    import os
    import subprocess
    hardware = {"gpu": "generic", "cpu_cores": os.cpu_count() or 1}

    try:
        if sys.platform == "linux":
            # Try lspci first (most common on Linux)
            try:
                output = subprocess.check_output(['lspci'], stderr=subprocess.STDOUT, timeout=10).decode('utf-8').lower()
                if 'nvidia' in output:
                    hardware["gpu"] = "nvidia"
                elif 'amd' in output or 'ati' in output:
                    hardware["gpu"] = "amd"
                elif 'intel' in output:
                    hardware["gpu"] = "intel"
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                # Fallback: check /sys/class/drm (works on most Linux without lspci)
                logger.debug(f"lspci failed, trying /sys/module fallback: {e}")
                try:
                    for driver in ['nvidia', 'radeon', 'amdgpu', 'i915']:
                        if Path(f"/sys/module/{driver}").exists():
                            hardware["gpu"] = "nvidia" if driver == "nvidia" else "amd" if driver in ['radeon', 'amdgpu'] else "intel"
                            break
                except Exception as e:
                    logger.debug(f"Hardware detection via /sys/module failed: {e}")
        elif sys.platform == "win32":
            # Windows: use wmic
            try:
                output = subprocess.check_output(
                    ['wmic', 'path', 'win32_videocontroller', 'get', 'name'],
                    stderr=subprocess.STDOUT, timeout=10
                ).decode('utf-8', errors='ignore').lower()
                if 'nvidia' in output:
                    hardware["gpu"] = "nvidia"
                elif 'amd' in output or 'ati' in output or 'radeon' in output:
                    hardware["gpu"] = "amd"
                elif 'intel' in output:
                    hardware["gpu"] = "intel"
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                logger.debug(f"Windows GPU detection failed: {e}")
        elif sys.platform == "darwin":
            # macOS: use system_profiler
            try:
                output = subprocess.check_output(
                    ['system_profiler', 'SPDisplaysDataType'],
                    stderr=subprocess.STDOUT, timeout=10
                ).decode('utf-8', errors='ignore').lower()
                if 'amd' in output or 'radeon' in output:
                    hardware["gpu"] = "amd"
                elif 'intel' in output:
                    hardware["gpu"] = "intel"
                elif 'apple' in output:
                    hardware["gpu"] = "apple"  # Apple Silicon integrated
                elif 'nvidia' in output:
                    hardware["gpu"] = "nvidia"
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                logger.debug(f"macOS GPU detection failed: {e}")
    except Exception as e:
        # Log unexpected errors but keep generic fallback
        logger.debug(f"Hardware detection failed: {e}")

    return hardware


def print_download_summary(stats: Any) -> None:
    """Print download summary with ASCII art header."""
    inner_width = BOX_WIDTH - 2
    indent_val = 2

    def print_row(content, row_color=BColors.OKBLUE, indent=indent_val):
        v_len = get_visual_length(content)
        padding = inner_width - v_len - indent
        print(f"{row_color}║{BColors.ENDC}{' ' * indent}{content}{' ' * max(0, padding)}{row_color}║{BColors.ENDC}")

    print(f"\n{BColors.OKBLUE}╔{'═' * inner_width}╗{BColors.ENDC}")
    # ASCII ART Header
    content_header = [
        fr"{BColors.HEADER}{BColors.BOLD} ___ ___ ___ ___ ___ ___  _  _   ___ _   _ __  __ __  __   _   _____   __ {BColors.ENDC}",
        fr"{BColors.HEADER}{BColors.BOLD}/ __| __/ __/ __|_ _/ _ \| \| | / __| | | |  \/  |  \/  | /_\ | _ \ \ / / {BColors.ENDC}",
        fr"{BColors.HEADER}{BColors.BOLD}\__ \ _|\__ \__ \| | (_) | .` | \__ \ |_| | |\/| | |\/| |/ _ \|   /\ V /  {BColors.ENDC}",
        fr"{BColors.HEADER}{BColors.BOLD}|___/___|___/___/___\___/|_|\_| |___/\___/|_|  |_|_|  |_/_/ \_\_|_ \ |_|   {BColors.ENDC}"
    ]
    for line in content_header:
        print_row(line, indent=indent_val)

    print(f"{BColors.OKBLUE}╠{'═' * inner_width}╣{BColors.ENDC}")

    print_row(f"{BColors.OKGREEN}✅ Installed: {BColors.BOLD}{stats.installed}{BColors.ENDC}")
    print_row(f"{BColors.OKCYAN}🔄 Updated:   {BColors.BOLD}{stats.updated}{BColors.ENDC}")
    print_row(f"{BColors.OKBLUE}💤 Up to date:{BColors.BOLD}{stats.skipped_up_to_date}{BColors.ENDC}")
    print_row(f"{BColors.WARNING}⚠️  Incompat.: {BColors.BOLD}{stats.skipped_incompatible}{BColors.ENDC}")

    if stats.not_found or stats.failed:
        print(f"{BColors.OKBLUE}╠{'═' * inner_width}╣{BColors.ENDC}")
        max_label_len = inner_width - indent_val - 4
        for name in stats.not_found:
            safe_name = name[:max_label_len-12] + "..." if len(name) > max_label_len-12 else name
            print_row(f"{BColors.FAIL}❌ NOT FOUND: {BColors.ENDC}{BColors.BOLD}{safe_name}{BColors.ENDC}")
        for name, reason in stats.failed:
            detail = f" ({reason})" if reason else ""
            available = inner_width - indent_val - 15
            full_text = f"{name}{detail}"
            if len(full_text) > available:
                safe_text = full_text[:available-3] + "..."
            else:
                safe_text = full_text
            print_row(f"{BColors.FAIL}❌ FAILED:    {BColors.ENDC}{BColors.BOLD}{safe_text}{BColors.ENDC}")

    print(f"{BColors.OKBLUE}╚{'═' * inner_width}╝{BColors.ENDC}\n")
