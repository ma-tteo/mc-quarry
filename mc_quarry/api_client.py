import json
import time
import logging
import random
import requests
from typing import Dict, Any, List, Optional, Union
from .utils import BColors

# Modrinth API base URL
BASE_API = "https://api.modrinth.com"

# CurseForge API base URL and constants
CF_API_BASE = "https://api.curseforge.com"
CF_GAME_ID = 432  # Minecraft
CF_MOD_CLASS_ID = 6  # Mod category
CF_RESOURCE_PACK_CLASS_ID = 12  # Texture pack category
CF_SORT_FIELD_RELEVANCE = 2  # Sort by relevance

# HTTP headers for API requests
HEADERS = {"User-Agent": "modpack-downloader/3.0"}

logger = logging.getLogger("mc-quarry")


class APIClient:
    def __init__(self, cf_api_key: str = ""):
        self.cf_api_key = cf_api_key
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        # Manual cache for version lookups (avoid lru_cache on instance methods)
        self._version_cache: Dict[str, Optional[Dict[str, Any]]] = {}

    def get_json(self, url: str, max_retries: int = 4, backoff: float = 1.5, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[Union[Dict[str, Any], List[Any]]]:
        """
        Execute GET request with exponential backoff retry logic.
        
        Args:
            url: API endpoint URL
            max_retries: Maximum number of retry attempts
            backoff: Base backoff time in seconds
            params: Optional query parameters
            headers: Optional request headers
            
        Returns:
            Parsed JSON response or None on failure
        """
        current_headers = headers if headers else {}
        for attempt in range(1, max_retries + 1):
            try:
                r = self.session.get(url, params=params, headers=current_headers, timeout=20)
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 404:
                    return None
                elif r.status_code == 429:
                    # Rate limited - use server-specified retry time or exponential backoff
                    wait_time = int(r.headers.get("Retry-After", backoff * (2 ** (attempt - 1))))
                    logger.warning(f"Rate limited (429) on {url}. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                elif 400 <= r.status_code < 500:
                    logger.error(f"Client Error {r.status_code} for {url}. No retry.")
                    return None
                else:
                    logger.debug(f"API Error {r.status_code} for {url} (Attempt {attempt})")
            except requests.RequestException as e:
                logger.debug(f"Network Error {e} for {url} (Attempt {attempt})")

            # Exponential backoff with jitter to avoid thundering herd
            wait_time = min(backoff * (2 ** (attempt - 1)) + random.uniform(0, 1), 60)
            time.sleep(wait_time)
        return None

    # --- Modrinth API ---

    def search_modrinth(self, name: str, project_type: str = 'mod', limit: int = 5) -> Optional[Dict[str, Any]]:
        """Search for projects on Modrinth."""
        facets = [[f"project_type:{project_type}"]]
        if project_type == 'mod':
            facets.append(["categories:fabric"])
        
        # Modrinth API expects facets as a JSON array string
        params = {
            "query": name,
            "index": "relevance", 
            "limit": limit,
            "facets": json.dumps(facets)
        }
        return self.get_json(f"{BASE_API}/v2/search", params=params)

    def get_modrinth_project(self, slug: str) -> Optional[Dict[str, Any]]:
        return self.get_json(f"{BASE_API}/v2/project/{slug}")

    def find_modrinth_version(self, project_id: str, mc_version: str, loader: str = 'fabric', force_latest: bool = False) -> Optional[Dict[str, Any]]:
        """
        Find the latest compatible version for a project.
        Results are cached to avoid repeated API calls for the same project/version.
        """
        # Create cache key from parameters
        cache_key = f"{project_id}:{mc_version}:{loader}:{force_latest}"
        
        # Check cache first
        if cache_key in self._version_cache:
            logger.debug(f"Cache hit for {cache_key}")
            return self._version_cache[cache_key]
        
        # Build query parameters
        params = {}
        
        # Only filter by version if not force_latest
        if not force_latest:
            params["game_versions"] = json.dumps([mc_version])
        
        if loader:
            params["loaders"] = json.dumps([loader])
        
        logger.debug(f"Fetching versions for {project_id} with params: {params}")
        
        # Fetch versions
        versions = self.get_json(f"{BASE_API}/v2/project/{project_id}/version", params=params)
        
        if not versions or not isinstance(versions, list):
            logger.warning(f"No versions returned for {project_id}")
            self._version_cache[cache_key] = None
            return None
        
        # Return first version (API returns versions sorted by date)
        result = versions[0] if len(versions) > 0 else None
        
        if result:
            logger.debug(f"Found version: {result.get('version_number', 'unknown')}")
        
        self._version_cache[cache_key] = result
        return result

    def pick_file_from_version(self, version_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not version_json:
            return None
        files = version_json.get("files", [])
        if not files:
            return None
        for f in files:
            if f.get("primary", False):
                return f
        for f in files:
            if f.get("filename", "").endswith((".jar", ".zip")):
                return f
        return files[0]

    # --- CurseForge API ---

    def get_cf_headers(self) -> Dict[str, str]:
        return {"x-api-key": self.cf_api_key}

    def search_curseforge(self, name: str, class_id: int = CF_MOD_CLASS_ID) -> Optional[Dict[str, Any]]:
        """
        Search CurseForge for a mod or resource pack.
        
        Args:
            name: Project name to search
            class_id: CF_MOD_CLASS_ID for mods, CF_RESOURCE_PACK_CLASS_ID for texture packs
            
        Returns:
            First search result or None
        """
        if not self.cf_api_key:
            return None
        url = f"{CF_API_BASE}/v1/mods/search"
        params = {
            'gameId': CF_GAME_ID,
            'classId': class_id,
            'searchFilter': name,
            'sortField': CF_SORT_FIELD_RELEVANCE,
            'sortOrder': 'desc',
            'limit': 5
        }
        data = self.get_json(url, params=params, headers=self.get_cf_headers())
        if isinstance(data, dict) and 'data' in data:
            hits = data['data']
            if hits:
                name_low = name.lower()
                for mod in hits:
                    if mod.get('name', '').lower() == name_low:
                        return mod
                return hits[0]
        return None

    def get_latest_file_cf(self, mod_id: int, mc_version: str, mod_loader_type: int = 4) -> Optional[Dict[str, Any]]:
        if not self.cf_api_key:
            return None
        url = f"{CF_API_BASE}/v1/mods/{mod_id}/files"
        data = self.get_json(url, params={'pageSize': 50}, headers=self.get_cf_headers())
        if isinstance(data, dict) and 'data' in data:
            files = data['data']
            valid_files = []
            for f in files:
                if mc_version in f.get('gameVersions', []):
                    if mod_loader_type != 0:
                        # Map CF loader type to string identifiers
                        # 4 = Fabric, 1 = Forge, 6 = NeoForge, 5 = Quilt
                        target_loaders = []
                        if mod_loader_type == 4: target_loaders = ['fabric', 'quilt']
                        elif mod_loader_type == 1: target_loaders = ['forge']
                        elif mod_loader_type == 6: target_loaders = ['neoforge']
                        elif mod_loader_type == 5: target_loaders = ['quilt']
                        
                        if any(v.lower() in target_loaders for v in f.get('gameVersions', [])):
                             valid_files.append(f)
                    else:
                        valid_files.append(f)
            
            if valid_files:
                valid_files.sort(key=lambda x: x['fileDate'], reverse=True)
                return valid_files[0]
        return None
