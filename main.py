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

import argparse
import logging
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional

from mc_quarry.api_client import APIClient
from mc_quarry.config_manager import load_config, save_config
from mc_quarry.constants import MOD_CATEGORIES_LIST as MOD_CATEGORIES
from mc_quarry.downloader import filter_mods, read_all_mod_info
from mc_quarry.exceptions import ConfigError
from mc_quarry.processor import _process_mod_wrapper
from mc_quarry.ui_manager import (
    detect_hardware,
    detect_language,
    get_string,
    print_banner,
    print_download_summary,
    print_section_header,
    set_selected_language,
    ui,
)
from mc_quarry.utils import BColors, DownloadStats
from scripts.check_duplicates import check_duplicates

# Setup logging - file only, no console output (use --debug for verbose)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("mc-quarry.log"),
    ],
)
logger = logging.getLogger("mc-quarry")

# Semantic version pattern for Minecraft versions (e.g., 1.21.11, 1.20.1-beta.3)
MC_VERSION_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)?([+-][a-zA-Z0-9.]+)?$")




def select_language(args_lang: Optional[str], config: Dict[str, Any]) -> str:
    """Select language from args, config, or user input.

    Args:
        args_lang: Language from command-line args (may be None)
        config: Current configuration dict with optional 'language' key

    Returns:
        Selected language code ('en' or 'it')
    """
    lang = args_lang or config.get("language") or detect_language()
    if not (args_lang or config.get("language")):
        print(get_string("lang_selection_menu"))
        choice = input(get_string("select_language_prompt")).strip()
        lang = "it" if choice == "2" else "en"
        config["language"] = lang
        save_config(config)
    set_selected_language(lang)
    return lang


def get_mc_version(args_version: Optional[str]) -> str:
    """Get Minecraft version from args or user input with validation.

    Args:
        args_version: Version from command-line args (may be None)

    Returns:
        Validated Minecraft version string

    Raises:
        sys.exit: If version is empty or format is invalid
    """
    version = (
        args_version
        or input(
            f" {BColors.BOLD}{get_string('enter_mc_version')}{BColors.ENDC}"
        ).strip()
    )
    if not version:
        print(get_string("invalid_version"))
        sys.exit(1)

    # Validate version format
    if not MC_VERSION_PATTERN.match(version):
        print(f"{BColors.FAIL}{get_string('invalid_version_format')}{BColors.ENDC}")
        sys.exit(1)

    return version


def should_process_category(
    flag: Optional[str], config: Dict[str, Any], args_yes: bool
) -> bool:
    """Determine if a mod category should be processed based on config and user input.

    Args:
        flag: Configuration flag name (e.g. 'install_light_qol'), or None
        config: Configuration dict with category flags
        args_yes: True if --yes batch mode is active

    Returns:
        True if the category should be processed, False otherwise
    """
    if not flag:
        return True

    if flag == "install_light_qol":
        return config.get(flag, True)

    return config.get(flag, False)


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
    verbose: bool = False,
    provider: str = "modrinth",
) -> None:
    """Process a single mod category (download mods).

    Args:
        client: API client instance
        config_key: Config key for the mod list (e.g. 'core_mods')
        project_type: 'mod' or 'resourcepack'
        out_dir: Output directory for downloaded files
        title: Display title for the section header
        config: Full configuration dict
        mc_version: Target Minecraft version
        args_yes: True if --yes batch mode is active
        threads: Number of parallel download threads
        global_stats: Shared DownloadStats accumulator
        hardware: Hardware info dict for compatibility filtering
        verbose: Show detailed log messages
        provider: 'modrinth' or 'curseforge'
    """
    mod_list = config.get(config_key, [])
    if not mod_list:
        return

    print_section_header(title)
    out_dir.mkdir(parents=True, exist_ok=True)
    installed = read_all_mod_info(out_dir)
    active_list, skipped = filter_mods(mod_list, mc_version, config, hardware)

    # Group skipped mods by reason category
    skipped_by_reason = {"incompatible": [], "hardware": [], "other": []}

    for mod_name, reason in skipped:
        reason_lower = reason.lower()
        if "incompatible" in reason_lower or "incompatible by rule" in reason_lower:
            skipped_by_reason["incompatible"].append((mod_name, reason))
        elif (
            "cores" in reason_lower
            or "gpu" in reason_lower
            or "requires" in reason_lower
        ):
            skipped_by_reason["hardware"].append((mod_name, reason))
        else:
            skipped_by_reason["other"].append((mod_name, reason))

    # Print grouped skip summary
    total_skipped = len(skipped)
    if total_skipped > 0:
        skip_summary = get_string(
            "skipped_mods_summary", None, total_skipped
        )
        print(f"\n{BColors.WARNING}{skip_summary}{BColors.ENDC}")

        if skipped_by_reason["incompatible"]:
            count = len(skipped_by_reason["incompatible"])
            mods = ", ".join([m[0] for m in skipped_by_reason["incompatible"][:5]])
            if count > 5:
                mods += f" (+{count - 5} more)"
            inc_line = get_string(
                "skipped_incompatible", None, count, mods
            )
            print(f"   {BColors.DIM}{inc_line}{BColors.ENDC}")

        if skipped_by_reason["hardware"]:
            count = len(skipped_by_reason["hardware"])
            for mod_name, reason in skipped_by_reason["hardware"]:
                hw_line = get_string(
                    "skipped_hardware", None, count, mod_name, reason
                )
                print(f"   {BColors.DIM}{hw_line}{BColors.ENDC}")

        if skipped_by_reason["other"]:
            count = len(skipped_by_reason["other"])
            mods = ", ".join([m[0] for m in skipped_by_reason["other"][:5]])
            if count > 5:
                mods += f" (+{count - 5} more)"
            print(
                f"   {BColors.DIM}{get_string('skipped_other', None, count, mods)}{BColors.ENDC}"
            )

        # Log detailed skip reasons
        for mod_name, reason in skipped:
            logger.info(f"Skipped: {mod_name} - {reason}")

    # Process downloads
    if active_list:
        ui.set_total(len(active_list))
        ui.set_status(f"Downloading {title}...")

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [
                executor.submit(
                    _process_mod_wrapper,
                    client,
                    m,
                    mc_version,
                    project_type,
                    out_dir,
                    installed,
                    global_stats,
                    provider,
                    verbose,
                )
                for m in active_list
            ]

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
    verbose: bool = False,
) -> Optional[Path]:
    """Process texture packs download and return destination path if copied.

    Args:
        client: API client instance
        config: Full configuration dict
        mc_version: Target Minecraft version
        args_yes: True if --yes batch mode is active
        threads: Number of parallel download threads
        base_dir: Base output directory
        global_stats: Shared DownloadStats accumulator
        verbose: Show detailed log messages

    Returns:
        Destination path if texture packs were copied, None otherwise
    """
    tp_list = config.get("texture_packs", [])
    cf_tp_list = config.get("curseforge_texture_packs", [])
    if not tp_list and not cf_tp_list:
        return None

    do_tp = args_yes
    if not do_tp:
        do_tp = (
            input(
                f"\n{BColors.BOLD}{get_string('download_texture_packs_prompt')}{BColors.ENDC}"
            )
            .lower()
            .startswith(("y", "s"))
        )

    if not do_tp:
        return None

    tp_dir = base_dir / f"texture_packs_{mc_version}"
    tp_dir.mkdir(parents=True, exist_ok=True)
    print_section_header("🎨 TEXTURE PACKS")

    # Read installed texture packs info to avoid re-downloads
    installed_tps = read_all_mod_info(tp_dir)

    # Use global stats
    total_tps = len(tp_list) + len(cf_tp_list)
    ui.set_total(total_tps)
    ui.set_status("Downloading Texture Packs...")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        # Modrinth texture packs
        for tp in tp_list:
            futures.append(
                executor.submit(
                    _process_mod_wrapper,
                    client,
                    tp,
                    mc_version,
                    "resourcepack",
                    tp_dir,
                    installed_tps,
                    global_stats,
                    "modrinth",
                    verbose,
                )
            )

        # CurseForge texture packs
        for tp in cf_tp_list:
            futures.append(
                executor.submit(
                    _process_mod_wrapper,
                    client,
                    tp,
                    mc_version,
                    "resourcepack",
                    tp_dir,
                    installed_tps,
                    global_stats,
                    "curseforge",
                    verbose,
                )
            )

        # Catch exceptions in threads
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                logger.error(f"TP thread execution error: {e}")
                ui.log(f"{BColors.FAIL}❌ TP Thread Error:{BColors.ENDC} {e}")

    ui.finish()

    if args_yes or input(
        f"\n{BColors.BOLD}{get_string('copy_texture_packs_prompt')}{BColors.ENDC}"
    ).lower().strip().startswith(("y", "s")):
        dest_tps = get_destination_path("resourcepacks_folder", False, args_yes, config)
        if dest_tps:
            config["resourcepacks_folder"] = str(dest_tps)
            save_config(config)
            dest_tps.mkdir(parents=True, exist_ok=True)
            print(
                f"{BColors.OKBLUE}{get_string('copying_files_to', None, dest_tps)}{BColors.ENDC}"
            )
            for f in tp_dir.glob("*.zip"):
                shutil.copy(f, dest_tps)
                print(
                    f"  {BColors.OKGREEN}{get_string('copied_file', None, f.name)}{BColors.ENDC}"
                )
            return dest_tps
    return None


def copy_mods_to_destination(
    config: Dict[str, Any], args_yes: bool, base_dir: Path, mc_version: str
) -> None:
    """Copy all downloaded mods to the destination folder.

    Prompts for confirmation unless in batch mode.
    Optionally deletes existing JARs in the destination before copying.

    Args:
        config: Full configuration dict
        args_yes: True if --yes batch mode is active
        base_dir: Base output directory containing mod subdirectories
        mc_version: Target Minecraft version used for subdirectory names
    """
    if not (
        args_yes
        or input(f"\n{BColors.BOLD}{get_string('copy_mods_prompt')}{BColors.ENDC}")
        .lower()
        .strip()
        .startswith(("y", "s"))
    ):
        return

    dest = get_destination_path("mods_folder", True, args_yes, config)
    if not dest:
        return

    config["mods_folder"] = str(dest)
    save_config(config)
    dest.mkdir(parents=True, exist_ok=True)

    if args_yes or input(
        f"{BColors.WARNING}{get_string('delete_existing_files_prompt')}{BColors.ENDC}"
    ).lower().startswith(("y", "s")):
        for f in dest.glob("*.jar"):
            f.unlink()

    # Collect all jars from enabled categories (deduplicate by resolve() to avoid copy duplicates)
    all_jars = []
    seen_paths = set()
    for cfg_key, _, subdir, _, flag, _ in MOD_CATEGORIES:
        if not config.get(cfg_key):
            continue
        if should_process_category(flag, config, args_yes):
            out_dir = base_dir / f"{subdir}_{mc_version}"
            if out_dir.exists():
                for jar in out_dir.glob("*.jar"):
                    resolved = jar.resolve()
                    if resolved not in seen_paths:
                        seen_paths.add(resolved)
                        all_jars.append(jar)

    if all_jars:
        print(
            f"{BColors.OKBLUE}{get_string('copying_files_to', None, dest)}{BColors.ENDC}"
        )
        for f in all_jars:
            shutil.copy(f, dest)
            print(
                f"  {BColors.OKGREEN}{get_string('copied_file', None, f.name)}{BColors.ENDC}"
            )
    else:
        print(f"{BColors.WARNING}{get_string('no_mods_found_to_copy')}{BColors.ENDC}")


def get_destination_path(
    config_key: str, is_mod: bool, args_yes: bool, current_config: Dict[str, Any]
) -> Optional[Path]:
    """
    Get destination path for mods/resourcepacks with security validation.

    Validates that paths are within safe directories to prevent path traversal attacks.
    """
    current_folder = current_config.get(config_key, "")
    home = Path.home()

    default_suggested = ""
    if sys.platform == "win32":
        # Windows
        default_suggested = (
            home
            / "AppData/Roaming/.minecraft"
            / ("mods" if is_mod else "resourcepacks")
        )
    elif sys.platform == "darwin":
        # macOS
        default_suggested = (
            home
            / "Library/Application Support/minecraft"
            / ("mods" if is_mod else "resourcepacks")
        )
    elif sys.platform == "linux":
        # Linux - check for various launcher locations
        flatpak_prism = (
            home
            / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances"
        )
        standard_prism = home / ".local/share/PrismLauncher/instances"
        standard_multimc = home / ".local/share/multimc/instances"
        # Also check for .minecraft in home (most common across all distros)
        vanilla_minecraft = home / ".minecraft"

        if flatpak_prism.exists():
            default_suggested = (
                flatpak_prism
                / "<INSTANCE_NAME>/.minecraft/"
                / ("mods" if is_mod else "resourcepacks")
            )
        elif standard_prism.exists():
            default_suggested = (
                standard_prism
                / "<INSTANCE_NAME>/.minecraft/"
                / ("mods" if is_mod else "resourcepacks")
            )
        elif standard_multimc.exists():
            default_suggested = (
                standard_multimc
                / "<INSTANCE_NAME>/.minecraft/"
                / ("mods" if is_mod else "resourcepacks")
            )
        elif vanilla_minecraft.exists():
            default_suggested = vanilla_minecraft / (
                "mods" if is_mod else "resourcepacks"
            )
        else:
            # Fallback to Flatpak mojang path (least common)
            default_suggested = (
                home
                / ".var/app/com.mojang.Minecraft/data/minecraft/"
                / ("mods" if is_mod else "resourcepacks")
            )
    else:
        # Unknown platform - use generic .minecraft
        default_suggested = (
            home / ".minecraft" / ("mods" if is_mod else "resourcepacks")
        )

    final_path = ""
    if args_yes:
        final_path = current_folder if current_folder else str(default_suggested)
    else:
        config_key_str = (
            "use_configured_path_mods" if is_mod else "use_configured_path_tps"
        )
        if current_folder:
            choice = (
                input(
                    f"{BColors.BOLD}"
                    f"{get_string(config_key_str, None, current_folder)}"
                    f"{BColors.ENDC}"
                )
                .strip()
                .lower()
            )
            if choice == "n":
                suggested = get_string(
                    "suggested_path", None, default_suggested
                )
                print(f"{BColors.OKCYAN}{suggested}{BColors.ENDC}")
                new_path = input(
                    f"{BColors.BOLD}{get_string('enter_path_prompt')}{BColors.ENDC}"
                ).strip()
                final_path = new_path if new_path else str(default_suggested)
            else:
                final_path = current_folder
        else:
            suggested = get_string(
                "suggested_path", None, default_suggested
            )
            print(f"{BColors.OKCYAN}{suggested}{BColors.ENDC}")
            new_path = input(
                f"{BColors.BOLD}{get_string('enter_path_prompt')}{BColors.ENDC}"
            ).strip()
            final_path = new_path if new_path else str(default_suggested)

    if "<INSTANCE_NAME>" in str(final_path):
        if args_yes:
            logger.error("Cannot determine instance name in batch mode.")
            return None
        instance = input(
            f"{BColors.BOLD}{get_string('enter_instance_name')}{BColors.ENDC}"
        ).strip()
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
                logger.warning(
                    f"Path validation warning: {resolved} is outside standard Minecraft directories"
                )
                print(
                    f"{BColors.WARNING}{get_string('warning_path_outside')}{BColors.ENDC}"
                )
                if args_yes:
                    logger.error(f"Path rejected in batch mode: {resolved}")
                    print(
                        f"{BColors.FAIL}{get_string('path_rejected_batch')}{BColors.ENDC}"
                    )
                    return None

                confirm = (
                    input(
                        f"{BColors.WARNING}"
                        "Are you sure you want to use this non-standard path? (y/N): "
                        f"{BColors.ENDC}"
                    )
                    .strip()
                    .lower()
                )
                if not confirm.startswith("y"):
                    print(
                        f"{BColors.FAIL}{get_string('operation_cancelled_security')}{BColors.ENDC}"
                    )
                    return None
    except (ValueError, OSError) as e:
        logger.error(f"Path validation failed: {e}")
        if args_yes:
            return None
        confirm = (
            input(
                f"{BColors.WARNING}Path validation failed. Proceed anyway? (y/N): {BColors.ENDC}"
            )
            .strip()
            .lower()
        )
        if not confirm.startswith("y"):
            return None

    p = Path(final_path)
    if p.parent and not p.parent.exists():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Could not create directory {p.parent}: {e}")
            return None
    return p


def main():
    """Entry point for the MC Quarry modpack downloader.

    Parses command-line arguments, loads configuration, detects hardware,
    processes all configured mod categories and texture packs, copies
    files to the destination, and prints a download summary.
    """
    parser = argparse.ArgumentParser(
        description="Modrinth & CurseForge Modpack Downloader"
    )
    parser.add_argument("--version", help="Minecraft Version")
    parser.add_argument("--lang", help="Language (en, it)")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-accept prompts")
    parser.add_argument("--threads", type=int, default=5, help="Parallel threads")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed logs (including skipped/up-to-date mods)",
    )
    args = parser.parse_args()

    try:
        config = load_config()
    except ConfigError as e:
        print(f"{BColors.FAIL}{e}{BColors.ENDC}")
        sys.exit(1)
    select_language(args.lang, config)

    # Check for duplicates if not in batch mode
    if not args.yes:
        check_duplicates()

    # Show banner before asking for version
    print_banner()
    mc_version = get_mc_version(args.version)

    logger.info(f"--- START SESSION (MC {mc_version}) ---")
    hardware = detect_hardware()
    hw_msg = get_string("hardware_info", None, hardware["gpu"], hardware["cpu_cores"])
    print(f" {BColors.OKCYAN}{hw_msg}{BColors.ENDC}")
    logger.info(hw_msg)
    print(f"{BColors.OKBLUE}{get_string('separator_line')}{BColors.ENDC}")

    # Load CurseForge API key from environment variable (preferred) or config
    cf_api_key = os.getenv("CURSEFORGE_API_KEY", config.get("curseforge_api_key", ""))
    if cf_api_key:
        logger.info("CurseForge API key loaded from environment/config")
    client = APIClient(cf_api_key=cf_api_key)
    base_dir = Path.cwd() / "modpack"

    # Global stats accumulator - passed to all download functions
    all_stats = DownloadStats()

    # Process mod categories
    for config_key, project_type, subdir, title, flag, provider in MOD_CATEGORIES:
        mod_list = config.get(config_key, [])
        if not mod_list:
            continue

        if not should_process_category(flag, config, args.yes):
            continue

        out_dir = base_dir / f"{subdir}_{mc_version}"
        process_mod_category(
            client,
            config_key,
            project_type,
            out_dir,
            title,
            config,
            mc_version,
            args.yes,
            args.threads,
            all_stats,
            hardware,
            args.verbose,
            provider,
        )

    # Process texture packs
    process_texture_packs(
        client,
        config,
        mc_version,
        args.yes,
        args.threads,
        base_dir,
        all_stats,
        args.verbose,
    )

    # Copy mods to destination
    copy_mods_to_destination(config, args.yes, base_dir, mc_version)

    # Print final summary only once at the end
    print_download_summary(all_stats)

    print(f"\n{BColors.HEADER}{get_string('script_finished')}{BColors.ENDC}")


if __name__ == "__main__":
    main()
