import json
import time
import logging
import random
import requests
from typing import Dict, Any, List, Optional, Union
from .utils import BColors

BASE_API = "https://api.modrinth.com"
CF_API_BASE = "https://api.curseforge.com"
HEADERS = {"User-Agent": "modpack-downloader/3.0"}

logger = logging.getLogger("mc-quarry")

class APIClient:
    def __init__(self, cf_api_key: str = ""):
        self.cf_api_key = cf_api_key
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

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
        facets = [[f"project_type:{project_type}"]]
        if project_type == 'mod':
            facets.append(["categories:fabric"])
        q = {"query": name, "index": "relevance", "limit": limit, "facets": json.dumps(facets)}
        return self.get_json(f"{BASE_API}/v2/search", params=q)

    def get_modrinth_project(self, slug: str) -> Optional[Dict[str, Any]]:
        return self.get_json(f"{BASE_API}/v2/project/{slug}")

    def find_modrinth_version(self, project_id: str, mc_version: str, loader: str = 'fabric', force_latest: bool = False) -> Optional[Dict[str, Any]]:
        params = {}
        if not force_latest:
            params["game_versions"] = json.dumps([mc_version])
        if loader:
            params["loaders"] = json.dumps([loader])
        versions = self.get_json(f"{BASE_API}/v2/project/{project_id}/version", params=params)
        if isinstance(versions, list) and len(versions) > 0:
            return versions[0]
        return None

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

    def search_curseforge(self, name: str, class_id: int = 6) -> Optional[Dict[str, Any]]:
        if not self.cf_api_key:
            return None
        url = f"{CF_API_BASE}/v1/mods/search"
        params = {
            'gameId': 432,
            'classId': class_id,
            'searchFilter': name,
            'sortField': 2,
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
                        if any(v.lower() == 'fabric' for v in f.get('gameVersions', [])) or mod_loader_type == 4:
                             valid_files.append(f)
                    else:
                        valid_files.append(f)
            
            if valid_files:
                valid_files.sort(key=lambda x: x['fileDate'], reverse=True)
                return valid_files[0]
        return None
