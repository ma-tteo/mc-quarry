#!/usr/bin/env python3
"""
MC Quarry Web Interface

A modern web UI for MC Quarry modpack downloader.
Provides real-time progress updates via WebSocket.

Usage:
    python3 web_interface.py [--host 0.0.0.0] [--port 5000]
"""

import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mc_quarry.api_client import APIClient
from mc_quarry.config_manager import load_config, save_config
from mc_quarry.constants import CATEGORIES as CATEGORY_MAP
from mc_quarry.exceptions import ConfigError
from mc_quarry.downloader import (
    filter_mods,
    read_all_mod_info,
)
from mc_quarry.processor import _process_mod_wrapper
from mc_quarry.ui_manager import detect_hardware
from mc_quarry.utils import DownloadStats

# Minecraft version pattern — kept in sync with main.py:MC_VERSION_PATTERN
MC_VERSION_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)?([+-][a-zA-Z0-9.]+)?$")

# Editable top-level config keys the web UI is allowed to write. Anything
# outside this whitelist passed to POST /api/config is ignored.
EDITABLE_CONFIG_KEYS = {
    "curseforge_api_key",
    "language",
    "install_light_qol",
    "mods_folder",
    "resourcepacks_folder",
    "core_mods",
    "utility_mods",
    "light_qol_mods",
    "curseforge_mods",
    "texture_packs",
    "curseforge_texture_packs",
}

# Type expectations for validation of editable keys.
CONFIG_LIST_KEYS = {
    "core_mods",
    "utility_mods",
    "light_qol_mods",
    "curseforge_mods",
    "texture_packs",
    "curseforge_texture_packs",
}
CONFIG_BOOL_KEYS = {"install_light_qol"}

# Setup Flask app
app = Flask(
    __name__,
    template_folder=Path(__file__).parent / "mc_quarry" / "web" / "templates",
    static_folder=Path(__file__).parent / "mc_quarry" / "web" / "static",
)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
socketio = SocketIO(
    app,
    cors_allowed_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
    async_mode="threading",
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mc-quarry-web")

# Global state — guarded by `state_lock` because it is shared between the
# background download thread and HTTP request handlers (previously unsynchronized).
state_lock = threading.Lock()
download_state = {
    "running": False,
    "progress": 0,
    "current_mod": "",
    "status": "idle",  # idle, running, complete, error
    "stats": {"installed": 0, "updated": 0, "skipped": 0, "failed": 0, "not_found": 0},
    "summary": {"failed": [], "not_found": [], "skipped_incompatible": 0},
    "log": [],
    "error": None,
}


def _snapshot_state() -> Dict[str, Any]:
    """Return a shallow copy of download_state under the lock (thread-safe read)."""
    with state_lock:
        return {
            k: (v.copy() if isinstance(v, (dict, list)) else v)
            for k, v in download_state.items()
        }


def _reset_state() -> None:
    """Reset download_state to a fresh idle snapshot (mutates in-place)."""
    with state_lock:
        download_state.clear()
        download_state.update(
            running=False,
            progress=0,
            current_mod="",
            status="idle",
            stats={"installed": 0, "updated": 0, "skipped": 0, "failed": 0, "not_found": 0},
            summary={"failed": [], "not_found": [], "skipped_incompatible": 0},
            log=[],
            error=None,
        )


def emit_log(message: str, level: str = "info"):
    """Emit log message to all connected clients."""
    socketio.emit("log", {"message": message, "level": level})


def emit_progress(current: int, total: int, mod_name: str = ""):
    """Emit progress update to all connected clients."""
    pct = (current / total * 100) if total > 0 else 0
    socketio.emit(
        "progress",
        {
            "current": current,
            "total": total,
            "percentage": pct,
            "current_mod": mod_name,
        },
    )


def emit_stats(stats: Dict[str, int]):
    """Emit stats update to all connected clients."""
    socketio.emit("stats", stats)


def run_download_task(config: Dict[str, Any], mc_version: str, categories: list):
    """Background task to run the download process."""
    try:
        with state_lock:
            download_state["running"] = True
            download_state["status"] = "running"
            download_state["error"] = None

        client = APIClient(cf_api_key=config.get("curseforge_api_key", ""))
        base_dir = Path(__file__).parent / "modpack"
        all_stats = DownloadStats()

        # Detect hardware once (the CLI does the same) and pass it to filter_mods
        # so mods are not re-detected on every iteration.
        hardware = detect_hardware()

        # Build list of all mods to process
        all_mods = []
        for category in categories:
            mod_list = config.get(category, [])
            for mod in mod_list:
                all_mods.append((category, mod))

        total_mods = len(all_mods)
        processed = 0

        for category, mod_name in all_mods:
            with state_lock:
                if not download_state["running"]:
                    break
                download_state["current_mod"] = mod_name
            emit_progress(processed, total_mods, mod_name)

            # Resolve output dir / project type / provider from CATEGORY_MAP.
            # Unknown categories fall back to core_mods (modrinth, mod).
            cat_cfg = CATEGORY_MAP.get(
                category, CATEGORY_MAP["core_mods"]
            )
            out_dir = base_dir / f"{cat_cfg['subdir']}_{mc_version}"
            project_type = cat_cfg["project_type"]
            provider = cat_cfg["provider"]

            out_dir.mkdir(parents=True, exist_ok=True)
            installed = read_all_mod_info(out_dir)

            # Filter mods (hardware passed explicitly → no per-mod re-detection)
            active_list, skipped = filter_mods([mod_name], mc_version, config, hardware=hardware)

            # Handle skipped mods
            for skip_name, reason in skipped:
                emit_log(f"Skipped: {skip_name} — {reason}", "warning")
                all_stats.skipped_incompatible += 1
                processed += 1
                emit_progress(processed, total_mods, skip_name)
                continue

            if not active_list:
                continue

            # Download mod
            try:
                # Use main's wrapper to handle BOTH Modrinth and CurseForge flawlessly
                # Interface adapter to route CLI logs to WebSockets
                class WebUI:
                    def log(self, msg):
                        clean_msg = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', msg)
                        emit_log(clean_msg, "info")
                    def set_status(self, msg):
                        pass
                    def update_progress(self):
                        pass

                web_ui_handler = WebUI()

                _process_mod_wrapper(
                    client,
                    mod_name,
                    mc_version,
                    project_type,
                    out_dir,
                    installed,
                    all_stats,
                    provider,
                    verbose=True,
                    ui_handler=web_ui_handler,
                )

                processed += 1
                emit_progress(processed, total_mods, mod_name)
                emit_stats(
                    {
                        "installed": all_stats.installed,
                        "updated": all_stats.updated,
                        "skipped": all_stats.skipped_up_to_date,
                        "failed": len(all_stats.failed),
                        "not_found": len(all_stats.not_found),
                    }
                )

            except Exception as e:
                emit_log(f"Error downloading {mod_name}: {e}", "error")
                all_stats.failed.append((mod_name, str(e)))
                processed += 1

        final_stats = {
            "installed": all_stats.installed,
            "updated": all_stats.updated,
            "skipped": all_stats.skipped_up_to_date,
            "failed": len(all_stats.failed),
            "not_found": len(all_stats.not_found),
        }
        final_summary = {
            "failed": list(all_stats.failed),
            "not_found": list(all_stats.not_found),
            "skipped_incompatible": all_stats.skipped_incompatible,
        }

        with state_lock:
            download_state["stats"] = final_stats
            download_state["summary"] = final_summary

        emit_stats(final_stats)
        # Push the final report to trigger the summary modal on the client.
        socketio.emit("complete", {"stats": final_stats, **final_summary})
        with state_lock:
            download_state["status"] = "complete"
        emit_log("Download complete!", "success")

    except Exception as e:
        with state_lock:
            download_state["error"] = str(e)
            download_state["status"] = "error"
        emit_log(f"Error: {e}", "error")
        logger.exception("Download task failed")

    finally:
        with state_lock:
            download_state["running"] = False


@app.route("/")
def index():
    """Serve the main web interface."""
    return render_template("index.html")


@app.route("/api/status")
def get_status():
    """Get current download status."""
    snap = _snapshot_state()
    # Don't leak the heavy log buffer; clients receive logs via Socket.IO.
    snap.pop("log", None)
    return jsonify(snap)


@app.route("/api/hardware")
def get_hardware():
    """Detect and return system hardware used for mod filtering."""
    hw = detect_hardware()
    return jsonify({"gpu": hw.get("gpu", "generic"), "cpu_cores": hw.get("cpu_cores", 1)})


@app.route("/api/summary")
def get_summary():
    """Return the per-mod summary of the last download (failures, not found, skips)."""
    snap = _snapshot_state()
    return jsonify(snap.get("summary", {"failed": [], "not_found": [], "skipped_incompatible": 0}))


@app.route("/api/config")
def get_config():
    """Get current configuration."""
    try:
        config = load_config()
    except ConfigError as e:
        return jsonify({"error": str(e)}), 500
    # Don't send API key to client
    if "curseforge_api_key" in config:
        config["curseforge_api_key"] = "***" if config["curseforge_api_key"] else ""
    return jsonify(config)


@app.route("/api/config", methods=["POST"])
def update_config():
    """Update configuration with minimal schema validation.

    Only editable keys (EDITABLE_CONFIG_KEYS) are accepted; unknown keys are
    ignored to prevent clobbering rule sections. List keys must be lists of
    strings; boolean keys must be booleans.
    """
    try:
        new_config = request.json or {}
        config = load_config()
    except ConfigError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    try:
        for key, value in new_config.items():
            if key not in EDITABLE_CONFIG_KEYS:
                continue
            if key in CONFIG_LIST_KEYS and not (
                isinstance(value, list)
                and all(isinstance(x, str) for x in value)
            ):
                return (
                    jsonify({"success": False, "error": f"'{key}' must be a list of strings"}),
                    400,
                )
            if key in CONFIG_BOOL_KEYS and not isinstance(value, bool):
                return (
                    jsonify({"success": False, "error": f"'{key}' must be a boolean"}),
                    400,
                )
            config[key] = value
        save_config(config)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/start", methods=["POST"])
def start_download():
    """Start download process."""
    with state_lock:
        if download_state["running"]:
            return jsonify({"success": False, "error": "Download already running"}), 400

    data = request.json or {}
    mc_version = (data.get("version") or "").strip()
    if not MC_VERSION_PATTERN.match(mc_version):
        return jsonify({"success": False, "error": "Invalid Minecraft version format"}), 400

    categories = data.get("categories", ["core_mods", "utility_mods", "light_qol_mods"])
    if not isinstance(categories, list) or not categories:
        return jsonify({"success": False, "error": "At least one category is required"}), 400

    # Reset state for a fresh run
    _reset_state()

    try:
        config = load_config()
    except ConfigError as e:
        return jsonify({"success": False, "error": str(e)}), 500

    # Start background thread
    thread = threading.Thread(
        target=run_download_task, args=(config, mc_version, categories), daemon=True
    )
    thread.start()

    with state_lock:
        download_state["running"] = True
        download_state["status"] = "running"

    return jsonify({"success": True})


@app.route("/api/stop", methods=["POST"])
def stop_download():
    """Stop download process."""
    with state_lock:
        download_state["running"] = False
    emit_log("Stopping download...", "warning")
    return jsonify({"success": True})


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")
    emit("connected", {"message": "Connected to MC Quarry Web Interface"})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MC Quarry Web Interface")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           MC Quarry Web Interface                         ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Starting server...                                       ║
    ║                                                           ║
    ║  Open in browser: http://{args.host}:{args.port}                    ║
    ║                                                           ║
    ║  Press Ctrl+C to stop                                   ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    socketio.run(
        app,
        host=args.host,
        port=args.port,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
