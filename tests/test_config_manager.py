"""Tests for mc_quarry.config_manager."""

import json

import pytest

from mc_quarry.config_manager import load_config


def test_load_config_returns_dict():
    """Load config returns a dict."""
    config = load_config()
    assert isinstance(config, dict)
    assert "language" in config


def test_save_and_load(temp_dir):
    """Round-trip save and load preserves config data."""
    import mc_quarry.config_manager as cm

    config_path = temp_dir / "test_config.json"
    original = cm.CONFIG_FILE
    cm.CONFIG_FILE = str(config_path)

    try:
        test_config = {"language": "en", "mods_folder": "/tmp/mods", "core_mods": ["sodium"]}
        cm.save_config(test_config, str(config_path))
        loaded = cm.load_config(str(config_path))
        assert loaded["language"] == "en"
        assert loaded["mods_folder"] == "/tmp/mods"
        assert "sodium" in loaded.get("core_mods", [])
    finally:
        cm.CONFIG_FILE = original


def test_load_config_preserves_unknown_keys(temp_dir):
    """Unknown keys in config file are preserved."""
    import mc_quarry.config_manager as cm

    config_path = temp_dir / "test_config.json"
    original = cm.CONFIG_FILE
    cm.CONFIG_FILE = str(config_path)

    # Write config with extra field
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"unknown_field": "test", "language": "it"}))

    try:
        loaded = cm.load_config(str(config_path))
        assert loaded.get("unknown_field") == "test"
        assert loaded["language"] == "it"
    finally:
        cm.CONFIG_FILE = original


def test_multiple_save_calls(temp_dir):
    """Multiple save calls don't lose data."""
    import mc_quarry.config_manager as cm

    config_path = temp_dir / "test_config.json"
    original = cm.CONFIG_FILE
    cm.CONFIG_FILE = str(config_path)

    try:
        cm.save_config({"language": "it", "mods_folder": "/a"}, str(config_path))
        cm.save_config({"language": "en", "mods_folder": "/b"}, str(config_path))
        loaded = cm.load_config(str(config_path))
        assert loaded["language"] == "en"
        assert loaded["mods_folder"] == "/b"
    finally:
        cm.CONFIG_FILE = original


class TestLoadConfigEdgeCases:
    """Edge cases for config loading."""

    def test_corrupted_json_creates_backup_and_exits(self, temp_dir):
        """Corrupted JSON triggers sys.exit and creates .bak backup."""
        import mc_quarry.config_manager as cm

        config_path = temp_dir / "test_config.json"
        config_path.write_text('{"broken": ')
        original = cm.CONFIG_FILE
        cm.CONFIG_FILE = str(config_path)
        try:
            with pytest.raises(SystemExit):
                cm.load_config(str(config_path))
            assert config_path.with_suffix(".json.bak").exists()
        finally:
            cm.CONFIG_FILE = original

    def test_restore_from_clean_copy(self, temp_dir):
        """Missing config restored from config_clean.json."""
        import mc_quarry.config_manager as cm

        config_path = temp_dir / "test_config.json"
        clean_path = temp_dir / "config_clean.json"
        clean_path.write_text('{"language": "it", "mods_folder": "/restored"}')
        original_clean = cm.CLEAN_CONFIG_FILE
        original_config = cm.CONFIG_FILE
        cm.CLEAN_CONFIG_FILE = str(clean_path)
        cm.CONFIG_FILE = str(config_path)
        try:
            loaded = cm.load_config(str(config_path))
            assert loaded["mods_folder"] == "/restored"
            assert loaded["language"] == "it"
        finally:
            cm.CLEAN_CONFIG_FILE = original_clean
            cm.CONFIG_FILE = original_config

    def test_clean_restore_failure_logged(self, temp_dir, caplog):
        """Clean restore failure is logged and load returns None."""
        import mc_quarry.config_manager as cm

        config_path = temp_dir / "nonexistent" / "test_config.json"
        clean_path = temp_dir / "config_clean.json"
        clean_path.write_text('{"language": "en"}')
        original_clean = cm.CLEAN_CONFIG_FILE
        original_config = cm.CONFIG_FILE
        cm.CLEAN_CONFIG_FILE = str(clean_path)
        cm.CONFIG_FILE = str(config_path)
        try:
            loaded = cm.load_config(str(config_path))
            assert loaded is None
            assert any("Failed to restore" in msg for msg in caplog.messages)
        finally:
            cm.CLEAN_CONFIG_FILE = original_clean
            cm.CONFIG_FILE = original_config

    def test_missing_file_no_clean_returns_none(self, temp_dir, caplog):
        """Neither config nor clean exists: load_config returns None."""
        import logging

        import mc_quarry.config_manager as cm

        caplog.set_level(logging.INFO)
        config_path = temp_dir / "nonexistent_config.json"
        original_clean = cm.CLEAN_CONFIG_FILE
        cm.CLEAN_CONFIG_FILE = str(temp_dir / "nonexistent_clean.json")
        try:
            loaded = cm.load_config(str(config_path))
            assert loaded is None
            assert any("not found" in msg for msg in caplog.messages)
        finally:
            cm.CLEAN_CONFIG_FILE = original_clean

    def test_user_config_merged_with_defaults(self, temp_dir):
        """Partial user config fills missing keys from defaults."""
        import mc_quarry.config_manager as cm

        config_path = temp_dir / "test_config.json"
        config_path.write_text(json.dumps({"language": "it"}))
        original = cm.CONFIG_FILE
        original_clean = cm.CLEAN_CONFIG_FILE
        cm.CONFIG_FILE = str(config_path)
        cm.CLEAN_CONFIG_FILE = str(temp_dir / "nonexistent_clean.json")
        try:
            loaded = cm.load_config(str(config_path))
            assert loaded["language"] == "it"
            assert loaded["core_mods"] == []
            assert loaded["curseforge_api_key"] == ""
        finally:
            cm.CONFIG_FILE = original
            cm.CLEAN_CONFIG_FILE = original_clean


class TestSaveConfigEdgeCases:
    """Edge cases for config saving."""

    def test_save_config_oserror_logged(self, temp_dir, caplog):
        """Read-only directory raises OSError which is logged."""
        import mc_quarry.config_manager as cm

        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        config_path = readonly_dir / "config.json"
        try:
            cm.save_config({"test": "data"}, str(config_path))
            assert any("Could not save config" in msg for msg in caplog.messages)
        finally:
            readonly_dir.chmod(0o755)

    def test_save_config_round_trip(self, temp_dir):
        """Save then load produces identical data for saved keys."""
        import mc_quarry.config_manager as cm

        config_path = temp_dir / "test_config.json"
        original_data = {
            "language": "en",
            "mods_folder": "/tmp/test",
            "core_mods": ["sodium"],
        }
        cm.save_config(original_data, str(config_path))
        loaded = cm.load_config(str(config_path))
        for k, v in original_data.items():
            assert loaded.get(k) == v
