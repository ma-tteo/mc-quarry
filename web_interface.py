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
from mc_quarry.downloader import (
    filter_mods,
    read_all_mod_info,
)
from mc_quarry.processor import _process_mod_wrapper
from mc_quarry.utils import DownloadStats

# Setup Flask app
app = Flask(
    __name__,
    template_folder=Path(__file__).parent / "mc_quarry" / "web" / "templates",
    static_folder=Path(__file__).parent / "mc_quarry" / "web" / "static",
)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mc-quarry-web")

# Global state
download_state = {
    "running": False,
    "progress": 0,
    "current_mod": "",
    "status": "idle",  # idle, running, complete, error
    "stats": {"installed": 0, "updated": 0, "skipped": 0, "failed": 0, "not_found": 0},
    "log": [],
    "error": None,
}


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
    global download_state

    try:
        download_state["running"] = True
        download_state["status"] = "running"
        download_state["error"] = None

        client = APIClient(cf_api_key=config.get("curseforge_api_key", ""))
        base_dir = Path(__file__).parent / "modpack"
        all_stats = DownloadStats()

        # Build list of all mods to process
        all_mods = []
        for category in categories:
            mod_list = config.get(category, [])
            for mod in mod_list:
                all_mods.append((category, mod))

        total_mods = len(all_mods)
        processed = 0

        for category, mod_name in all_mods:
            if not download_state["running"]:
                break

            download_state["current_mod"] = mod_name
            emit_progress(processed, total_mods, mod_name)

            # Determine output directory and project type
            if "curseforge" in category:
                out_dir = base_dir / f"mods_core_{mc_version}"
                project_type = "mod"
                provider = "curseforge"
            elif "light_qol" in category:
                out_dir = base_dir / f"mods_light_qol_{mc_version}"
                project_type = "mod"
                provider = "modrinth"
            elif "utility" in category:
                out_dir = base_dir / f"mods_utility_{mc_version}"
                project_type = "mod"
                provider = "modrinth"
            elif "texture" in category:
                out_dir = base_dir / f"texture_packs_{mc_version}"
                project_type = "resourcepack"
                provider = "modrinth"
            else:
                out_dir = base_dir / f"mods_core_{mc_version}"
                project_type = "mod"
                provider = "modrinth"

            out_dir.mkdir(parents=True, exist_ok=True)
            installed = read_all_mod_info(out_dir)

            # Filter mods
            active_list, skipped = filter_mods([mod_name], mc_version, config)

            # Handle skipped mods
            for skip_name, reason in skipped:
                emit_log(f"⚠️  Skipped: {skip_name} - {reason}", "warning")
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
                    ui_handler=web_ui_handler
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
                emit_log(f"❌ Error downloading {mod_name}: {e}", "error")
                all_stats.failed.append((mod_name, str(e)))
                processed += 1

        download_state["stats"] = {
            "installed": all_stats.installed,
            "updated": all_stats.updated,
            "skipped": all_stats.skipped_up_to_date,
            "failed": len(all_stats.failed),
            "not_found": len(all_stats.not_found),
        }

        emit_stats(download_state["stats"])
        download_state["status"] = "complete"
        emit_log("✅ Download complete!", "success")

    except Exception as e:
        download_state["error"] = str(e)
        download_state["status"] = "error"
        emit_log(f"❌ Error: {e}", "error")
        logger.exception("Download task failed")

    finally:
        download_state["running"] = False


@app.route("/")
def index():
    """Serve the main web interface."""
    return render_template("index.html")


@app.route("/api/status")
def get_status():
    """Get current download status."""
    return jsonify(
        {
            "running": download_state["running"],
            "progress": download_state["progress"],
            "current_mod": download_state["current_mod"],
            "status": download_state["status"],
            "stats": download_state["stats"],
            "error": download_state["error"],
        }
    )


@app.route("/api/config")
def get_config():
    """Get current configuration."""
    config = load_config()
    # Don't send API key to client
    if "curseforge_api_key" in config:
        config["curseforge_api_key"] = "***" if config["curseforge_api_key"] else ""
    return jsonify(config)


@app.route("/api/config", methods=["POST"])
def update_config():
    """Update configuration."""
    try:
        new_config = request.json
        config = load_config()
        config.update(new_config)
        save_config(config)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/start", methods=["POST"])
def start_download():
    """Start download process."""
    global download_state

    if download_state["running"]:
        return jsonify({"success": False, "error": "Download already running"}), 400

    data = request.json or {}
    mc_version = data.get("version", "1.21.11")
    categories = data.get("categories", ["core_mods", "utility_mods", "light_qol_mods"])

    # Reset state
    download_state = {
        "running": False,
        "progress": 0,
        "current_mod": "",
        "status": "idle",
        "stats": {
            "installed": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "not_found": 0,
        },
        "log": [],
        "error": None,
    }

    config = load_config()

    # Start background thread
    thread = threading.Thread(
        target=run_download_task, args=(config, mc_version, categories), daemon=True
    )
    thread.start()

    download_state["running"] = True
    download_state["status"] = "running"

    return jsonify({"success": True})


@app.route("/api/stop", methods=["POST"])
def stop_download():
    """Stop download process."""
    global download_state
    download_state["running"] = False
    emit_log("⏹️  Stopping download...", "warning")
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
