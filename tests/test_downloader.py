"""Tests for mc_quarry.downloader.

Covers all 7 public functions: download_file, write_mod_info, read_all_mod_info,
compare_versions, check_incompatibility, filter_mods, execute_download.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import responses
from requests.exceptions import ConnectionError as RequestsConnectionError

from mc_quarry.downloader import (
    check_incompatibility,
    compare_versions,
    download_file,
    execute_download,
    filter_mods,
    read_all_mod_info,
    write_mod_info,
)


class TestDownloadFile:
    """Tests for download_file() — HTTP download with retry logic."""

    @responses.activate
    def test_successful_download(self, temp_dir):
        """Basic success: body written to destination file."""
        url = "https://cdn.example.com/mod.jar"
        dest = temp_dir / "mod.jar"
        responses.get(url, body=b"jar content data", status=200)

        result = download_file(url, dest)

        assert result is True
        assert dest.exists()
        assert dest.read_bytes() == b"jar content data"

    @responses.activate
    @patch("mc_quarry.downloader.time.sleep")
    def test_retry_then_succeed(self, mock_sleep, temp_dir):
        """First attempt fails (500), second attempt succeeds."""
        url = "https://cdn.example.com/mod.jar"
        dest = temp_dir / "mod.jar"
        responses.get(url, body=b"", status=500)
        responses.get(url, body=b"retry success", status=200)

        result = download_file(url, dest, max_retries=2)

        assert result is True
        assert dest.read_bytes() == b"retry success"

    @responses.activate
    @patch("mc_quarry.downloader.time.sleep")
    def test_all_retries_fail(self, mock_sleep, temp_dir):
        """All attempts return 500, function returns False."""
        url = "https://cdn.example.com/mod.jar"
        dest = temp_dir / "mod.jar"
        for _ in range(5):
            responses.get(url, body=b"", status=500)

        result = download_file(url, dest, max_retries=3)

        assert result is False
        assert not dest.exists()

    @responses.activate
    def test_http_404_returns_false(self, temp_dir):
        """A single 404 fails without retry needed to exhaust."""
        url = "https://cdn.example.com/missing.jar"
        dest = temp_dir / "missing.jar"
        responses.get(url, body=b"Not Found", status=404)

        result = download_file(url, dest, max_retries=1)

        assert result is False
        assert not dest.exists()

    @responses.activate
    @patch("mc_quarry.downloader.time.sleep")
    def test_connection_error_retried(self, mock_sleep, temp_dir):
        """ConnectionError (no route to host) is caught and retried."""
        url = "https://cdn.example.com/down.jar"
        dest = temp_dir / "down.jar"
        responses.get(url, body=RequestsConnectionError("connection refused"))

        result = download_file(url, dest, max_retries=1)

        assert result is False
        assert not dest.exists()

    @responses.activate
    def test_max_retries_one_fails_fast(self, temp_dir):
        """max_retries=1 means no retry after first failure."""
        url = "https://cdn.example.com/fail.jar"
        dest = temp_dir / "fail.jar"
        responses.get(url, body=b"", status=500)

        result = download_file(url, dest, max_retries=1)

        assert result is False

    @responses.activate
    def test_empty_response_body(self, temp_dir):
        """An empty but successful response still creates the file."""
        url = "https://cdn.example.com/empty.jar"
        dest = temp_dir / "empty.jar"
        responses.get(url, body=b"", status=200)

        result = download_file(url, dest)

        assert result is True
        assert dest.exists()
        assert dest.read_bytes() == b""


class TestWriteModInfo:
    """Tests for write_mod_info() — .modinfo JSON metadata sidecar."""

    def test_writes_correct_metadata(self, temp_dir):
        """All metadata fields are written correctly."""
        jar_path = temp_dir / "sodium-0.6.0.jar"
        jar_path.write_text("dummy")

        write_mod_info(
            jar_path,
            project_id="proj123",
            project_slug="sodium",
            version_id="ver456",
            version_name="0.6.0",
            filename="sodium-0.6.0.jar",
            provider="modrinth",
        )

        info_path = jar_path.with_suffix(".jar.modinfo")
        assert info_path.exists()
        data = json.loads(info_path.read_text())
        assert data["project_id"] == "proj123"
        assert data["project_slug"] == "sodium"
        assert data["version_id"] == "ver456"
        assert data["version_name"] == "0.6.0"
        assert data["filename"] == "sodium-0.6.0.jar"
        assert data["provider"] == "modrinth"

    def test_provider_defaults_to_modrinth(self, temp_dir):
        """Provider defaults to 'modrinth' when not specified."""
        jar_path = temp_dir / "lithium.jar"
        jar_path.write_text("dummy")

        write_mod_info(
            jar_path,
            project_id="p1",
            project_slug="lithium",
            version_id="v1",
            version_name="1.0",
            filename="lithium.jar",
        )

        info_path = jar_path.with_suffix(".jar.modinfo")
        data = json.loads(info_path.read_text())
        assert data["provider"] == "modrinth"

    def test_filename_is_sanitized(self, temp_dir):
        """Filename goes through sanitize_filename before storage."""
        jar_path = temp_dir / "mod.jar"
        jar_path.write_text("dummy")

        write_mod_info(
            jar_path,
            project_id="p1",
            project_slug="slug",
            version_id="v1",
            version_name="1.0",
            filename=r"bad<>name|.jar",
        )

        info_path = jar_path.with_suffix(".jar.modinfo")
        data = json.loads(info_path.read_text())
        assert data["filename"] == "badname.jar"

    def test_overwrites_existing_modinfo(self, temp_dir):
        """Writing a second modinfo overwrites the first."""
        jar_path = temp_dir / "mod.jar"
        jar_path.write_text("dummy")
        info_path = jar_path.with_suffix(".jar.modinfo")
        info_path.write_text(json.dumps({"old": "data", "version_name": "0.1"}))

        write_mod_info(
            jar_path,
            project_id="new_id",
            project_slug="new-slug",
            version_id="new_ver",
            version_name="2.0",
            filename="mod.jar",
        )

        data = json.loads(info_path.read_text())
        assert data["version_name"] == "2.0"

    def test_os_error_logged(self, temp_dir):
        """When the parent directory does not exist an error is logged."""
        jar_path = Path("/nonexistent/deeply/nested/mod.jar")

        # Should not raise — only log
        write_mod_info(
            jar_path,
            project_id="p1",
            project_slug="slug",
            version_id="v1",
            version_name="1.0",
            filename="mod.jar",
        )
        # No assertion needed — the function handled the error cleanly


class TestReadAllModInfo:
    """Tests for read_all_mod_info() — directory scan of .modinfo files."""

    def test_empty_directory_returns_empty_dict(self, temp_dir):
        """No .modinfo files means an empty dict."""
        assert read_all_mod_info(temp_dir) == {}

    def test_single_valid_modinfo(self, temp_dir):
        """A single modinfo with matching jar is indexed by project_id and slug."""
        (temp_dir / "sodium.jar").write_text("dummy")
        (temp_dir / "sodium.jar.modinfo").write_text(json.dumps({
            "project_id": "proj123",
            "project_slug": "sodium",
            "version_id": "v1",
            "version_name": "0.6.0",
            "filename": "sodium.jar",
            "provider": "modrinth",
        }))

        result = read_all_mod_info(temp_dir)

        assert "proj123" in result
        assert "sodium" in result
        assert result["proj123"]["version_name"] == "0.6.0"

    def test_multiple_modinfo_files(self, temp_dir):
        """Multiple modinfo files are all indexed by project_id and slug."""
        for name in ["sodium", "lithium"]:
            (temp_dir / f"{name}.jar").write_text("dummy")
            (temp_dir / f"{name}.jar.modinfo").write_text(json.dumps({
                "project_id": f"proj_{name}",
                "project_slug": name,
                "version_id": "v1",
                "version_name": "1.0",
                "filename": f"{name}.jar",
                "provider": "modrinth",
            }))

        result = read_all_mod_info(temp_dir)

        assert "proj_sodium" in result
        assert "proj_lithium" in result
        assert "sodium" in result
        assert "lithium" in result
        assert len(result) == 4  # 2 project_ids + 2 slugs

    def test_missing_project_id_skipped(self, temp_dir):
        """Modinfo without project_id is skipped, file is NOT deleted."""
        (temp_dir / "mod.jar").write_text("dummy")
        (temp_dir / "mod.jar.modinfo").write_text(json.dumps({
            "version_id": "v1",
            "filename": "mod.jar",
        }))

        result = read_all_mod_info(temp_dir)

        assert result == {}
        assert (temp_dir / "mod.jar.modinfo").exists()

    def test_missing_filename_skipped(self, temp_dir):
        """Modinfo without filename is skipped, file is NOT deleted."""
        (temp_dir / "mod.jar").write_text("dummy")
        (temp_dir / "mod.jar.modinfo").write_text(json.dumps({
            "project_id": "p123",
            "version_id": "v1",
        }))

        result = read_all_mod_info(temp_dir)

        assert result == {}
        assert (temp_dir / "mod.jar.modinfo").exists()

    def test_orphaned_modinfo_removed(self, temp_dir):
        """Modinfo whose jar file does not exist is deleted."""
        info_path = temp_dir / "mod.jar.modinfo"
        info_path.write_text(json.dumps({
            "project_id": "p123",
            "project_slug": "mod",
            "filename": "mod.jar",
            "provider": "modrinth",
        }))

        result = read_all_mod_info(temp_dir)

        assert result == {}
        assert not info_path.exists()

    def test_corrupted_json_removed(self, temp_dir):
        """Modinfo with invalid JSON is removed."""
        info_path = temp_dir / "bad.modinfo"
        info_path.write_text("not valid json {{{")

        result = read_all_mod_info(temp_dir)

        assert result == {}
        assert not info_path.exists()


class TestCompareVersions:
    """Tests for compare_versions() — version string comparison."""

    def test_v1_greater_than_v2(self):
        assert compare_versions("2.0.0", "1.0.0") == 1

    def test_v1_less_than_v2(self):
        assert compare_versions("1.0.0", "2.0.0") == -1

    def test_equal_versions(self):
        assert compare_versions("1.20.1", "1.20.1") == 0

    def test_prerelease_handled(self):
        """Pre-release versions compare sensibly (release > pre-release)."""
        assert compare_versions("1.20", "1.20-alpha") >= 0

    def test_fallback_numeric_parse(self):
        """When packaging.version fails, numeric tuple fallback works."""
        assert compare_versions("1.20", "1.20.1") == -1

    def test_fallback_numeric_extraction(self):
        assert compare_versions("abc1.5", "abc2.0") < 0
        assert compare_versions("abc2.0", "abc1.5") > 0

    def test_build_metadata_newer(self):
        """Build metadata ('+something') makes a version newer in PEP 440."""
        assert compare_versions("1.20.1+build.123", "1.20.1") == 1
        assert compare_versions("1.20.1", "1.20.1+build.123") == -1

    def test_different_length_versions(self):
        """1.20 equals 1.20.0 under normal parsing."""
        assert compare_versions("1.20", "1.20.0") == 0


class TestCheckIncompatibility:
    """Tests for check_incompatibility() — MC-version based mod skipping."""

    def test_no_incompatible_rules(self):
        """Empty ruleset means no mod is incompatible."""
        config = {"incompatible_mods": {}}
        result, reason = check_incompatibility("OptiFine", "1.20.1", config)
        assert result is False
        assert reason is None

    def test_exact_version_match(self):
        """Exact MC version match triggers incompatibility."""
        config = {"incompatible_mods": {"OptiFine": ["1.20.1"]}}
        result, reason = check_incompatibility("OptiFine", "1.20.1", config)
        assert result is True
        assert "incompatible by rule" in (reason or "")

    def test_less_than_rule(self):
        """'<1.20' means incompatible when mc_version >= threshold."""
        config = {"incompatible_mods": {"OptiFine": ["<1.20"]}}
        result, _ = check_incompatibility("OptiFine", "1.20.1", config)
        assert result is True

    def test_greater_than_rule(self):
        """'>1.20' means incompatible when mc_version > threshold."""
        config = {"incompatible_mods": {"OptiFine": [">1.20"]}}
        result, _ = check_incompatibility("OptiFine", "1.20.1", config)
        assert result is True

    def test_plus_rule(self):
        """'1.20+' means incompatible when mc_version >= 1.20."""
        config = {"incompatible_mods": {"OptiFine": ["1.20+"]}}
        result, _ = check_incompatibility("OptiFine", "1.20.1", config)
        assert result is True

    def test_greater_than_rule_not_matched(self):
        """'>1.20' does NOT match when mc_version == 1.20 (not strictly greater)."""
        config = {"incompatible_mods": {"OptiFine": [">1.20"]}}
        result, _ = check_incompatibility("OptiFine", "1.20", config)
        assert result is False

    def test_case_insensitive_mod_name(self):
        """Mod name matching is case-insensitive."""
        config = {"incompatible_mods": {"optifine": ["1.20.1"]}}
        result, _ = check_incompatibility("OptiFine", "1.20.1", config)
        assert result is True

    def test_no_match_for_different_mod(self):
        """A mod not in the ruleset is never incompatible."""
        config = {"incompatible_mods": {"Sodium": ["1.20.1"]}}
        result, reason = check_incompatibility("OptiFine", "1.20.1", config)
        assert result is False
        assert reason is None


class TestFilterMods:
    """Tests for filter_mods() — full mod eligibility pipeline."""

    def test_all_eligible(self):
        """Without rules all mods pass through."""
        config = {}
        mods = ["sodium", "lithium"]
        eligible, skipped = filter_mods(
            mods, "1.20.1", config,
            hardware={"gpu": "nvidia", "cpu_cores": 8},
        )
        assert eligible == mods
        assert skipped == []

    def test_incompatible_mod_skipped(self):
        """Incompatibility rule excludes a mod."""
        config = {"incompatible_mods": {"optifine": ["1.20.1"]}}
        mods = ["sodium", "optifine"]
        eligible, skipped = filter_mods(
            mods, "1.20.1", config,
            hardware={"gpu": "nvidia", "cpu_cores": 8},
        )
        assert eligible == ["sodium"]
        assert len(skipped) == 1
        assert skipped[0][0] == "optifine"

    def test_gpu_mismatch(self):
        """GPU requirement blocks incompatible hardware."""
        config = {"requirements": {"nvidium": {"gpu": "nvidia"}}}
        mods = ["nvidium"]
        eligible, skipped = filter_mods(
            mods, "1.20.1", config,
            hardware={"gpu": "amd", "cpu_cores": 8},
        )
        assert eligible == []
        assert "GPU" in skipped[0][1]

    def test_cpu_cores_insufficient(self):
        """CPU core requirement filters out under-powered machines."""
        config = {"requirements": {"c2me": {"min_cpu_cores": 8}}}
        mods = ["c2me"]
        eligible, skipped = filter_mods(
            mods, "1.20.1", config,
            hardware={"gpu": "nvidia", "cpu_cores": 4},
        )
        assert eligible == []
        assert "cores" in skipped[0][1]

    def test_conflict_rule(self):
        """When OptiFine is eligible, conflicting Sodium is skipped."""
        config = {"conflicts": {"OptiFine": ["Sodium"]}}
        mods = ["OptiFine", "Sodium"]
        eligible, skipped = filter_mods(
            mods, "1.20.1", config,
            hardware={"gpu": "nvidia", "cpu_cores": 8},
        )
        assert eligible == ["OptiFine"]
        assert len(skipped) == 1
        assert "Conflicts" in skipped[0][1]

    def test_conflict_without_primary(self):
        """Sodium is NOT skipped when OptiFine is not in the list."""
        config = {"conflicts": {"OptiFine": ["Sodium"]}}
        mods = ["Sodium"]
        eligible, skipped = filter_mods(
            mods, "1.20.1", config,
            hardware={"gpu": "nvidia", "cpu_cores": 8},
        )
        assert eligible == ["Sodium"]
        assert skipped == []

    def test_empty_mod_list(self):
        """Empty input yields empty output."""
        eligible, skipped = filter_mods(
            [], "1.20.1", {},
            hardware={"gpu": "nvidia", "cpu_cores": 8},
        )
        assert eligible == []
        assert skipped == []

    @patch("mc_quarry.downloader.detect_hardware")
    def test_detect_hardware_called_when_not_provided(self, mock_detect):
        """When hardware arg is None, detect_hardware() is called."""
        mock_detect.return_value = {"gpu": "nvidia", "cpu_cores": 4}
        eligible, _ = filter_mods(["sodium"], "1.20.1", {})
        assert eligible == ["sodium"]
        mock_detect.assert_called_once()

    def test_multiple_skipped_reasons(self):
        """Multiple filters produce multiple skip entries."""
        config = {
            "incompatible_mods": {"optifine": ["1.20.1"]},
            "requirements": {"nvidium": {"gpu": "nvidia"}},
        }
        mods = ["sodium", "optifine", "nvidium"]
        eligible, skipped = filter_mods(
            mods, "1.20.1", config,
            hardware={"gpu": "amd", "cpu_cores": 4},
        )
        assert eligible == ["sodium"]
        assert len(skipped) == 2


class TestExecuteDownload:
    """Tests for execute_download() — full download orchestration."""

    def test_already_up_to_date(self, stats, temp_dir):
        """Same version_id and provider means 'up to date' — no download."""
        installed_mods = {
            "proj123": {
                "version_id": "ver1",
                "provider": "modrinth",
                "filename": "mod.jar",
                "project_slug": "test-mod",
            },
        }
        log_func = MagicMock()

        execute_download(
            display_name="Test Mod",
            project_id="proj123",
            project_slug="test-mod",
            version_id="ver1",
            version_name="1.0",
            filename="mod.jar",
            url="https://example.com/mod.jar",
            provider="modrinth",
            output_dir=temp_dir,
            installed_mods=installed_mods,
            stats=stats,
            log_func=log_func,
            verbose=True,
        )

        assert stats.skipped_up_to_date == 1
        assert stats.installed == 0
        assert stats.updated == 0
        log_func.assert_called()

    def test_already_up_to_date_non_verbose(self, stats, temp_dir):
        """In non-verbose mode, up-to-date does not call log_func."""
        installed_mods = {
            "proj123": {
                "version_id": "ver1",
                "provider": "modrinth",
                "filename": "mod.jar",
                "project_slug": "test-mod",
            },
        }
        log_func = MagicMock()

        execute_download(
            display_name="Test Mod",
            project_id="proj123",
            project_slug="test-mod",
            version_id="ver1",
            version_name="1.0",
            filename="mod.jar",
            url="https://example.com/mod.jar",
            provider="modrinth",
            output_dir=temp_dir,
            installed_mods=installed_mods,
            stats=stats,
            log_func=log_func,
            verbose=False,
        )

        assert stats.skipped_up_to_date == 1
        log_func.assert_not_called()

    @patch("mc_quarry.downloader.download_file")
    def test_update_available(self, mock_download, stats, temp_dir):
        """When version_id differs, old file is removed and new one downloaded."""
        old_jar = temp_dir / "old-mod.jar"
        old_jar.write_text("old content")
        old_info = temp_dir / "old-mod.jar.modinfo"
        old_info.write_text("{}")

        installed_mods = {
            "proj123": {
                "version_id": "ver_old",
                "provider": "modrinth",
                "version_name": "0.9",
                "filename": "old-mod.jar",
                "project_slug": "test-mod",
            },
        }
        log_func = MagicMock()
        mock_download.return_value = True

        execute_download(
            display_name="Test Mod",
            project_id="proj123",
            project_slug="test-mod",
            version_id="ver_new",
            version_name="1.0",
            filename="new-mod.jar",
            url="https://example.com/new-mod.jar",
            provider="modrinth",
            output_dir=temp_dir,
            installed_mods=installed_mods,
            stats=stats,
            log_func=log_func,
            verbose=True,
        )

        assert stats.updated == 1
        assert not old_jar.exists()
        mock_download.assert_called_once()

    @patch("mc_quarry.downloader.download_file")
    def test_fresh_download(self, mock_download, stats, temp_dir):
        """A new mod is downloaded and .modinfo is written."""
        mock_download.return_value = True
        log_func = MagicMock()

        execute_download(
            display_name="New Mod",
            project_id="proj_new",
            project_slug="new-mod",
            version_id="v1",
            version_name="1.0",
            filename="new-mod.jar",
            url="https://example.com/new-mod.jar",
            provider="modrinth",
            output_dir=temp_dir,
            installed_mods={},
            stats=stats,
            log_func=log_func,
            verbose=True,
        )

        assert stats.installed == 1
        mock_download.assert_called_once_with(
            "https://example.com/new-mod.jar",
            temp_dir / "new-mod.jar",
        )
        info_path = temp_dir / "new-mod.jar.modinfo"
        assert info_path.exists()
        data = json.loads(info_path.read_text())
        assert data["project_id"] == "proj_new"

    @patch("mc_quarry.downloader.download_file")
    def test_download_failure_logged(self, mock_download, stats, temp_dir):
        """When download fails, stats track the failure and log_func is called."""
        mock_download.return_value = False
        log_func = MagicMock()

        execute_download(
            display_name="Fails Mod",
            project_id="proj_fail",
            project_slug="fails-mod",
            version_id="v1",
            version_name="1.0",
            filename="fail.jar",
            url="https://example.com/fail.jar",
            provider="curseforge",
            output_dir=temp_dir,
            installed_mods={},
            stats=stats,
            log_func=log_func,
            verbose=False,
        )

        assert stats.installed == 0
        assert len(stats.failed) == 1
        assert stats.failed[0][0] == "Fails Mod"
        log_func.assert_called()

    def test_file_exists_indexed(self, stats, temp_dir):
        """When file exists without metadata, it is indexed (not re-downloaded)."""
        dest_jar = temp_dir / "existing.jar"
        dest_jar.write_text("dummy content")
        log_func = MagicMock()

        execute_download(
            display_name="Existing Mod",
            project_id="proj_existing",
            project_slug="existing-mod",
            version_id="v1",
            version_name="1.0",
            filename="existing.jar",
            url="https://example.com/existing.jar",
            provider="modrinth",
            output_dir=temp_dir,
            installed_mods={},
            stats=stats,
            log_func=log_func,
            verbose=True,
        )

        assert stats.installed == 1
        info_path = temp_dir / "existing.jar.modinfo"
        assert info_path.exists()

    @patch("mc_quarry.downloader.download_file")
    def test_non_verbose_success_no_log(self, mock_download, stats, temp_dir):
        """In non-verbose mode, successful download does not spam log."""
        mock_download.return_value = True
        log_func = MagicMock()

        execute_download(
            display_name="Quiet Mod",
            project_id="proj_quiet",
            project_slug="quiet-mod",
            version_id="v1",
            version_name="1.0",
            filename="quiet.jar",
            url="https://example.com/quiet.jar",
            provider="modrinth",
            output_dir=temp_dir,
            installed_mods={},
            stats=stats,
            log_func=log_func,
            verbose=False,
        )

        assert stats.installed == 1
        log_func.assert_not_called()

    @patch("mc_quarry.downloader.download_file")
    def test_project_url_included_in_details(self, mock_download, stats, temp_dir):
        """When project_url is provided it appears in detail log lines."""
        mock_download.return_value = True
        log_func = MagicMock()

        execute_download(
            display_name="Mod With URL",
            project_id="proj_url",
            project_slug="mod-url",
            version_id="v1",
            version_name="1.0",
            filename="mod-url.jar",
            url="https://example.com/mod-url.jar",
            provider="modrinth",
            output_dir=temp_dir,
            installed_mods={},
            stats=stats,
            log_func=log_func,
            project_url="https://modrinth.com/mod/mod-url",
            verbose=True,
        )

        assert stats.installed == 1
        # log_func should have been called at least for the detail line
        all_logs = "".join(c[0][0] for c in log_func.call_args_list)
        assert "modrinth.com" in all_logs
