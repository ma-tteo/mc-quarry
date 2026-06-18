"""
Shared mod processing logic for both CLI and Web interfaces.

Handles the unified _process_mod_wrapper that dispatches to
Modrinth or CurseForge API based on provider.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .api_client import CF_MOD_CLASS_ID, CF_RESOURCE_PACK_CLASS_ID, APIClient
from .downloader import execute_download
from .utils import BColors, DownloadStats

logger = logging.getLogger("mc-quarry")


_SLUG_STRIP_CHARS = str.maketrans(
    {c: None for c in "'\"`"}
)


def _generate_slug_candidates(name: str) -> List[str]:
    """Generate candidate Modrinth slugs from a mod name.

    The search API is unreliable (returns 0 hits for all queries as of
    mid-2026), so we infer slugs for direct project endpoint lookups.

    Args:
        name: Mod display name (e.g. 'Fabric API', 'FerriteCore')

    Returns:
        List of candidate slugs ordered by likelihood.
    """
    candidates: List[str] = []
    base = name.strip()

    texts = [base]

    paren_match = re.search(r'\(([^)]+)\)', base)
    if paren_match:
        without_parens = re.sub(r'\s*\([^)]*\)\s*', ' ', base).strip()
        if without_parens:
            texts.append(without_parens)
        texts.append(paren_match.group(1))

    for t in texts:
        t = t.translate(_SLUG_STRIP_CHARS)
        t = re.sub(r'[!,\-]+$', '', t)
        if not t:
            continue

        slug1 = re.sub(r'[\s._|/]+', '-', t)
        slug1 = re.sub(r'-+', '-', slug1).strip('-').lower()
        if slug1:
            candidates.append(slug1)

        slug2 = re.sub(r'(?<=[a-z])(?=[A-Z])', '-', t).lower()
        slug2 = re.sub(r'[\s._|/]+', '-', slug2)
        slug2 = re.sub(r'-+', '-', slug2).strip('-')
        if slug2 and slug2 != slug1:
            candidates.append(slug2)

        slug3 = slug1.replace('-', '') if slug1 else ''
        if slug3 and slug3 != slug1:
            candidates.append(slug3)

        parts = slug1.split('-')
        for i in range(1, len(parts)):
            shorter = '-'.join(parts[:-i])
            if shorter and len(shorter) > 2:
                candidates.append(shorter)

        if len(parts) > 1:
            first_word = parts[0]
            if first_word not in candidates and len(first_word) > 2:
                candidates.append(first_word)

    seen = set()
    deduped = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return deduped


def _process_mod_wrapper(
    client: APIClient,
    name: str,
    mc_version: str,
    project_type: str,
    output_dir: Path,
    installed_mods: Dict[str, Any],
    stats: DownloadStats,
    provider: str,
    verbose: bool = False,
    ui_handler: Optional[Any] = None,
) -> None:
    """
    Generic wrapper for processing mods from any provider (Modrinth/CurseForge).

    Handles search, version resolution, and download dispatch.
    Prints messages via UI manager for thread safety.

    Args:
        client: API client instance
        name: Mod name or URL
        mc_version: Target Minecraft version
        project_type: 'mod' or 'resourcepack'
        output_dir: Directory to download into
        installed_mods: Dict of already installed mods (project_id/slug -> info)
        stats: DownloadStats accumulator (thread-safe)
        provider: 'modrinth' or 'curseforge'
        verbose: Show detailed log messages
        ui_handler: Optional UI handler (falls back to global CLI UI)
    """
    from .ui_manager import ui as global_ui

    clean_name = name.strip()
    current_ui = ui_handler if ui_handler else global_ui

    try:
        if provider == "modrinth":
            _handle_modrinth(client, clean_name, project_type, mc_version,
                             output_dir, installed_mods, stats, verbose, current_ui)
        elif provider == "curseforge":
            _handle_curseforge(client, clean_name, project_type, mc_version,
                               output_dir, installed_mods, stats, verbose, current_ui)

    except Exception as e:
        current_ui.log(
            f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC}"
            f" — {BColors.FAIL}❌ System Error{BColors.ENDC}"
        )
        current_ui.log(f"   {BColors.DIM}Detail: {e}{BColors.ENDC}")
        stats.add_failed(clean_name, str(e))
        logger.exception(f"{provider} processing error for {clean_name}")
        current_ui.update_progress()


def _handle_modrinth(
    client: APIClient,
    clean_name: str,
    project_type: str,
    mc_version: str,
    output_dir: Path,
    installed_mods: Dict[str, Any],
    stats: DownloadStats,
    verbose: bool,
    ui: Any,
) -> None:
    """
    Handle a Modrinth mod download.

    Searches by URL slug or name, resolves the latest compatible version,
    and dispatches to execute_download.

    Args:
        client: API client instance with Modrinth methods
        clean_name: Mod name or Modrinth URL
        project_type: 'mod' or 'resourcepack'
        mc_version: Target Minecraft version
        output_dir: Directory to download into
        installed_mods: Dict of already installed mods
        stats: DownloadStats accumulator (thread-safe)
        verbose: Show detailed log messages
        ui: UI handler for progress and log output
    """
    project = None

    if "modrinth.com" in clean_name:
        slug = clean_name.rstrip("/").split("/")[-1]
        project_data = client.get_modrinth_project(slug)
        if project_data:
            project = {
                "project_id": project_data["id"],
                "slug": project_data["slug"],
                "title": project_data["title"],
            }

    if not project and "modrinth.com" not in clean_name:
        # Direct slug lookup (search API is unreliable — returns 0 hits
        # for all queries as of mid-2026)
        for slug in _generate_slug_candidates(clean_name):
            project_data = client.get_modrinth_project(slug)
            if project_data:
                project = {
                    "project_id": project_data["id"],
                    "slug": project_data["slug"],
                    "title": project_data["title"],
                }
                break

    if not project:
        # Fall back to search API in case it recovers
        search_results = client.search_modrinth(clean_name, project_type)
        if search_results and "hits" in search_results and search_results["hits"]:
            hits = search_results["hits"]
            name_low = clean_name.lower()

            for h in hits:
                if (
                    h.get("title", "").lower() == name_low
                    or h.get("slug", "").lower() == name_low
                ):
                    project = h
                    break

            if not project and hits:
                first_hit = hits[0]
                first_title = first_hit.get("title", "").lower()
                if name_low in first_title or first_title in name_low:
                    project = first_hit

    if not project:
        if verbose:
            ui.log(
                f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC}"
                f" — {BColors.FAIL}❌ Not Found{BColors.ENDC} (Modrinth)"
            )
        stats.add_not_found(clean_name)
        ui.update_progress()
        return

    title = project.get("title") or project.get("name")
    loader = "fabric" if project_type == "mod" else None
    pid = project["project_id"] if "project_id" in project else project["id"]
    latest_version = client.find_modrinth_version(pid, mc_version, loader=loader)

    if not latest_version and project_type == "resourcepack":
        latest_version = client.find_modrinth_version(
            pid, mc_version, loader=None, force_latest=True
        )

    if not latest_version:
        if verbose:
            ui.log(
                f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{title}{BColors.ENDC}"
                f" — {BColors.FAIL}❌ No compatible version{BColors.ENDC} (Modrinth)"
            )
        stats.add_failed(title, "No compatible version found on Modrinth")
        ui.update_progress()
        return

    file_info = client.pick_file_from_version(latest_version)
    if not file_info:
        ui.log(
            f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{title}{BColors.ENDC}"
            f" — {BColors.FAIL}❌ No file{BColors.ENDC}"
        )
        stats.add_failed(title, "No file to download")
        ui.update_progress()
        return

    project_url = f"https://modrinth.com/{project_type}/{project['slug']}"
    ui.set_status(f"Processing {clean_name}...")
    execute_download(
        clean_name, pid, project["slug"],
        latest_version["id"], latest_version["name"],
        file_info["filename"], file_info["url"],
        "modrinth", output_dir, installed_mods, stats,
        lambda msg: ui.log(msg), project_url, verbose,
    )
    ui.update_progress()


def _handle_curseforge(
    client: APIClient,
    clean_name: str,
    project_type: str,
    mc_version: str,
    output_dir: Path,
    installed_mods: Dict[str, Any],
    stats: DownloadStats,
    verbose: bool,
    ui: Any,
) -> None:
    """
    Handle a CurseForge mod download.

    Validates API key, searches by name or URL, resolves the latest
    compatible file, and dispatches to execute_download.

    Args:
        client: API client instance with CurseForge methods
        clean_name: Mod name or CurseForge URL
        project_type: 'mod' or 'resourcepack'
        mc_version: Target Minecraft version
        output_dir: Directory to download into
        installed_mods: Dict of already installed mods
        stats: DownloadStats accumulator (thread-safe)
        verbose: Show detailed log messages
        ui: UI handler for progress and log output
    """
    if not client.cf_api_key:
        ui.log(
            f"{BColors.BOLD}{clean_name}{BColors.ENDC}:"
            f" {BColors.FAIL}❌ CF API Key missing{BColors.ENDC}"
        )
        stats.add_not_found(clean_name)
        ui.update_progress()
        return

    ui.set_status(f"Searching CF: {clean_name}...")
    if "curseforge.com" in clean_name:
        clean_name = clean_name.rstrip("/").split("/")[-1]

    cf_class_id = CF_MOD_CLASS_ID if project_type == "mod" else CF_RESOURCE_PACK_CLASS_ID
    cf_project = client.search_curseforge(clean_name, class_id=cf_class_id)

    if not cf_project:
        if verbose:
            ui.log(
                f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{clean_name}{BColors.ENDC}"
                f" — {BColors.FAIL}❌ Not Found{BColors.ENDC} (CurseForge)"
            )
        stats.add_not_found(clean_name)
        ui.update_progress()
        return

    cf_loader = 4 if project_type == "mod" else 0
    cf_file = client.get_latest_file_cf(
        cf_project["id"], mc_version, mod_loader_type=cf_loader
    )

    if not cf_file and project_type == "resourcepack":
        cf_file = client.get_latest_file_cf(
            cf_project["id"], mc_version,
            mod_loader_type=cf_loader, force_latest=True
        )

    if not cf_file:
        if verbose:
            ui.log(
                f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{cf_project['name']}{BColors.ENDC}"
                f" — {BColors.FAIL}❌ No compatible version{BColors.ENDC} (CurseForge)"
            )
        stats.add_failed(cf_project["name"], "No compatible version on CF")
        ui.update_progress()
        return

    project_url = cf_project.get("links", {}).get(
        "websiteUrl",
        f"https://www.curseforge.com/minecraft/"
        f"{'mc-mods' if project_type == 'mod' else 'texture-packs'}/{cf_project['slug']}",
    )

    if not cf_file.get("downloadUrl"):
        ui.log(
            f"✨ {BColors.BOLD}{BColors.BRIGHT_WHITE}{cf_project['name']}{BColors.ENDC}"
            f" — {BColors.WARNING}⚠️ API Download Disabled{BColors.ENDC}"
        )
        ui.log(f"   {BColors.DIM}Please download manually:"
               f" {BColors.UNDERLINE}{project_url}{BColors.ENDC}")
        stats.add_failed(cf_project["name"], "API download disabled by author")
        ui.update_progress()
        return

    execute_download(
        clean_name, str(cf_project["id"]), cf_project["slug"],
        str(cf_file["id"]), cf_file.get("displayName", str(cf_file["id"])),
        cf_file["fileName"], cf_file["downloadUrl"],
        "curseforge", output_dir, installed_mods, stats,
        lambda msg: ui.log(msg), project_url, verbose,
    )
    ui.update_progress()
