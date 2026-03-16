#!/usr/bin/env python3
import sys
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
    get_string, print_banner, print_section_header, 
    detect_language, set_selected_language, detect_hardware
)
from mc_quarry.api_client import APIClient
from mc_quarry.downloader import (
    read_all_mod_info, filter_mods, execute_download
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("mc-quarry.log"),
        # logging.StreamHandler() # Enable for debug
    ]
)
logger = logging.getLogger("mc-quarry")

print_lock = threading.Lock()

def process_modrinth_wrapper(client: APIClient, name: str, mc_version: str, project_type: str, output_dir: Path, installed_mods: Dict[str, Any], stats: DownloadStats):
    clean_name = name.strip()
    logs = []
    def log(msg): logs.append(msg)

    try:
        project = None
        if "modrinth.com" in clean_name:
            slug = clean_name.rstrip('/').split('/')[-1]
            project_data = client.get_modrinth_project(slug)
            if project_data:
                project = {"project_id": project_data["id"], "slug": project_data["slug"], "title": project_data["title"]}

        if not project:
            search_results = client.search_modrinth(clean_name, project_type)
            if search_results and "hits" in search_results and search_results["hits"]:
                hits = search_results["hits"]
                name_low = clean_name.lower()
                for h in hits:
                    if h.get("title", "").lower() == name_low or h.get("slug", "").lower() == name_low:
                        project = h
                        break
                if not project: project = hits[0]
        
        if not project:
            log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC} — {BColors.FAIL}❌ Not Found{BColors.ENDC}")
            log(f"   {BColors.DIM}Provider: Modrinth | Query: {clean_name}{BColors.ENDC}")
            stats.add_not_found(clean_name)
        else:
            title = project.get("title") or project.get("name")
            loader = 'fabric' if project_type == 'mod' else None
            pid = project["project_id"] if "project_id" in project else project["id"]
            latest_version = client.find_modrinth_version(pid, mc_version, loader=loader)
            
            if not latest_version and project_type == 'resourcepack':
                 latest_version = client.find_modrinth_version(pid, mc_version, loader=None, force_latest=True)

            if not latest_version:
                log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{title}{BColors.ENDC} — {BColors.FAIL}❌ No compatible version{BColors.ENDC}")
                log(f"   {BColors.DIM}Provider: Modrinth | MC: {mc_version}{BColors.ENDC}")
                stats.add_failed(title, "No compatible version found")
            else:
                file_info = client.pick_file_from_version(latest_version)
                if not file_info:
                    log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{title}{BColors.ENDC} — {BColors.FAIL}❌ No file{BColors.ENDC}")
                    log(f"   {BColors.DIM}Provider: Modrinth | Version: {latest_version['name']}{BColors.ENDC}")
                    stats.add_failed(title, "No file to download")
                else:
                    project_url = f"https://modrinth.com/{project_type}/{project['slug']}"
                    execute_download(clean_name, pid, project["slug"], 
                                     latest_version["id"], latest_version["name"], file_info["filename"], file_info["url"], 
                                     "modrinth", output_dir, installed_mods, stats, log, project_url)
    except Exception as e:
        log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC} — {BColors.FAIL}❌ System Error{BColors.ENDC}")
        log(f"   {BColors.DIM}Detail: {e}{BColors.ENDC}")
        stats.add_failed(clean_name, str(e))
        logger.exception(f"Modrinth processing error for {clean_name}")
    
    with print_lock:
        if logs: print("\n".join(logs))

def process_curseforge_wrapper(client: APIClient, name: str, mc_version: str, project_type: str, output_dir: Path, installed_mods: Dict[str, Any], stats: DownloadStats):
    clean_name = name.strip()
    if "curseforge.com" in clean_name:
        clean_name = clean_name.rstrip('/').split('/')[-1]

    logs = []
    def log(msg): logs.append(msg)

    if not client.cf_api_key:
        log(f"{BColors.BOLD}{clean_name}{BColors.ENDC}: {BColors.FAIL}❌ CF API Key missing{BColors.ENDC}")
        stats.add_not_found(clean_name)
    else:
        try:
            cf_class_id = 6 if project_type == 'mod' else 12
            cf_project = client.search_curseforge(clean_name, class_id=cf_class_id)
            
            if not cf_project:
                log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC} — {BColors.FAIL}❌ Not Found{BColors.ENDC}")
                log(f"   {BColors.DIM}Provider: CurseForge | Query: {clean_name}{BColors.ENDC}")
                stats.add_not_found(clean_name)
            else:
                cf_loader = 4 if project_type == 'mod' else 0
                cf_file = client.get_latest_file_cf(cf_project['id'], mc_version, mod_loader_type=cf_loader)
                
                if not cf_file:
                    log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{cf_project['name']}{BColors.ENDC} — {BColors.FAIL}❌ No compatible version{BColors.ENDC}")
                    log(f"   {BColors.DIM}Provider: CurseForge | MC: {mc_version}{BColors.ENDC}")
                    stats.add_failed(cf_project['name'], "No compatible version on CF")
                else:
                    project_url = cf_project.get('links', {}).get('websiteUrl', f"https://www.curseforge.com/minecraft/{'mc-mods' if project_type=='mod' else 'texture-packs'}/{cf_project['slug']}")
                    execute_download(clean_name, str(cf_project['id']), cf_project['slug'], str(cf_file['id']), 
                                     cf_file.get('displayName', str(cf_file['id'])), cf_file['fileName'], 
                                     cf_file['downloadUrl'], "curseforge", output_dir, installed_mods, stats, log, project_url)
        except Exception as e:
            log(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC} — {BColors.FAIL}❌ System Error{BColors.ENDC}")
            log(f"   {BColors.DIM}Detail: {e}{BColors.ENDC}")
            stats.add_failed(clean_name, str(e))
            logger.exception(f"CurseForge processing error for {clean_name}")
    
    with print_lock:
        if logs: print("\n".join(logs))

def get_destination_path(config_key: str, is_mod: bool, args_yes: bool, current_config: Dict[str, Any]) -> Optional[Path]:
    current_folder = current_config.get(config_key, "")
    home = Path.home()
    
    default_suggested = ""
    if sys.platform == "win32":
        default_suggested = home / "AppData/Roaming/.minecraft" / ("mods" if is_mod else "resourcepacks")
    elif sys.platform == "linux":
        flatpak_prism = home / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances"
        standard_prism = home / ".local/share/PrismLauncher/instances"
        standard_multimc = home / ".local/share/multimc/instances"
        
        if flatpak_prism.exists():
            default_suggested = flatpak_prism / "<INSTANCE_NAME>/.minecraft/" / ("mods" if is_mod else "resourcepacks")
        elif standard_prism.exists():
            default_suggested = standard_prism / "<INSTANCE_NAME>/.minecraft/" / ("mods" if is_mod else "resourcepacks")
        elif standard_multimc.exists():
            default_suggested = standard_multimc / "<INSTANCE_NAME>/.minecraft/" / ("mods" if is_mod else "resourcepacks")
        else:
            default_suggested = home / ".var/app/com.mojang.Minecraft/data/minecraft/" / ("mods" if is_mod else "resourcepacks")

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
    
    if not final_path: return None
    
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
    args = parser.parse_args()

    config = load_config()

    # Language selection
    lang = args.lang or config.get("language") or detect_language()
    if not (args.lang or config.get("language")):
        print("1. English\n2. Italiano")
        choice = input("Select Language: ").strip()
        lang = 'it' if choice == '2' else 'en'
        config["language"] = lang
        save_config(config)
    set_selected_language(lang)

    print_banner()
    mc_version = args.version or input(f" {BColors.BOLD}{get_string('enter_mc_version')}{BColors.ENDC}").strip()
    if not mc_version:
        print(get_string('invalid_version'))
        sys.exit(1)

    logger.info(f"--- START SESSION (MC {mc_version}) ---")
    hardware = detect_hardware()
    hw_msg = get_string('hardware_info', None, hardware['gpu'], hardware['cpu_cores'])
    print(f" {BColors.OKCYAN}{hw_msg}{BColors.ENDC}")
    logger.info(hw_msg)
    print(f"{BColors.OKBLUE}═════════════════════════════════════════════════════════════{BColors.ENDC}")

    client = APIClient(cf_api_key=config.get("curseforge_api_key", ""))
    stats = DownloadStats()
    base_dir = Path.cwd() / "modpack"
    
    # Process Categories
    categories = [
        ("mods", "mod", base_dir / f"mods_core_{mc_version}", "💎 CORE MODS", None),
        ("curseforge_mods", "mod_cf", base_dir / f"mods_core_{mc_version}", "🔥 CURSEFORGE MODS", None),
        ("light_qol_mods", "mod", base_dir / f"mods_light_qol_{mc_version}", "💡 LIGHT QOL", "install_light_qol"),
        ("medium_qol_mods", "mod", base_dir / f"mods_medium_qol_{mc_version}", "🎭 MEDIUM QOL", "install_medium_qol"),
        ("survival_qol_mods", "mod", base_dir / f"mods_survival_{mc_version}", "⚔️ SURVIVAL QOL", "install_survival_qol")
    ]

    for config_key, p_type, out_dir, title, flag in categories:
        mod_list = config.get(config_key, [])
        if not mod_list: 
            if flag in ["install_medium_qol", "install_survival_qol"] and not args.yes:
                 print(f"\n{BColors.WARNING}{get_string('no_survival_qol_found' if flag == 'install_survival_qol' else 'no_medium_qol_found')}{BColors.ENDC}")
            continue
        
        # Decide if we should process this category
        should_process = True
        if flag:
            enabled_in_config = config.get(flag, False) if flag != "install_light_qol" else config.get(flag, True)
            if flag == "install_light_qol":
                should_process = enabled_in_config
            else:
                # Per Medium e Survival: in batch mode usiamo il config, in interattivo chiediamo sempre
                if args.yes:
                    should_process = enabled_in_config
                else:
                    prompt_key = 'install_medium_qol_prompt' if flag == "install_medium_qol" else 'install_survival_qol_prompt'
                    should_process = input(f"\n{BColors.BOLD}{get_string(prompt_key)}{BColors.ENDC}").lower().startswith(('y', 's'))

        if not should_process:
            continue

        print_section_header(title)
        out_dir.mkdir(parents=True, exist_ok=True)
        installed = read_all_mod_info(out_dir)
        active_list, skipped = filter_mods(mod_list, mc_version, config)
        
        for mod_name, reason in skipped:
            print(f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{mod_name}{BColors.ENDC} — {BColors.WARNING}⚠️ Skipped{BColors.ENDC}")
            print(f"   {BColors.DIM}Reason: {reason}{BColors.ENDC}")
            logger.info(f"Skipped: {mod_name} - {reason}")

        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            if p_type == "mod_cf":
                futures = [executor.submit(process_curseforge_wrapper, client, m, mc_version, "mod", out_dir, installed, stats) for m in active_list]
            else:
                futures = [executor.submit(process_modrinth_wrapper, client, m, mc_version, p_type, out_dir, installed, stats) for m in active_list]
            for _ in as_completed(futures): pass

    stats.print_summary()

    # --- TEXTURE PACKS ---
    tp_list = config.get("texture_packs", [])
    if tp_list:
        do_tp = args.yes
        if not do_tp:
            do_tp = input(f"\n{BColors.BOLD}{get_string('download_texture_packs_prompt')}{BColors.ENDC}").lower().startswith(('y', 's'))

        if do_tp:
            tp_dir = base_dir / f"texture_packs_{mc_version}"
            tp_dir.mkdir(parents=True, exist_ok=True)
            print_section_header("🎨 TEXTURE PACKS")
            
            tp_stats = DownloadStats()
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = [executor.submit(process_modrinth_wrapper, client, tp, mc_version, 'resourcepack', tp_dir, {}, tp_stats) for tp in tp_list]
                for f in as_completed(futures): pass
            
            tp_stats.print_summary()
                
            if args.yes or input(f"\n{BColors.BOLD}{get_string('copy_texture_packs_prompt')}{BColors.ENDC}").lower().strip().startswith(('y', 's')):
                dest_tps = get_destination_path("resourcepacks_folder", False, args.yes, config)
                if dest_tps:
                    config["resourcepacks_folder"] = str(dest_tps)
                    save_config(config)
                    dest_tps.mkdir(parents=True, exist_ok=True)
                    print(f"{BColors.OKBLUE}{get_string('copying_files_to', None, dest_tps)}{BColors.ENDC}")
                    for f in tp_dir.glob("*.zip"):
                        shutil.copy(f, dest_tps)
                        print(f"  {BColors.OKGREEN}{get_string('copied_file', None, f.name)}{BColors.ENDC}")

    # Final Copy Logic (All Mods)
    if args.yes or input(f"\n{BColors.BOLD}{get_string('copy_mods_prompt')}{BColors.ENDC}").lower().strip().startswith(('y', 's')):
        dest = get_destination_path("mods_folder", True, args.yes, config)
        if dest:
            config["mods_folder"] = str(dest)
            save_config(config)
            dest.mkdir(parents=True, exist_ok=True)
            if args.yes or input(f"{BColors.WARNING}{get_string('delete_existing_files_prompt')}{BColors.ENDC}").lower().startswith(('y', 's')):
                for f in dest.glob("*.jar"): f.unlink()
            
            # Collect and copy all jars from all enabled categories
            all_jars = []
            for cfg_key, _, out_dir, _, flag in categories:
                # Check if this category was supposed to be processed
                if not config.get(cfg_key): continue
                
                should_have_processed = True
                if flag:
                    should_have_processed = config.get(flag, False) if flag != "install_light_qol" else config.get(flag, True)
                
                if should_have_processed and out_dir.exists():
                    all_jars.extend(out_dir.glob("*.jar"))
            
            if all_jars:
                print(f"{BColors.OKBLUE}{get_string('copying_files_to', None, dest)}{BColors.ENDC}")
                for f in all_jars:
                    shutil.copy(f, dest)
                    print(f"  {BColors.OKGREEN}{get_string('copied_file', None, f.name)}{BColors.ENDC}")
            else:
                print(f"{BColors.WARNING}No mods found to copy.{BColors.ENDC}")

    print(f"\n{BColors.HEADER}{get_string('script_finished')}{BColors.ENDC}")

if __name__ == "__main__":
    main()