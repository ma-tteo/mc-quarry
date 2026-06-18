"""Translation dictionary and language utilities for mc-quarry."""

import locale
import re
from typing import Dict, Optional

translations: Dict[str, Dict[str, str]] = {
    "script_title": {
        "en": "🚀 Modrinth & CurseForge Modpack Downloader v6",
        "it": "🚀 Downloader Modpack Modrinth & CurseForge v6",
    },
    "enter_mc_version": {
        "en": "❓ Please enter the Minecraft version (e.g., 1.21.1): ",
        "it": "❓ Inserisci la versione di Minecraft (es. 1.21.1): ",
    },
    "invalid_version": {
        "en": "❌ Invalid version. Exiting.",
        "it": "❌ Versione non valida. Esco.",
    },
    "target_mc_version": {
        "en": "🎯 Target MC version: {}",
        "it": "🎯 Versione MC di destinazione: {}",
    },
    "mods_output_folder": {
        "en": "📂 Mods output folder: {}",
        "it": "📂 Cartella di output delle mod: {}",
    },
    "reading_installed_mods": {
        "en": "📦 Reading installed mods...",
        "it": "📦 Lettura delle mod installate...",
    },
    "found_valid_mods": {
        "en": "Found {} mods with valid metadata.",
        "it": "Trovate {} mod con metadati validi.",
    },
    "processing_mod": {
        "en": "✨ Processing: {}",
        "it": "✨ Elaborazione: {}",
    },
    "project_not_found": {
        "en": "  ❌ Project not found for '{}'. Skipping.",
        "it": "  ❌ Progetto non trovato per '{}'. Salto.",
    },
    "found_project": {
        "en": "  Found project: {}",
        "it": "  Trovato progetto: {}",
    },
    "no_compatible_version_mod": {
        "en": "  ❌ No compatible version found for this mod. Skipping.",
        "it": "  ❌ Nessuna versione compatibile trovata per questa mod. Salto.",
    },
    "mod_up_to_date": {
        "en": "  ✅ '{}' is already up to date (Version: {}). Skipping.",
        "it": "  ✅ '{}' è già aggiornato (Versione: {}). Salto.",
    },
    "update_available": {
        "en": "  🔄 Update available for '{}'.",
        "it": "  🔄 Aggiornamento disponibile per '{}'.",
    },
    "installed_vs_found": {
        "en": "    Installed: {} -> Found: {}",
        "it": "    Installata: {} -> Trovata: {}",
    },
    "removing_old_file": {
        "en": "    🗑️ Removing old file: {}",
        "it": "    🗑️ Rimozione del vecchio file: {}",
    },
    "latest_version": {
        "en": "  Version: {}",
        "it": "  Versione: {}",
    },
    "no_downloadable_file": {
        "en": "  ❌ No downloadable file found in this version. Skipping.",
        "it": "  ❌ Nessun file scaricabile trovato in questa versione. Salto.",
    },
    "file_exists": {
        "en": "  ⚠️ File '{}' already exists. Skipping.",
        "it": "  ⚠️ Il file '{}' esiste già. Salto.",
    },
    "missing_metadata": {
        "en": "    💾 Missing metadata, creating it now.",
        "it": "    💾 Metadati mancanti, li creo ora.",
    },
    "downloading_file": {
        "en": "  📥 Downloading '{}'...",
        "it": "  📥 Download di '{}'...",
    },
    "download_complete": {
        "en": "  ✅ Download complete.",
        "it": "  ✅ Download completato.",
    },
    "download_failed": {"en": "  ❌ Download failed.", "it": "  ❌ Download fallito."},
    "error_processing": {
        "en": "❌ An error occurred while processing {}: {}",
        "it": "❌ Si è verificato un errore durante l'elaborazione di {}: {}",
    },
    "mods_operation_complete": {
        "en": "📦 Mods operation complete!",
        "it": "📦 Operazione mod completata!",
    },
    "copy_mods_prompt": {
        "en": "❓ Do you want to copy the .jar files to a Minecraft mods folder? (y/n): ",
        "it": "❓ Vuoi copiare i file .jar in una cartella di mod di Minecraft? (s/n): ",
    },
    "suggested_path": {
        "en": "📂 Suggested path: {}",
        "it": "📂 Percorso suggerito: {}",
    },
    "enter_path_prompt": {
        "en": "➡️  Enter the path (leave empty to use the suggested one): ",
        "it": "➡️  Inserisci il percorso (lascia vuoto per usare quello suggerito): ",
    },
    "enter_instance_name": {
        "en": "➡️  Enter the launcher instance name: ",
        "it": "➡️  Inserisci il nome dell'istanza del launcher: ",
    },
    "destination_not_exist": {
        "en": "❌ The destination folder '{}' does not exist. Please create it and try again.",
        "it": "❌ La cartella di destinazione '{}' non esiste. Creala e riprova.",
    },
    "delete_existing_files_prompt": {
        "en": "🗑️ Do you want to delete existing files in the destination folder before copying? (y/n): ",
        "it": "🗑️ Vuoi eliminare i file esistenti nella cartella di destinazione prima di copiare? (s/n): ",
    },
    "copied_file": {"en": "  ✅ Copied: {}", "it": "  ✅ Copiato: {}"},
    "deleted_file": {"en": "  🗑️ Deleted: {}", "it": "  🗑️ Eliminato: {}"},
    "copying_files_to": {
        "en": "📥 Copying files to: {}",
        "it": "📥 Copia dei file in: {}",
    },
    "deleting_files_from": {
        "en": "🗑️ Deleting files from: {}",
        "it": "🗑️ Eliminazione dei file da: {}",
    },
    "download_texture_packs_prompt": {
        "en": "❓ Do you want to download texture packs as well? (y/n): ",
        "it": "❓ Vuoi scaricare anche i texture pack? (s/n): ",
    },
    "script_finished": {
        "en": "🎉 Script finished. Have fun!",
        "it": "🎉 Script terminato. Buon divertimento!",
    },
    "start_texture_pack_download": {
        "en": "🎨 Starting texture pack download...",
        "it": "🎨 Inizio download texture pack...",
    },
    "texture_packs_output_folder": {
        "en": "📂 Texture packs output folder: {}",
        "it": "📂 Cartella di output dei texture pack: {}",
    },
    "no_compatible_version_tp": {
        "en": "  ⚠️ No compatible version found. Trying to download the latest one.",
        "it": "  ⚠️ Nessuna versione compatibile trovata. Tento di scaricare la più recente.",
    },
    "cannot_find_any_version": {
        "en": "  ❌ Could not find any version. Skipping.",
        "it": "  ❌ Impossibile trovare alcuna versione. Salto.",
    },
    "texture_pack_download_complete": {
        "en": "🎨 Texture pack download complete!",
        "it": "🎨 Download dei texture pack completato!",
    },
    "copy_texture_packs_prompt": {
        "en": "❓ Do you want to copy the texture packs to a Minecraft folder? (y/n): ",
        "it": "❓ Vuoi copiare i texture pack in una cartella di Minecraft? (s/n): ",
    },
    "lang_saved": {
        "en": "🌍 Language preference saved.",
        "it": "🌍 Preferenza lingua salvata.",
    },
    "start_parallel": {
        "en": "🚀 Starting parallel download with {} threads...",
        "it": "🚀 Avvio download parallelo con {} thread...",
    },
    "use_configured_path_mods": {
        "en": "Use configured path for mods ({})? (Y/n): ",
        "it": "Vuoi usare il percorso configurato per le mod ({})? (S/n): ",
    },
    "use_configured_path_tps": {
        "en": "Use configured path for texture packs ({})? (Y/n): ",
        "it": "Vuoi usare il percorso configurato per i texture pack ({})? (S/n): ",
    },
    "no_path_provided_mods": {
        "en": "No destination path provided for mods. Copying mods skipped.",
        "it": "Nessun percorso di destinazione fornito per le mod. Copia mod saltata.",
    },
    "no_path_provided_tps": {
        "en": "No destination path provided for texture packs. Copying texture packs skipped.",
        "it": "Nessun percorso di destinazione fornito per i texture pack. Copia texture pack saltata.",
    },
    "path_rejected_batch": {
        "en": "Security error: Non-standard path rejected in auto-accept mode.",
        "it": "Errore di sicurezza: Percorso non standard rifiutato in modalità auto-accept.",
    },
    "operation_cancelled_security": {
        "en": "Operation cancelled for security reasons.",
        "it": "Operazione annullata per motivi di sicurezza.",
    },
    "copying_mods_skipped": {"en": "Copying mods skipped.", "it": "Copia mod saltata."},
    "copying_tps_skipped": {
        "en": "Copying texture packs skipped.",
        "it": "Copia texture pack saltata.",
    },
    "no_light_qol_found": {
        "en": "⚠️ No light QoL mods found in config.",
        "it": "⚠️ Nessuna mod QoL leggera trovata nel config.",
    },
    "starting_light_qol_download": {
        "en": "ℹ️ Starting download of light QoL mods. To disable, set 'install_light_qol' to false in config.json",
        "it": "ℹ️ Inizio download delle mod QoL leggere. Per disabilitare, imposta 'install_light_qol' a false in config.json",
    },
    "config_not_found": {
        "en": "⚠️ {} not found. Creating a new default config file.",
        "it": "⚠️ {} non trovato. Creo un nuovo file di configurazione predefinito.",
    },
    "config_corrupted": {
        "en": "⚠️ {} is corrupted. Backing it up and creating a new default config.",
        "it": "⚠️ {} è corrotto. Eseguo il backup e creo una nuova configurazione predefinita.",
    },
    "backup_failed": {
        "en": "Could not back up corrupted file: {}",
        "it": "Impossibile eseguire il backup del file corrotto: {}",
    },
    "switching_to_cf": {
        "en": "  ⚠️ Not found on Modrinth. Switching to CurseForge...",
        "it": "  ⚠️ Non trovato su Modrinth. Passo a CurseForge...",
    },
    "cf_key_missing": {
        "en": "  ❌ CurseForge API Key missing in config.json. Skipping CurseForge search.",
        "it": "  ❌ Chiave API CurseForge mancante in config.json. Salto la ricerca su CurseForge.",
    },
    "hardware_info": {
        "en": "💻 Detected Hardware: GPU={}, CPU Cores={}",
        "it": "💻 Hardware Rilevato: GPU={}, Core CPU={}",
    },
    "lang_selection_menu": {
        "en": "1. English\n2. Italiano",
        "it": "1. English\n2. Italiano",
    },
    "select_language_prompt": {
        "en": "Select Language: ",
        "it": "Seleziona Lingua: ",
    },
    "invalid_version_format": {
        "en": "Invalid version format. Use semantic versioning (e.g., 1.21.11)",
        "it": "Formato versione non valido. Usa il versioning semantico (es. 1.21.11)",
    },
    "skipped_mods_summary": {
        "en": "⚠️  Skipped {} mod(s):",
        "it": "⚠️  Saltate {} mod:",
    },
    "skipped_incompatible": {
        "en": "Incompatible ({}): {}",
        "it": "Incompatibili ({}): {}",
    },
    "skipped_hardware": {
        "en": "Hardware ({}): {} ({})",
        "it": "Hardware ({}): {} ({})",
    },
    "skipped_other": {
        "en": "Other ({}): {}",
        "it": "Altri ({}): {}",
    },
    "warning_path_outside": {
        "en": "Warning: Path is outside standard directories. Proceeding at your own risk.",
        "it": "Attenzione: Il percorso è al di fuori delle directory standard. Procedi a tuo rischio.",
    },
    "no_mods_found_to_copy": {
        "en": "No mods found to copy.",
        "it": "Nessuna mod trovata da copiare.",
    },
    "config_backup_created": {
        "en": "A backup has been created at {}",
        "it": "Un backup è stato creato in {}",
    },
    "config_fix_json": {
        "en": "Please fix the JSON error (e.g., missing comma) before running again.",
        "it": "Correggi l'errore JSON (es. virgola mancante) prima di eseguire di nuovo.",
    },
    "duplicate_config_not_found": {
        "en": "❌ config.json not found.",
        "it": "❌ config.json non trovato.",
    },
    "duplicate_config_load_error": {
        "en": "❌ Error loading config: {}",
        "it": "❌ Errore nel caricamento del config: {}",
    },
    "duplicate_found_summary": {
        "en": "\n⚠️ Found {} duplicate(s):\n",
        "it": "\n⚠️ Trovati {} duplicati:\n",
    },
    "duplicate_mod_header": {
        "en": "Mod: {}",
        "it": "Mod: {}",
    },
    "duplicate_present_in": {
        "en": "Present in:",
        "it": "Presente in:",
    },
    "duplicate_list_entry": {
        "en": "  {}. {}",
        "it": "  {}. {}",
    },
    "duplicate_keep_all": {
        "en": "  {}. Keep in all (don't remove)",
        "it": "  {}. Mantieni in tutti (non rimuovere)",
    },
    "duplicate_choice_prompt": {
        "en": "\nChoose which category to KEEP (1-{}) or press enter to skip: ",
        "it": "\nScegli quale categoria MANTENERE (1-{}) o premi invio per saltare: ",
    },
    "duplicate_removed_from": {
        "en": "  🗑️ Removed from {}",
        "it": "  🗑️ Rimosso da {}",
    },
    "duplicate_skipped": {
        "en": "  ⏩ Skipped.",
        "it": "  ⏩ Saltato.",
    },
    "duplicate_invalid_choice": {
        "en": "  ❌ Invalid choice.",
        "it": "  ❌ Scelta non valida.",
    },
    "duplicate_config_updated": {
        "en": "\n✅ config.json updated successfully.",
        "it": "\n✅ config.json aggiornato con successo.",
    },
    "duplicate_no_changes": {
        "en": "\nℹ️ No changes made.",
        "it": "\nℹ️ Nessuna modifica apportata.",
    },
    "separator_line": {
        "en": "═════════════════════════════════════════════════════════════",
        "it": "═════════════════════════════════════════════════════════════",
    },
}


selected_lang: str = "en"


def get_string_no_ansi(s: str) -> str:
    """Strip ANSI escape codes from a string for length calculation.

    Args:
        s: String potentially containing ANSI escape sequences

    Returns:
        Clean string with all ANSI codes removed
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", s)


def detect_language() -> str:
    """Detect the system language, returning 'it' for Italian or 'en' as fallback.

    Returns:
        Language code ('it' or 'en')
    """
    try:
        sys_lang = locale.getlocale()[0]
        return "it" if sys_lang and sys_lang.startswith("it") else "en"
    except Exception:
        return "en"


def set_selected_language(lang: str):
    """Set the global language for UI translations.

    Args:
        lang: Language code (e.g. 'en', 'it')
    """
    global selected_lang
    selected_lang = lang


def get_string(key: str, lang: Optional[str] = None, *args) -> str:
    """Retrieve a translated string from the dictionary, falling back to English.

    Args:
        key: Translation key to look up
        lang: Optional language override (defaults to selected_lang)
        *args: Format arguments to substitute into the translated string

    Returns:
        Translated and formatted string, or the key itself if not found
    """
    use_lang = lang if lang else selected_lang
    s = translations.get(key, {}).get(
        use_lang, translations.get(key, {}).get("en", key)
    )
    if args:
        return s.format(*args)
    return s
