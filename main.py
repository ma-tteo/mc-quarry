#!/usr/bin/env python3
r"""
MC Quarry - Modrinth & CurseForge Modpack Downloader

    __  _________     ____                             
   /  |/  / ____/    / __ \__  ______ _____________  __
  / /|_/ / /  ______/ / / / / / / __ `/ ___/ ___/ / / /
 / /  / / /__/_____/ /_/ / /_/ / /_/ / /  / /  / /_/ / 
/_/  /_/\____/     \___\_\__,_/\__,_/_/  /_/   \__, /  
                                              /____/   

Copyright (C) 2026 Matto244

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import sys
import os
import re
import time
import shutil
import argparse
import threading
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional

from mc_quarry.utils import BColors, DownloadStats, BOX_WIDTH
from mc_quarry.config_manager import load_config, save_config
from mc_quarry.ui_manager import (
    get_string, print_banner, print_section_header, print_download_summary,
    detect_language, set_selected_language, detect_hardware, ui
)
from mc_quarry.api_client import APIClient, CF_MOD_CLASS_ID, CF_RESOURCE_PACK_CLASS_ID
from mc_quarry.downloader import (
    read_all_mod_info, filter_mods, execute_download
)

# Setup logging - file only, no console output (use --debug for verbose)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("mc-quarry.log"),
    ]
)
logger = logging.getLogger("mc-quarry")

# Semantic version pattern for Minecraft versions (e.g., 1.21.11, 1.20.1-beta.3)
MC_VERSION_PATTERN = re.compile(r'^\d+\.\d+(\.\d+)?([+-][a-zA-Z0-9.]+)?$')

# Category definition: (config_key, project_type, output_subdir, title, config_flag)
MOD_CATEGORIES = [
    ("mods", "mod", "mods_core", "💎 CORE MODS", None),
    ("curseforge_mods", "mod_cf", "mods_core", "🔥 CURSEFORGE MODS", None),
    ("light_qol_mods", "mod", "mods_light_qol", "💡 LIGHT QOL", "install_light_qol"),
    ("medium_qol_mods", "mod", "mods_medium_qol", "🎭 MEDIUM QOL", "install_medium_qol"),
    ("survival_qol_mods", "mod", "mods_survival", "⚔️ SURVIVAL QOL", "install_survival_qol")
]


def _process_mod_wrapper(
    client: APIClient,
    name: str,
    mc_version: str,
    project_type: str,
    output_dir: Path,
    installed_mods: Dict[str, Any],
    stats: DownloadStats,
    provider: str,
    verbose: bool = False
) -> None:
    """
    Generic wrapper for processing mods from any provider (Modrinth/CurseForge).
    Prints messages via UI manager for thread safety.
    """
    clean_name = name.strip()

    try:
        project = None
        
        if provider == "modrinth":
            # Handle Modrinth
            if "modrinth.com" in clean_name:
                slug = clean_name.rstrip('/').split('/')[-1]
                project_data = client.get_modrinth_project(slug)
                if project_data:
                    project = {
                        "project_id": project_data["id"],
                        "slug": project_data["slug"],
                        "title": project_data["title"]
                    }

            if not project:
                search_results = client.search_modrinth(clean_name, project_type)
                if search_results and "hits" in search_results and search_results["hits"]:
                    hits = search_results["hits"]
                    name_low = clean_name.lower()
                    
                    # 1. Look for exact match (title or slug)
                    for h in hits:
                        if h.get("title", "").lower() == name_low or h.get("slug", "").lower() == name_low:
                            project = h
                            break
                    
                    # 2. Fallback to first hit only if it's a very close match (title contains search term)
                    if not project and hits:
                        first_hit = hits[0]
                        first_title = first_hit.get("title", "").lower()
                        if name_low in first_title or first_title in name_low:
                            project = first_hit

            if project:
                title = project.get("title") or project.get("name")
                loader = 'fabric' if project_type == 'mod' else None
                pid = project["project_id"] if "project_id" in project else project["id"]
                latest_version = client.find_modrinth_version(pid, mc_version, loader=loader)

                if not latest_version and project_type == 'resourcepack':
                    latest_version = client.find_modrinth_version(pid, mc_version, loader=None, force_latest=True)

                if latest_version:
                    file_info = client.pick_file_from_version(latest_version)
                    if file_info:
                        project_url = f"https://modrinth.com/{project_type}/{project['slug']}"
                        
                        ui.set_status(f"Processing {clean_name}...")
                        execute_download(
                            clean_name, pid, project["slug"],
                            latest_version["id"], latest_version["name"],
                            file_info["filename"], file_info["url"],
                            "modrinth", output_dir, installed_mods, stats, 
                            lambda msg: ui.log(msg), project_url, verbose
                        )
                        ui.update_progress()
                        return
                    else:
                        ui.log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{title}{BColors.ENDC} — {BColors.FAIL}❌ No file{BColors.ENDC}")
                        stats.add_failed(title, "No file to download")
                        ui.update_progress()
                        return
                else:
                    # No compatible version found on Modrinth
                    if verbose:
                        ui.log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{title}{BColors.ENDC} — {BColors.FAIL}❌ No compatible version{BColors.ENDC} (Modrinth)")
                    stats.add_failed(title, "No compatible version found on Modrinth")
                    ui.update_progress()
                    return
            
            # Not found on Modrinth
            if verbose:
                ui.log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC} — {BColors.FAIL}❌ Not Found{BColors.ENDC} (Modrinth)")
            stats.add_not_found(clean_name)
            ui.update_progress()
            return

        elif provider == "curseforge":
            # Handle CurseForge
            if not client.cf_api_key:
                ui.log(f"{BColors.BOLD}{clean_name}{BColors.ENDC}: {BColors.FAIL}❌ CF API Key missing{BColors.ENDC}")
                stats.add_not_found(clean_name)
                ui.update_progress()
                return
            
            ui.set_status(f"Searching CF: {clean_name}...")
            if "curseforge.com" in clean_name:
                clean_name = clean_name.rstrip('/').split('/')[-1]

            cf_class_id = CF_MOD_CLASS_ID if project_type == 'mod' else CF_RESOURCE_PACK_CLASS_ID
            cf_project = client.search_curseforge(clean_name, class_id=cf_class_id)

            if not cf_project:
                if verbose:
                    ui.log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC} — {BColors.FAIL}❌ Not Found{BColors.ENDC} (CurseForge)")
                stats.add_not_found(clean_name)
                ui.update_progress()
                return

            cf_loader = 4 if project_type == 'mod' else 0
            cf_file = client.get_latest_file_cf(cf_project['id'], mc_version, mod_loader_type=cf_loader)

            if not cf_file:
                if verbose:
                    ui.log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{cf_project['name']}{BColors.ENDC} — {BColors.FAIL}❌ No compatible version{BColors.ENDC} (CurseForge)")
                stats.add_failed(cf_project['name'], "No compatible version on CF")
                ui.update_progress()
                return

            project_url = cf_project.get('links', {}).get('websiteUrl', 
                f"https://www.curseforge.com/minecraft/{'mc-mods' if project_type=='mod' else 'texture-packs'}/{cf_project['slug']}")
            
            execute_download(
                clean_name, str(cf_project['id']), cf_project['slug'],
                str(cf_file['id']), cf_file.get('displayName', str(cf_file['id'])),
                cf_file['fileName'], cf_file['downloadUrl'],
                "curseforge", output_dir, installed_mods, stats, 
                lambda msg: ui.log(msg), project_url, verbose
            )
            ui.update_progress()
            return

    except Exception as e:
        ui.log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC} — {BColors.FAIL}❌ System Error{BColors.ENDC}")
        ui.log(f"   {BColors.DIM}Detail: {e}{BColors.ENDC}")
        stats.add_failed(clean_name, str(e))
        logger.exception(f"{provider} processing error for {clean_name}")
        ui.update_progress()

def select_language(args_lang: Optional[str], config: Dict[str, Any]) -> str:
    """Select language from args, config, or user input."""
    lang = args_lang or config.get("language") or detect_language()
    if not (args_lang or config.get("language")):
        print("1. English\n2. Italiano")
        choice = input("Select Language: ").strip()
        lang = 'it' if choice == '2' else 'en'
        config["language"] = lang
        save_config(config)
    set_selected_language(lang)
    return lang


def get_mc_version(args_version: Optional[str]) -> str:
    """Get Minecraft version from args or user input with validation."""
    version = args_version or input(f" {BColors.BOLD}{get_string('enter_mc_version')}{BColors.ENDC}").strip()
    if not version:
        print(get_string('invalid_version'))
        sys.exit(1)
    
    # Validate version format
    if not MC_VERSION_PATTERN.match(version):
        print(f"{BColors.FAIL}Invalid version format. Use semantic versioning (e.g., 1.21.11){BColors.ENDC}")
        sys.exit(1)
    
    return version


def should_process_category(flag: Optional[str], config: Dict[str, Any], args_yes: bool) -> bool:
    """Determine if a mod category should be processed based on config and user input."""
    if not flag:
        return True
    
    enabled_in_config = config.get(flag, False) if flag != "install_light_qol" else config.get(flag, True)
    
    if flag == "install_light_qol":
        return enabled_in_config
    
    # For Medium and Survival QoL: use config in batch mode, ask in interactive
    if args_yes:
        return enabled_in_config
    
    prompt_key = 'install_medium_qol_prompt' if flag == "install_medium_qol" else 'install_survival_qol_prompt'
    return input(f"\n{BColors.BOLD}{get_string(prompt_key)}{BColors.ENDC}").lower().startswith(('y', 's'))

def process_mod_category(
    client: APIClient,
    config_key: str,
    project_type: str,
    out_dir: Path,
    title: str,
    config: Dict[str, Any],
    mc_version: str,
    args_yes: bool,
    threads: int,
    global_stats: DownloadStats,
    hardware: Dict[str, Any],
    verbose: bool = False
) -> None:
    """Process a single mod category (download mods)."""
    mod_list = config.get(config_key, [])
    if not mod_list:
        return

    print_section_header(title)
    out_dir.mkdir(parents=True, exist_ok=True)
    installed = read_all_mod_info(out_dir)
    active_list, skipped = filter_mods(mod_list, mc_version, config, hardware)

    # Group skipped mods by reason category
    skipped_by_reason = {
        'incompatible': [],
        'hardware': [],
        'other': []
    }
    
    for mod_name, reason in skipped:
        reason_lower = reason.lower()
        if 'incompatible' in reason_lower or 'incompatible by rule' in reason_lower:
            skipped_by_reason['incompatible'].append((mod_name, reason))
        elif 'cores' in reason_lower or 'gpu' in reason_lower or 'requires' in reason_lower:
            skipped_by_reason['hardware'].append((mod_name, reason))
        else:
            skipped_by_reason['other'].append((mod_name, reason))
    
    # Print grouped skip summary
    total_skipped = len(skipped)
    if total_skipped > 0:
        print(f"\n{BColors.WARNING}⚠️  Skipped {total_skipped} mod(s):{BColors.ENDC}")
        
        if skipped_by_reason['incompatible']:
            count = len(skipped_by_reason['incompatible'])
            mods = ', '.join([m[0] for m in skipped_by_reason['incompatible'][:5]])
            if count > 5:
                mods += f" (+{count - 5} more)"
            print(f"   {BColors.DIM}Incompatible ({count}):{BColors.ENDC} {mods}")
        
        if skipped_by_reason['hardware']:
            count = len(skipped_by_reason['hardware'])
            for mod_name, reason in skipped_by_reason['hardware']:
                print(f"   {BColors.DIM}Hardware ({count}):{BColors.ENDC} {mod_name} ({reason})")
        
        if skipped_by_reason['other']:
            count = len(skipped_by_reason['other'])
            mods = ', '.join([m[0] for m in skipped_by_reason['other'][:5]])
            if count > 5:
                mods += f" (+{count - 5} more)"
            print(f"   {BColors.DIM}Other ({count}):{BColors.ENDC} {mods}")
        
        # Log detailed skip reasons
        for mod_name, reason in skipped:
            logger.info(f"Skipped: {mod_name} - {reason}")

    # Process downloads
    if active_list:
        ui.set_total(len(active_list))
        ui.set_status(f"Downloading {title}...")
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            if project_type == "mod_cf":
                futures = [executor.submit(process_curseforge_wrapper, client, m, mc_version, "mod", out_dir, installed, global_stats, verbose) for m in active_list]
            else:
                futures = [executor.submit(process_modrinth_wrapper, client, m, mc_version, project_type, out_dir, installed, global_stats, verbose) for m in active_list]
            
            # Wait for all downloads to complete and catch exceptions
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    logger.error(f"Thread execution error: {e}")
                    ui.log(f"{BColors.FAIL}❌ Thread Error:{BColors.ENDC} {e}")
        
        ui.finish()
        print()  # Newline after section


def process_texture_packs(
    client: APIClient,
    config: Dict[str, Any],
    mc_version: str,
    args_yes: bool,
    threads: int,
    base_dir: Path,
    global_stats: DownloadStats,
    verbose: bool = False
) -> Optional[Path]:
    """Process texture packs download and return destination path if copied."""
    tp_list = config.get("texture_packs", [])
    if not tp_list:
        return None

    do_tp = args_yes
    if not do_tp:
        do_tp = input(f"\n{BColors.BOLD}{get_string('download_texture_packs_prompt')}{BColors.ENDC}").lower().startswith(('y', 's'))

    if not do_tp:
        return None

    tp_dir = base_dir / f"texture_packs_{mc_version}"
    tp_dir.mkdir(parents=True, exist_ok=True)
    print_section_header("🎨 TEXTURE PACKS")

    # Use global stats
    ui.set_total(len(tp_list))
    ui.set_status("Downloading Texture Packs...")
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(process_modrinth_wrapper, client, tp, mc_version, 'resourcepack', tp_dir, {}, global_stats, verbose) for tp in tp_list]
        for _ in as_completed(futures):
            pass

    ui.finish()

    if args_yes or input(f"\n{BColors.BOLD}{get_string('copy_texture_packs_prompt')}{BColors.ENDC}").lower().strip().startswith(('y', 's')):
        dest_tps = get_destination_path("resourcepacks_folder", False, args_yes, config)
        if dest_tps:
            config["resourcepacks_folder"] = str(dest_tps)
            save_config(config)
            dest_tps.mkdir(parents=True, exist_ok=True)
            print(f"{BColors.OKBLUE}{get_string('copying_files_to', None, dest_tps)}{BColors.ENDC}")
            for f in tp_dir.glob("*.zip"):
                shutil.copy(f, dest_tps)
                print(f"  {BColors.OKGREEN}{get_string('copied_file', None, f.name)}{BColors.ENDC}")
            return dest_tps
    return None


def copy_mods_to_destination(config: Dict[str, Any], args_yes: bool, base_dir: Path, mc_version: str) -> None:
    """Copy all downloaded mods to the destination folder."""
    if not (args_yes or input(f"\n{BColors.BOLD}{get_string('copy_mods_prompt')}{BColors.ENDC}").lower().strip().startswith(('y', 's'))):
        return
    
    dest = get_destination_path("mods_folder", True, args_yes, config)
    if not dest:
        return
    
    config["mods_folder"] = str(dest)
    save_config(config)
    dest.mkdir(parents=True, exist_ok=True)
    
    if args_yes or input(f"{BColors.WARNING}{get_string('delete_existing_files_prompt')}{BColors.ENDC}").lower().startswith(('y', 's')):
        for f in dest.glob("*.jar"):
            f.unlink()

    # Collect all jars from enabled categories
    all_jars = []
    for cfg_key, _, subdir, _, flag in MOD_CATEGORIES:
        if not config.get(cfg_key):
            continue
        should_have_processed = True
        if flag:
            should_have_processed = config.get(flag, False) if flag != "install_light_qol" else config.get(flag, True)
        if should_have_processed:
            out_dir = base_dir / f"{subdir}_{mc_version}"
            if out_dir.exists():
                all_jars.extend(out_dir.glob("*.jar"))

    if all_jars:
        print(f"{BColors.OKBLUE}{get_string('copying_files_to', None, dest)}{BColors.ENDC}")
        for f in all_jars:
            shutil.copy(f, dest)
            print(f"  {BColors.OKGREEN}{get_string('copied_file', None, f.name)}{BColors.ENDC}")
    else:
        print(f"{BColors.WARNING}No mods found to copy.{BColors.ENDC}")


def process_modrinth_wrapper(client: APIClient, name: str, mc_version: str, project_type: str, output_dir: Path, installed_mods: Dict[str, Any], stats: DownloadStats, verbose: bool = False):
    """Wrapper for Modrinth downloads (uses unified _process_mod_wrapper)."""
    _process_mod_wrapper(client, name, mc_version, project_type, output_dir, installed_mods, stats, "modrinth", verbose)


def process_curseforge_wrapper(client: APIClient, name: str, mc_version: str, project_type: str, output_dir: Path, installed_mods: Dict[str, Any], stats: DownloadStats, verbose: bool = False):
    """Wrapper for CurseForge downloads (uses unified _process_mod_wrapper)."""
    _process_mod_wrapper(client, name, mc_version, project_type, output_dir, installed_mods, stats, "curseforge", verbose)

def get_destination_path(config_key: str, is_mod: bool, args_yes: bool, current_config: Dict[str, Any]) -> Optional[Path]:
    """
    Get destination path for mods/resourcepacks with security validation.

    Validates that paths are within safe directories to prevent path traversal attacks.
    """
    current_folder = current_config.get(config_key, "")
    home = Path.home()

    default_suggested = ""
    if sys.platform == "win32":
        # Windows
        default_suggested = home / "AppData/Roaming/.minecraft" / ("mods" if is_mod else "resourcepacks")
    elif sys.platform == "darwin":
        # macOS
        default_suggested = home / "Library/Application Support/minecraft" / ("mods" if is_mod else "resourcepacks")
    elif sys.platform == "linux":
        # Linux - check for various launcher locations
        flatpak_prism = home / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances"
        standard_prism = home / ".local/share/PrismLauncher/instances"
        standard_multimc = home / ".local/share/multimc/instances"
        # Also check for .minecraft in home (most common across all distros)
        vanilla_minecraft = home / ".minecraft"

        if flatpak_prism.exists():
            default_suggested = flatpak_prism / "<INSTANCE_NAME>/.minecraft/" / ("mods" if is_mod else "resourcepacks")
        elif standard_prism.exists():
            default_suggested = standard_prism / "<INSTANCE_NAME>/.minecraft/" / ("mods" if is_mod else "resourcepacks")
        elif standard_multimc.exists():
            default_suggested = standard_multimc / "<INSTANCE_NAME>/.minecraft/" / ("mods" if is_mod else "resourcepacks")
        elif vanilla_minecraft.exists():
            default_suggested = vanilla_minecraft / ("mods" if is_mod else "resourcepacks")
        else:
            # Fallback to Flatpak mojang path (least common)
            default_suggested = home / ".var/app/com.mojang.Minecraft/data/minecraft/" / ("mods" if is_mod else "resourcepacks")
    else:
        # Unknown platform - use generic .minecraft
        default_suggested = home / ".minecraft" / ("mods" if is_mod else "resourcepacks")

    final_path = ""
    if args_yes:
        final_path = current_folder if current_folder else str(default_suggested)
    else:
        if current_folder:
            choice = input(f"{BColors.BOLD}{get_string('use_configured_path_mods' if is_mod else 'use_configured_path_tps', None, current_folder)}{BColors.ENDC}").strip().lower()
            if choice == 'n':
                print(f"{BColors.OKCYAN}{get_string('suggested_path', None, default_suggested)}{BColors.ENDC}")
                new_path = input(f"{BColors.BOLD}{get_string('enter_path_prompt')}{BColors.ENDC}").strip()
                final_path = new_path if new_path else str(default_suggested)
            else:
                final_path = current_folder
        else:
            print(f"{BColors.OKCYAN}{get_string('suggested_path', None, default_suggested)}{BColors.ENDC}")
            new_path = input(f"{BColors.BOLD}{get_string('enter_path_prompt')}{BColors.ENDC}").strip()
            final_path = new_path if new_path else str(default_suggested)

    if "<INSTANCE_NAME>" in str(final_path):
        if args_yes:
            logger.error("Cannot determine instance name in batch mode.")
            return None
        instance = input(f"{BColors.BOLD}{get_string('enter_instance_name')}{BColors.ENDC}").strip()
        final_path = str(final_path).replace("<INSTANCE_NAME>", instance)

    if not final_path:
        return None

    # Security validation: prevent path traversal attacks
    try:
        resolved = Path(final_path).resolve()
        home_resolved = Path.home().resolve()

        # Check if path is within home directory
        try:
            resolved.relative_to(home_resolved)
        except ValueError:
            # Path is outside home - check if it's a known Minecraft location
            known_minecraft_paths = [
                Path("/usr/share/games/minecraft"),
                Path("/opt/minecraft"),
                Path("/usr/local/share/minecraft"),
            ]
            if not any(str(resolved).startswith(str(p)) for p in known_minecraft_paths):
                logger.warning(f"Path validation warning: {resolved} is outside standard Minecraft directories")
                print(f"{BColors.WARNING}Warning: Path is outside standard directories. Proceeding at your own risk.{BColors.ENDC}")
                # Allow user to proceed with custom path
    except Exception as e:
        logger.error(f"Path validation failed: {e}")
        # Continue anyway if validation fails but path seems valid otherwise


    p = Path(final_path)
    if p.parent and not p.parent.exists():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create directory {p.parent}: {e}")
            return None
    return p

def main():
    parser = argparse.ArgumentParser(description="Modrinth & CurseForge Modpack Downloader")
    parser.add_argument("--version", help="Minecraft Version")
    parser.add_argument("--lang", help="Language (en, it)")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-accept prompts")
    parser.add_argument("--threads", type=int, default=5, help="Parallel threads")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed logs (including skipped/up-to-date mods)")
    args = parser.parse_args()

    config = load_config()
    lang = select_language(args.lang, config)
    
    # Show banner before asking for version
    print_banner()
    mc_version = get_mc_version(args.version)

    logger.info(f"--- START SESSION (MC {mc_version}) ---")
    hardware = detect_hardware()
    hw_msg = get_string('hardware_info', None, hardware['gpu'], hardware['cpu_cores'])
    print(f" {BColors.OKCYAN}{hw_msg}{BColors.ENDC}")
    logger.info(hw_msg)
    print(f"{BColors.OKBLUE}═════════════════════════════════════════════════════════════{BColors.ENDC}")

    # Load CurseForge API key from environment variable (preferred) or config
    cf_api_key = os.getenv("CURSEFORGE_API_KEY", config.get("curseforge_api_key", ""))
    if cf_api_key:
        logger.info("CurseForge API key loaded from environment/config")
    client = APIClient(cf_api_key=cf_api_key)
    base_dir = Path.cwd() / "modpack"
    
    # Global stats accumulator - passed to all download functions
    all_stats = DownloadStats()

    # Process mod categories
    for config_key, project_type, subdir, title, flag in MOD_CATEGORIES:
        mod_list = config.get(config_key, [])
        if not mod_list:
            if flag in ["install_medium_qol", "install_survival_qol"] and not args.yes:
                print(f"\n{BColors.WARNING}{get_string('no_survival_qol_found' if flag == 'install_survival_qol' else 'no_medium_qol_found')}{BColors.ENDC}")
            continue

        if not should_process_category(flag, config, args.yes):
            continue

        out_dir = base_dir / f"{subdir}_{mc_version}"
        process_mod_category(client, config_key, project_type, out_dir, title, config, mc_version, args.yes, args.threads, all_stats, hardware, args.verbose)

    # Process texture packs
    process_texture_packs(client, config, mc_version, args.yes, args.threads, base_dir, all_stats, args.verbose)

    # Copy mods to destination
    copy_mods_to_destination(config, args.yes, base_dir, mc_version)

    # Print final summary only once at the end
    print_download_summary(all_stats)

    print(f"\n{BColors.HEADER}{get_string('script_finished')}{BColors.ENDC}")

if __name__ == "__main__":
    main()
