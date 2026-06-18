"""Tests for mc_quarry.processor."""

from unittest import mock

import responses

from mc_quarry.api_client import APIClient
from mc_quarry.processor import (
    _generate_slug_candidates,
    _handle_curseforge,
    _handle_modrinth,
    _process_mod_wrapper,
)

# ---------------------------------------------------------------------------
# Module-level mock data (matching patterns in test_api_client.py)
# ---------------------------------------------------------------------------

# -- Modrinth mock data --

MOCK_MR_PROJECT = {
    "id": "A1b2c3d4",
    "slug": "sodium",
    "title": "Sodium",
    "project_type": "mod",
}

MOCK_MR_SEARCH_EXACT = {
    "hits": [
        {"project_id": "A1b2c3d4", "slug": "sodium", "title": "Sodium"},
    ],
}

MOCK_MR_SEARCH_PARTIAL = {
    "hits": [
        {"project_id": "A1b2c3d4", "slug": "sodium", "title": "Sodium Extended"},
    ],
}

MOCK_MR_EMPTY_SEARCH = {"hits": []}

MOCK_MR_VERSION = {
    "id": "v1",
    "version_number": "0.6.0",
    "name": "0.6.0",
    "files": [
        {
            "filename": "sodium-0.6.0.jar",
            "url": "https://cdn.modrinth.com/sodium-0.6.0.jar",
            "primary": True,
        },
    ],
    "game_versions": ["1.21"],
    "loaders": ["fabric"],
}

MOCK_MR_VERSIONS = [MOCK_MR_VERSION]

MOCK_MR_VERSION_NO_FILES = {
    "id": "v_empty",
    "version_number": "0.0.0",
    "name": "0.0.0",
    "files": [],
}

# -- CurseForge mock data --

MOCK_CF_PROJECT = {
    "id": 12345,
    "name": "JEI",
    "slug": "jei",
    "classId": 6,
}

MOCK_CF_SEARCH = {"data": [MOCK_CF_PROJECT]}
MOCK_CF_EMPTY_SEARCH = {"data": []}

MOCK_CF_FILE = {
    "id": 98765,
    "fileName": "jei-1.21-fabric.jar",
    "displayName": "JEI 1.21",
    "fileDate": "2025-01-15T12:00:00Z",
    "gameVersions": ["1.21", "Fabric", "fabric"],
    "downloadUrl": "https://cf.example.com/jei.jar",
}

MOCK_CF_FILES = {"data": [MOCK_CF_FILE]}

MOCK_CF_FILE_NO_URL = {
    "id": 98765,
    "fileName": "jei-1.21-fabric.jar",
    "displayName": "JEI 1.21",
    "fileDate": "2025-01-15T12:00:00Z",
    "gameVersions": ["1.21", "Fabric", "fabric"],
    "downloadUrl": None,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_ui():
    """Create a fresh MagicMock for the UI handler."""
    return mock.MagicMock()


# ---------------------------------------------------------------------------
# _generate_slug_candidates tests
# ---------------------------------------------------------------------------


class TestGenerateSlugCandidates:
    """Verify slug inference from mod names."""

    def test_simple_name(self):
        """Single-word name becomes its lowercase self."""
        assert _generate_slug_candidates("Sodium") == ["sodium"]

    def test_multi_word(self):
        """Spaces become hyphens."""
        cands = _generate_slug_candidates("Fabric API")
        assert "fabric-api" in cands

    def test_camelcase(self):
        """CamelCase gets hyphenated."""
        cands = _generate_slug_candidates("FerriteCore")
        assert "ferrite-core" in cands

    def test_apostrophe_stripped(self):
        """Apostrophes removed, spaces become hyphens."""
        cands = _generate_slug_candidates("Xaero's Minimap")
        assert "xaeros-minimap" in cands

    def test_parenthetical_abbreviation(self):
        """Parenthetical abbreviation included as a candidate."""
        cands = _generate_slug_candidates("YetAnotherConfigLib (YACL)")
        assert "yacl" in cands

    def test_no_hyphens_variant(self):
        """No-hyphens variant generated (for slugs like 'morechathistory')."""
        cands = _generate_slug_candidates("More Chat History")
        assert "morechathistory" in cands

    def test_shorter_variants(self):
        """Progressively shorter slugs generated."""
        cands = _generate_slug_candidates("Cloth Config API")
        assert "cloth-config-api" in cands


# ---------------------------------------------------------------------------
# _handle_modrinth tests
# ---------------------------------------------------------------------------


class TestHandleModrinth:
    """Exercise the _handle_modrinth function end-to-end via HTTP mocking."""

    # -- URL-based lookup ------------------------------------------------

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_url_lookup_and_download(self, mock_exec, stats, temp_dir):
        """A modrinth.com URL resolves the project slug and downloads."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            json=MOCK_MR_PROJECT,
            status=200,
        )
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=MOCK_MR_VERSIONS,
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client,
            "https://modrinth.com/mod/sodium",
            "mod",
            "1.21",
            temp_dir,
            {},
            stats,
            False,
            ui,
        )

        mock_exec.assert_called_once()
        assert stats.not_found == []
        assert stats.failed == []

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_url_lookup_not_found_fallback_to_search(
        self, mock_exec, stats, temp_dir
    ):
        """URL project lookup fails (404); search fallback succeeds."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            status=404,
        )
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MR_SEARCH_EXACT,
            status=200,
        )
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=MOCK_MR_VERSIONS,
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client,
            "https://modrinth.com/mod/sodium",
            "mod",
            "1.21",
            temp_dir,
            {},
            stats,
            False,
            ui,
        )

        mock_exec.assert_called_once()

    # -- Search-based lookup ---------------------------------------------

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_slug_lookup_success(self, mock_exec, stats, temp_dir):
        """Name resolves to a valid slug — direct project endpoint used."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            json=MOCK_MR_PROJECT,
            status=200,
        )
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=MOCK_MR_VERSIONS,
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client, "Sodium", "mod", "1.21", temp_dir, {}, stats, False, ui,
        )

        mock_exec.assert_called_once()

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_search_exact_title_match(self, mock_exec, stats, temp_dir):
        """Slug lookup fails; name matches a search hit's title exactly."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            status=404,
        )
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MR_SEARCH_EXACT,
            status=200,
        )
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=MOCK_MR_VERSIONS,
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client, "Sodium", "mod", "1.21", temp_dir, {}, stats, False, ui,
        )

        mock_exec.assert_called_once()

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_search_exact_slug_match(self, mock_exec, stats, temp_dir):
        """Slug lookup fails; name matches a search hit's slug exactly."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            status=404,
        )
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MR_SEARCH_EXACT,
            status=200,
        )
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=MOCK_MR_VERSIONS,
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client, "sodium", "mod", "1.21", temp_dir, {}, stats, False, ui,
        )

        mock_exec.assert_called_once()

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_search_partial_match(self, mock_exec, stats, temp_dir):
        """Slug lookup fails; name is a substring of the first hit's title."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            status=404,
        )
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MR_SEARCH_PARTIAL,
            status=200,
        )
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=MOCK_MR_VERSIONS,
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client, "Sodium", "mod", "1.21", temp_dir, {}, stats, False, ui,
        )

        mock_exec.assert_called_once()

    # -- Failure modes ---------------------------------------------------

    @responses.activate
    def test_project_not_found(self, stats, temp_dir):
        """No matching project triggers add_not_found."""
        responses.get(
            "https://api.modrinth.com/v2/project/doesnotexist",
            status=404,
        )
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MR_EMPTY_SEARCH,
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client,
            "DoesNotExist",
            "mod",
            "1.21",
            temp_dir,
            {},
            stats,
            False,
            ui,
        )

        assert stats.not_found == ["DoesNotExist"]
        assert stats.failed == []

    @responses.activate
    def test_no_compatible_version(self, stats, temp_dir):
        """Project found but no version for the MC version."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            status=404,
        )
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MR_SEARCH_EXACT,
            status=200,
        )
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=[],
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client, "Sodium", "mod", "1.20", temp_dir, {}, stats, False, ui,
        )

        assert stats.failed == [("Sodium", "No compatible version found on Modrinth")]

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_resourcepack_fallback_to_force_latest(
        self, mock_exec, stats, temp_dir
    ):
        """Resource pack: first version lookup fails, retry with force_latest."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            status=404,
        )
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MR_SEARCH_EXACT,
            status=200,
        )
        # First call returns empty (no matching MC version)
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=[],
            status=200,
        )
        # Second call (force_latest) returns a version
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=MOCK_MR_VERSIONS,
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client, "Sodium", "resourcepack", "1.21",
            temp_dir, {}, stats, False, ui,
        )

        mock_exec.assert_called_once()

    @responses.activate
    def test_no_file_in_version(self, stats, temp_dir):
        """Version exists but has no downloadable files."""
        responses.get(
            "https://api.modrinth.com/v2/project/sodium",
            status=404,
        )
        responses.get(
            "https://api.modrinth.com/v2/search",
            json=MOCK_MR_SEARCH_EXACT,
            status=200,
        )
        responses.get(
            "https://api.modrinth.com/v2/project/A1b2c3d4/version",
            json=[MOCK_MR_VERSION_NO_FILES],
            status=200,
        )

        client = APIClient()
        ui = _make_mock_ui()
        _handle_modrinth(
            client, "Sodium", "mod", "1.21", temp_dir, {}, stats, False, ui,
        )

        assert stats.failed == [("Sodium", "No file to download")]


# ---------------------------------------------------------------------------
# _handle_curseforge tests
# ---------------------------------------------------------------------------


class TestHandleCurseforge:
    """Exercise the _handle_curseforge function end-to-end via HTTP mocking."""

    def test_no_api_key(self, stats, temp_dir):
        """Missing CF API key triggers add_not_found immediately."""
        client = APIClient()  # no key
        ui = _make_mock_ui()
        _handle_curseforge(
            client, "JEI", "mod", "1.21", temp_dir, {}, stats, False, ui,
        )

        assert stats.not_found == ["JEI"]
        assert stats.failed == []

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_url_lookup(self, mock_exec, stats, temp_dir):
        """A curseforge.com URL extracts the name and downloads."""
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=MOCK_CF_SEARCH,
            status=200,
        )
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json=MOCK_CF_FILES,
            status=200,
        )

        client = APIClient("fake-key")
        ui = _make_mock_ui()
        _handle_curseforge(
            client,
            "https://www.curseforge.com/minecraft/mc-mods/jei",
            "mod",
            "1.21",
            temp_dir,
            {},
            stats,
            False,
            ui,
        )

        mock_exec.assert_called_once()

    @responses.activate
    def test_project_not_found(self, stats, temp_dir):
        """Search returns empty results."""
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=MOCK_CF_EMPTY_SEARCH,
            status=200,
        )

        client = APIClient("fake-key")
        ui = _make_mock_ui()
        _handle_curseforge(
            client, "DoesNotExist", "mod", "1.21",
            temp_dir, {}, stats, False, ui,
        )

        assert stats.not_found == ["DoesNotExist"]

    @responses.activate
    def test_no_compatible_version(self, stats, temp_dir):
        """Project found but no compatible file for the MC version."""
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=MOCK_CF_SEARCH,
            status=200,
        )
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json={"data": []},
            status=200,
        )

        client = APIClient("fake-key")
        ui = _make_mock_ui()
        _handle_curseforge(
            client, "JEI", "mod", "1.20", temp_dir, {}, stats, False, ui,
        )

        assert stats.failed == [("JEI", "No compatible version on CF")]

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_resourcepack_fallback_to_force_latest(
        self, mock_exec, stats, temp_dir
    ):
        """Resource pack: first file lookup fails, retry with force_latest."""
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=MOCK_CF_SEARCH,
            status=200,
        )
        # First call returns empty (no matching MC version)
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json={"data": []},
            status=200,
        )
        # Second call (force_latest) returns a file
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json=MOCK_CF_FILES,
            status=200,
        )

        client = APIClient("fake-key")
        ui = _make_mock_ui()
        _handle_curseforge(
            client, "JEI", "resourcepack", "1.21",
            temp_dir, {}, stats, False, ui,
        )

        mock_exec.assert_called_once()

    @responses.activate
    def test_download_url_disabled(self, stats, temp_dir):
        """File has no downloadUrl -> API download disabled."""
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=MOCK_CF_SEARCH,
            status=200,
        )
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json={"data": [MOCK_CF_FILE_NO_URL]},
            status=200,
        )

        client = APIClient("fake-key")
        ui = _make_mock_ui()
        _handle_curseforge(
            client, "JEI", "mod", "1.21", temp_dir, {}, stats, False, ui,
        )

        assert stats.failed == [("JEI", "API download disabled by author")]

    @responses.activate
    @mock.patch("mc_quarry.processor.execute_download")
    def test_successful_download(self, mock_exec, stats, temp_dir):
        """Happy path: project found, file found, execute_download called."""
        responses.get(
            "https://api.curseforge.com/v1/mods/search",
            json=MOCK_CF_SEARCH,
            status=200,
        )
        responses.get(
            "https://api.curseforge.com/v1/mods/12345/files",
            json=MOCK_CF_FILES,
            status=200,
        )

        client = APIClient("fake-key")
        ui = _make_mock_ui()
        _handle_curseforge(
            client, "JEI", "mod", "1.21", temp_dir, {}, stats, False, ui,
        )

        mock_exec.assert_called_once()
        assert stats.not_found == []
        assert stats.failed == []


# ---------------------------------------------------------------------------
# _process_mod_wrapper tests
# ---------------------------------------------------------------------------


class TestProcessModWrapper:
    """Test dispatching, exception handling, and argument plumbing."""

    @mock.patch("mc_quarry.processor._handle_modrinth")
    def test_dispatch_modrinth(self, mock_handle, stats, temp_dir):
        """Wrapper dispatches to _handle_modrinth for provider='modrinth'."""
        client = mock.MagicMock()
        ui = _make_mock_ui()
        _process_mod_wrapper(
            client, "Sodium", "1.21", "mod", temp_dir,
            {}, stats, "modrinth", verbose=False, ui_handler=ui,
        )

        mock_handle.assert_called_once_with(
            client, "Sodium", "mod", "1.21", temp_dir,
            {}, stats, False, ui,
        )

    @mock.patch("mc_quarry.processor._handle_curseforge")
    def test_dispatch_curseforge(self, mock_handle, stats, temp_dir):
        """Wrapper dispatches to _handle_curseforge for provider='curseforge'."""
        client = mock.MagicMock()
        ui = _make_mock_ui()
        _process_mod_wrapper(
            client, "JEI", "1.21", "mod", temp_dir,
            {}, stats, "curseforge", verbose=False, ui_handler=ui,
        )

        mock_handle.assert_called_once_with(
            client, "JEI", "mod", "1.21", temp_dir,
            {}, stats, False, ui,
        )

    @mock.patch("mc_quarry.processor._handle_modrinth")
    def test_exception_handling(self, mock_handle, stats, temp_dir):
        """Wrapper catches exceptions and records failure in stats."""
        mock_handle.side_effect = RuntimeError("API timeout")
        ui = _make_mock_ui()

        _process_mod_wrapper(
            mock.MagicMock(), "Sodium", "1.21", "mod",
            temp_dir, {}, stats, "modrinth", verbose=True, ui_handler=ui,
        )

        assert len(stats.failed) == 1
        name, reason = stats.failed[0]
        assert name == "Sodium"
        assert "API timeout" in reason
        ui.log.assert_called()
        ui.update_progress.assert_called_once()

    @mock.patch("mc_quarry.processor._handle_modrinth")
    def test_custom_ui_handler(self, mock_handle, stats, temp_dir):
        """Wrapper passes ui_handler through to the handler."""
        custom_ui = _make_mock_ui()

        _process_mod_wrapper(
            mock.MagicMock(), "Sodium", "1.21", "mod",
            temp_dir, {}, stats, "modrinth", verbose=True,
            ui_handler=custom_ui,
        )

        _args, _kwargs = mock_handle.call_args
        assert _args[8] is custom_ui  # ui is the 9th positional arg

    @mock.patch("mc_quarry.processor._handle_modrinth")
    def test_name_stripping(self, mock_handle, stats, temp_dir):
        """Leading/trailing whitespace is stripped from the name."""
        ui = _make_mock_ui()
        _process_mod_wrapper(
            mock.MagicMock(), "   Sodium  ", "1.21", "mod",
            temp_dir, {}, stats, "modrinth", verbose=False, ui_handler=ui,
        )

        _args, _kwargs = mock_handle.call_args
        assert _args[1] == "Sodium"  # clean_name is the 2nd positional arg
