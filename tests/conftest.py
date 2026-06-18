"""Shared test fixtures and configuration."""

import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from mc_quarry.utils import DownloadStats


@pytest.fixture
def stats() -> DownloadStats:
    """Fresh DownloadStats instance for each test."""
    return DownloadStats()


@pytest.fixture
def temp_dir() -> Path:
    """Temporary directory for download tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def empty_config() -> Dict[str, Any]:
    return {}


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    return {
        "language": "en",
        "install_performance_mods": True,
        "install_light_qol": False,
        "mods_folder": "",
        "resourcepacks_folder": "",
        "curseforge_api_key": "",
        "performance_mods": ["sodium", "lithium"],
        "light_qol_mods": [],
        "texture_packs": [],
        "curseforge_texture_packs": [],
    }
