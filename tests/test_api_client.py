"""Tests for mc_quarry.api_client."""

import json

import responses

from mc_quarry.api_client import APIClient

# Modrinth test data
MOCK_MODRINTH_SEARCH = {
    "hits": [
        {
            "slug": "sodium",
            "title": "Sodium",
            "project_type": "mod",
            "versions": ["1.21", "1.20.1"],
        }
    ]
}

MOCK_MODRINTH_PROJECT = {
    "slug": "sodium",
    "title": "Sodium",
    "project_type": "mod",
    "client_side": "required",
    "server_side": "required",
}

MOCK_MODRINTH_VERSIONS = [
    {
        "id": "ver001",
        "version_number": "0.6.0",
        "files": [
            {
                "filename": "sodium-0.6.0.jar",
                "url": "https://cdn.modrinth.com/sodium-0.6.0.jar",
                "primary": True,
            }
        ],
        "game_versions": ["1.21"],
        "loaders": ["fabric"],
    }
]


def _cf_data_response(data):
    """Wrap data in CurseForge response envelope."""
    return {"data": data}


MOCK_CF_SEARCH = _cf_data_response([
    {
        "id": 12345,
        "name": "JEI",
        "slug": "jei",
        "classId": 6,
    }
])

MOCK_CF_FILES = _cf_data_response([
    {
        "id": 98765,
        "fileName": "jei-1.21-fabric.jar",
        "fileDate": "2025-01-15T12:00:00Z",
        "gameVersions": ["1.21", "Fabric", "fabric"],
        "downloadUrl": "https://cf.example.com/jei.jar",
    }
])


class TestAPIClientInit:
    def test_default_key(self):
        client = APIClient()
        assert client.cf_api_key == ""

    def test_with_key(self):
        client = APIClient("my-key")
        assert client.cf_api_key == "my-key"

    def test_session_configured(self):
        client = APIClient()
        assert client.session.headers["User-Agent"] == "modpack-downloader/3.0"


class TestGetJSON:
    @responses.activate
    def test_success(self):
        responses.get("https://api.example.com/test", json={"ok": True}, status=200)
        client = APIClient()
        result = client.get_json("https://api.example.com/test")
        assert result == {"ok": True}

    @responses.activate
    def test_404_returns_none(self):
        responses.get("https://api.example.com/notfound", status=404)
        client = APIClient()
        result = client.get_json("https://api.example.com/notfound")
        assert result is None

    @responses.activate
    def test_429_rate_limit_retries(self):
        # First call 429, second succeeds
        responses.get(
            "https://api.example.com/ratelimit",
            status=429,
            headers={"Retry-After": "0"},
        )
        responses.get(
            "https://api.example.com/ratelimit",
            json={"ok": True},
            status=200,
        )
        client = APIClient()
        result = client.get_json("https://api.example.com/ratelimit")
        assert result == {"ok": True}
        # Two calls made
        assert len(responses.calls) == 2

    @responses.activate
    def test_4xx_client_error_no_retry(self):
        responses.get("https://api.example.com/badrequest", status=400)
        client = APIClient()
        result = client.get_json("https://api.example.com/badrequest")
        assert result is None

    @responses.activate
    def test_network_error_retries(self):
        responses.get("https://api.example.com/error", status=503)
        responses.get("https://api.example.com/error", status=503)
        responses.get("https://api.example.com/error", status=503)
        responses.get("https://api.example.com/error", status=503)
        client = APIClient()
        result = client.get_json("https://api.example.com/error", max_retries=3)
        assert result is None

    @responses.activate
    def test_malformed_json_returns_none(self):
        responses.get(
            "https://api.example.com/badjson",
            body="not json",
            status=200,
            content_type="application/json",
        )
        client = APIClient()
        result = client.get_json("https://api.example.com/badjson")
        assert result is None


class TestModrinthSearch:
    @responses.activate
    def test_search_found(self):
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MODRINTH_SEARCH,
            status=200,
        )
        client = APIClient()
        result = client.search_modrinth("sodium")
        assert result is not None
        assert result["hits"][0]["slug"] == "sodium"

    @responses.activate
    def test_search_no_api_key(self):
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MODRINTH_SEARCH,
            status=200,
        )
        client = APIClient()
        result = client.search_modrinth("sodium")
        assert result is not None

    @responses.activate
    def test_search_facets_include_fabric(self):
        def request_callback(request):
            params = dict(urllib.parse.parse_qsl(request.url.split("?")[1]))
            facets = json.loads(params["facets"])
            # Should filter for fabric mods
            assert ["categories:fabric"] in facets
            return (200, {}, json.dumps(MOCK_MODRINTH_SEARCH))

        import urllib.parse

        responses.add_callback(
            responses.GET,
            "https://api.modrinth.com/v2/search",
            callback=request_callback,
        )
        client = APIClient()
        client.search_modrinth("sodium")

    @responses.activate
    def test_search_resource_pack_no_fabric_facet(self):
        """Resource pack search should not add fabric facet."""

        def request_callback(request):
            params = dict(urllib.parse.parse_qsl(request.url.split("?")[1]))
            facets = json.loads(params["facets"])
            # resource pack search should not have fabric filter
            fabric_facets = [f for f in facets if "fabric" in str(f)]
            assert len(fabric_facets) == 0
            return (200, {}, json.dumps(MOCK_MODRINTH_SEARCH))

        import urllib.parse

        responses.add_callback(
            responses.GET,
            "https://api.modrinth.com/v2/search",
            callback=request_callback,
        )
        client = APIClient()
        client.search_modrinth("some-pack", project_type="resourcepack")


class TestModrinthProject:
    @responses.activate
    def test_get_project_found(self):
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            json=MOCK_MODRINTH_PROJECT,
            status=200,
        )
        client = APIClient()
        project = client.get_modrinth_project("sodium")
        assert project is not None
        assert project["slug"] == "sodium"

    @responses.activate
    def test_get_project_not_found(self):
        responses.get(
            "https://api.modrinth.com/v2/project/nonexistent",
            status=404,
        )
        client = APIClient()
        project = client.get_modrinth_project("nonexistent")
        assert project is None


class TestModrinthVersion:
    @responses.activate
    def test_find_version_success(self):
        responses.get(
            "https://api.modrinth.com/v2/project/sodium/version",
            json=MOCK_MODRINTH_VERSIONS,
            status=200,
        )
        client = APIClient()
        version = client.find_modrinth_version("sodium", "1.21")
        assert version is not None
        assert version["version_number"] == "0.6.0"

    @responses.activate
    def test_find_version_no_results(self):
        responses.get(
            "https://api.modrinth.com/v2/project/sodium/version",
            json=[],
            status=200,
        )
        client = APIClient()
        version = client.find_modrinth_version("sodium", "1.20")
        assert version is None

    @responses.activate
    def test_find_version_cached(self):
        responses.get(
            "https://api.modrinth.com/v2/project/sodium/version",
            json=MOCK_MODRINTH_VERSIONS,
            status=200,
        )
        client = APIClient()
        # First call fetches
        v1 = client.find_modrinth_version("sodium", "1.21")
        # Second call uses cache — no new HTTP call
        v2 = client.find_modrinth_version("sodium", "1.21")
        assert v1 == v2
        assert len(responses.calls) == 1

    @responses.activate
    def test_force_latest_skips_version_filter(self):
        def request_callback(request):
            params = dict(urllib.parse.parse_qsl(request.url.split("?")[1]))
            # force_latest should NOT send game_versions filter
            assert "game_versions" not in params or params.get("game_versions") == "null"
            return (200, {}, json.dumps(MOCK_MODRINTH_VERSIONS))

        import urllib.parse

        responses.add_callback(
            responses.GET,
            "https://api.modrinth.com/v2/project/sodium/version",
            callback=request_callback,
        )
        client = APIClient()
        client.find_modrinth_version("sodium", "1.21", force_latest=True)


class TestPickFile:
    def test_returns_none_for_empty_version(self):
        client = APIClient()
        assert client.pick_file_from_version({}) is None

    def test_returns_primary_file(self):
        client = APIClient()
        version = {
            "files": [
                {"filename": "secondary.jar", "url": "https://a.com/b.jar", "primary": False},
                {"filename": "primary.jar", "url": "https://a.com/p.jar", "primary": True},
            ]
        }
        result = client.pick_file_from_version(version)
        assert result["filename"] == "primary.jar"

    def test_falls_back_to_first_jar(self):
        client = APIClient()
        version = {
            "files": [
                {"filename": "data.txt", "url": "https://a.com/d.txt", "primary": False},
                {"filename": "mod.jar", "url": "https://a.com/m.jar", "primary": False},
            ]
        }
        result = client.pick_file_from_version(version)
        assert result["filename"] == "mod.jar"

    def test_returns_first_file_if_no_jar(self):
        client = APIClient()
        version = {
            "files": [
                {"filename": "readme.txt", "url": "https://a.com/r.txt", "primary": False},
            ]
        }
        result = client.pick_file_from_version(version)
        assert result["filename"] == "readme.txt"


class TestCurseForge:
    @responses.activate
    def test_search_without_key_returns_none(self):
        client = APIClient()
        result = client.search_curseforge("jei")
        assert result is None

    @responses.activate
    def test_search_with_key_found(self):
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=_cf_data_response([{"id": 12345, "name": "JEI", "slug": "jei"}]),
            status=200,
        )
        client = APIClient("fake-key")
        result = client.search_curseforge("JEI")
        assert result is not None
        assert result["name"] == "JEI"

    @responses.activate
    def test_search_exact_name_match_preferred(self):
        """Exact name match should be preferred over first hit."""
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=_cf_data_response([
                {"id": 1, "name": "JEI (Unofficial)", "slug": "jei-unofficial"},
                {"id": 2, "name": "JEI", "slug": "jei"},
            ]),
            status=200,
        )
        client = APIClient("fake-key")
        result = client.search_curseforge("JEI")
        # Should pick exact match (id=2), not first hit (id=1)
        assert result["id"] == 2

    @responses.activate
    def test_latest_file_without_key_returns_none(self):
        client = APIClient()
        result = client.get_latest_file_cf(12345, "1.21")
        assert result is None

    @responses.activate
    def test_latest_file_found(self):
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json=MOCK_CF_FILES,
            status=200,
        )
        client = APIClient("fake-key")
        result = client.get_latest_file_cf(12345, "1.21", mod_loader_type=4)
        assert result is not None
        assert result["fileName"] == "jei-1.21-fabric.jar"

    @responses.activate
    def test_latest_file_force_latest_skips_version_filter(self):
        """With force_latest=True, should return latest regardless of MC version."""
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json=_cf_data_response([
                {
                    "id": 1,
                    "fileName": "jei-old.jar",
                    "fileDate": "2024-01-01T12:00:00Z",
                    "gameVersions": ["1.20", "Fabric"],
                    "downloadUrl": "https://cf.example.com/old.jar",
                },
                {
                    "id": 2,
                    "fileName": "jei-new.jar",
                    "fileDate": "2025-01-01T12:00:00Z",
                    "gameVersions": ["1.21", "Fabric"],
                    "downloadUrl": "https://cf.example.com/new.jar",
                },
            ]),
            status=200,
        )
        client = APIClient("fake-key")
        result = client.get_latest_file_cf(12345, "1.20", force_latest=True)
        # Should return newest file (id=2) even though mc_version is 1.20
        assert result["id"] == 2

    @responses.activate
    def test_latest_file_no_compatible(self):
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json=_cf_data_response([]),
            status=200,
        )
        client = APIClient("fake-key")
        result = client.get_latest_file_cf(12345, "1.21")
        assert result is None

    @responses.activate
    def test_search_partial_name_match_fallback(self):
        """When exact match not found, fallback to first close match."""
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=_cf_data_response([
                {"id": 42, "name": "jei-unofficial", "slug": "jei-unofficial"},
            ]),
            status=200,
        )
        client = APIClient("fake-key")
        result = client.search_curseforge("JEI")
        assert result is not None
        assert result["id"] == 42

    @responses.activate
    def test_get_cf_headers(self):
        client = APIClient("my-secret-key")
        headers = client.get_cf_headers()
        assert headers["x-api-key"] == "my-secret-key"


class TestCFLoaderMapping:
    @responses.activate
    def test_fabric_loader_filter(self):
        """Fabric loader (type 4) should match 'fabric' or 'quilt' variants."""
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json=_cf_data_response([
                {
                    "id": 1,
                    "fileName": "mod-forge.jar",
                    "fileDate": "2025-01-01T12:00:00Z",
                    "gameVersions": ["1.21", "Forge"],
                    "downloadUrl": "https://cf.example.com/forge.jar",
                },
                {
                    "id": 2,
                    "fileName": "mod-fabric.jar",
                    "fileDate": "2025-01-01T12:00:00Z",
                    "gameVersions": ["1.21", "Fabric", "fabric"],
                    "downloadUrl": "https://cf.example.com/fabric.jar",
                },
            ]),
            status=200,
        )
        client = APIClient("fake-key")
        result = client.get_latest_file_cf(12345, "1.21", mod_loader_type=4)
        # Should pick the fabric version
        assert result is not None
        assert result["fileName"] == "mod-fabric.jar"
