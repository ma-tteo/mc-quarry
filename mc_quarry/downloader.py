import json
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
from packaging import version as pkg_version

from .ui_manager import detect_hardware
from .utils import BColors, DownloadStats, sanitize_filename

logger = logging.getLogger("mc-quarry")


def download_file(url: str, dest_path: Path, max_retries: int = 4) -> bool:
    """Download a file with retry logic."""
    headers = {"User-Agent": "modpack-downloader/3.0"}
    for attempt in range(1, max_retries + 1):
        try:
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                with tmp_path.open("wb") as out:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            out.write(chunk)

            # Atomic swap (move handles cross-partition issues better than replace)
            if tmp_path.exists():
                shutil.move(str(tmp_path), str(dest_path))
            return True
        except requests.RequestException as e:
            logger.warning(f"Download attempt {attempt} failed for {url}: {e}")
            if attempt < max_retries:
                time.sleep(1 * attempt)
    logger.error(f"Download failed after {max_retries} attempts: {url}")
    return False


def write_mod_info(
    jar_path: Path,
    project_id: str,
    project_slug: str,
    version_id: str,
    version_name: str,
    filename: str,
    provider: str = "modrinth",
):
    """Save .modinfo JSON metadata file."""
    info_path = jar_path.with_suffix(jar_path.suffix + ".modinfo")
    metadata = {
        "project_id": str(project_id),
        "project_slug": project_slug,
        "version_id": str(version_id),
        "version_name": version_name,
        "filename": sanitize_filename(filename),
        "provider": provider,
    }
    try:
        with info_path.open("w") as f:
            json.dump(metadata, f, indent=4)
    except OSError as e:
        logger.error(f"Error writing .modinfo for {filename}: {e}")


def read_all_mod_info(directory: Path) -> Dict[str, Dict[str, Any]]:
    """Read all .modinfo files from directory and build index."""
    installed = {}
    for info_file in directory.glob("*.modinfo"):
        try:
            with info_file.open("r") as f:
                data = json.load(f)
                if "project_id" in data and data.get("filename"):
                    jar_path = directory / data["filename"]
                    if jar_path.is_file():
                        installed[data["project_id"]] = data
                        if "project_slug" in data:
                            installed[data["project_slug"]] = data
                    else:
                        # Orphaned modinfo - jar file was deleted
                        info_file.unlink()
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Corrupted modinfo file {info_file}: {e}")
            info_file.unlink()
        except Exception as e:
            logger.error(f"Unexpected error reading {info_file}: {e}")
    return installed


def compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings. Returns 1, -1, or 0."""
    try:
        ver1, ver2 = pkg_version.parse(v1), pkg_version.parse(v2)
        if ver1 > ver2:
            return 1
        if ver1 < ver2:
            return -1
        return 0
    except Exception as e:
        logger.debug(f"Version parse fallback for {v1} / {v2}: {e}")
        # Fallback to integer tuple comparison if packaging.version fails
        try:

            def to_numeric_tuple(v: str) -> Tuple:
                """Convert version string to numeric tuple for comparison."""
                clean_v = re.sub(r"[^0-9.]", "", v.split("-")[0].split("+")[0])
                return tuple(int(x) for x in clean_v.split(".") if x.isdigit())

            t1, t2 = to_numeric_tuple(v1), to_numeric_tuple(v2)
            if t1 > t2:
                return 1
            if t1 < t2:
                return -1
            return 0
        except Exception as e2:
            logger.debug(f"Version numeric fallback for {v1} / {v2}: {e2}")
            # Last resort string comparison
            if v1 > v2:
                return 1
            if v1 < v2:
                return -1
            return 0


def check_incompatibility(
    mod_name: str, mc_version: str, config: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Check if a mod is incompatible with the current Minecraft version."""
    incompatible_rules = config.get("incompatible_mods", {})
    for rule_mod, invalid_versions in incompatible_rules.items():
        if rule_mod.lower() == mod_name.lower():
            for ver_rule in invalid_versions:
                if ver_rule.startswith("<"):
                    # <1.20 means the mod only works below 1.20 — skip if mc_version >= threshold
                    if compare_versions(mc_version, ver_rule[1:]) >= 0:
                        return (
                            True,
                            f"Skipping '{mod_name}' on {mc_version} (incompatible by rule: {ver_rule})",
                        )
                elif ver_rule.startswith(">"):
                    if compare_versions(mc_version, ver_rule[1:]) > 0:
                        return (
                            True,
                            f"Skipping '{mod_name}' on {mc_version} (incompatible by rule: {ver_rule})",
                        )
                elif ver_rule.endswith("+"):
                    if compare_versions(mc_version, ver_rule[:-1]) >= 0:
                        return (
                            True,
                            f"Skipping '{mod_name}' on {mc_version} (incompatible by rule: {ver_rule})",
                        )
                elif ver_rule == mc_version:
                    return (
                        True,
                        f"Skipping '{mod_name}' on {mc_version} (incompatible by rule: {ver_rule})",
                    )
    return False, None


def filter_mods(
    mod_list: List[str],
    mc_version: str,
    config: Dict[str, Any],
    hardware: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str]]:
    """Filter mods based on compatibility rules and hardware requirements."""
    eligible_mods = []
    skipped_reasons = []

    if hardware is None:
        hardware = detect_hardware()

    hardware_rules = config.get("requirements", {})

    for mod in mod_list:
        is_inc, reason = check_incompatibility(mod, mc_version, config)
        if is_inc:
            skipped_reasons.append((mod, reason))
            continue

        if mod in hardware_rules:
            req = hardware_rules[mod]
            if "gpu" in req and hardware["gpu"] != req["gpu"]:
                skipped_reasons.append(
                    (mod, f"Requires {req['gpu']} GPU, found {hardware['gpu']}")
                )
                continue
            if "min_cpu_cores" in req and hardware["cpu_cores"] < req["min_cpu_cores"]:
                skipped_reasons.append(
                    (
                        mod,
                        f"Requires {req['min_cpu_cores']} cores, found {hardware['cpu_cores']}",
                    )
                )
                continue
        eligible_mods.append(mod)

    final_mods = []
    conflict_rules = config.get("conflicts", {})
    current_final_names = set()

    for mod in eligible_mods:
        skip_mod = False
        mod_low = mod.lower()
        for primary_mod, opposites in conflict_rules.items():
            if primary_mod.lower() in current_final_names and any(opt.lower() in mod_low for opt in opposites):
                    skipped_reasons.append((mod, f"Conflicts with '{primary_mod}'"))
                    skip_mod = True
                    break
        if not skip_mod:
            final_mods.append(mod)
            current_final_names.add(mod_low)

    return final_mods, skipped_reasons


def execute_download(
    display_name: str,
    project_id: str,
    project_slug: str,
    version_id: str,
    version_name: str,
    filename: str,
    url: str,
    provider: str,
    output_dir: Path,
    installed_mods: Dict[str, Any],
    stats: DownloadStats,
    log_func: Callable[[str], None],
    project_url: str = "",
    verbose: bool = False,
):
    """Execute download logic for a single mod/resource pack."""
    file_name = sanitize_filename(filename)
    dest_path = output_dir / file_name

    installed_data = installed_mods.get(project_id) or installed_mods.get(project_slug)
    needs_download = True

    info_parts = [f"📦 {version_name}", f"🌐 {provider.capitalize()}"]
    if project_url:
        info_parts.append(f"🔗 {BColors.UNDERLINE}{project_url}{BColors.ENDC}")
    details = f"   {BColors.DIM}{' | '.join(info_parts)}{BColors.ENDC}"

    # Case 1: Mod already installed - check if up-to-date
    if installed_data:
        if (
            str(installed_data.get("version_id")) == str(version_id)
            and installed_data.get("provider") == provider
        ):
            # Already up-to-date
            if verbose:
                log_func(
                    f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{display_name}{BColors.ENDC} — {BColors.OKGREEN}✅ Up to date{BColors.ENDC}"
                )
                log_func(details)
            stats.add_skipped_up_to_date()
            needs_download = False
        else:
            # Update available - remove old version
            old_ver = installed_data.get("version_name", "?")
            if verbose:
                log_func(
                    f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{display_name}{BColors.ENDC} — {BColors.OKCYAN}🔄 Update{BColors.ENDC} ({old_ver} → {version_name})"
                )
                log_func(details)
            stats.add_updated()
            old_path = output_dir / installed_data["filename"]
            if old_path.exists():
                try:
                    old_path.unlink()
                    info_path = old_path.with_suffix(old_path.suffix + ".modinfo")
                    if info_path.exists():
                        info_path.unlink()
                except Exception as e:
                    logger.error(f"Error removing old file {old_path}: {e}")

    # Case 2: File exists but no metadata - index it
    if needs_download:
        if dest_path.exists() and not installed_data:
            if verbose:
                log_func(
                    f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{display_name}{BColors.ENDC} — {BColors.WARNING}⚠️ Indexed{BColors.ENDC}"
                )
                log_func(details)
            write_mod_info(
                dest_path,
                project_id,
                project_slug,
                version_id,
                version_name,
                file_name,
                provider,
            )
            stats.add_installed()
        else:
            # Case 3: Download new file
            if download_file(url, dest_path):
                if verbose:
                    log_func(
                        f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{display_name}{BColors.ENDC} — {BColors.OKGREEN}📥 Downloaded{BColors.ENDC}"
                    )
                    log_func(details)
                write_mod_info(
                    dest_path,
                    project_id,
                    project_slug,
                    version_id,
                    version_name,
                    file_name,
                    provider,
                )
                if not installed_data:
                    stats.add_installed()
            else:
                # Always log failures, even if not verbose
                log_func(
                    f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{display_name}{BColors.ENDC} — {BColors.FAIL}❌ Failed{BColors.ENDC}"
                )
                log_func(details)
                stats.add_failed(display_name, f"Download failed from {provider}")
