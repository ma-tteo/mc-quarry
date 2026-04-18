#!/usr/bin/env python3
"""
MC Quarry Web Interface

A modern web UI for MC Quarry modpack downloader.
Provides real-time progress updates via WebSocket.

Usage:
    python3 web_interface.py [--host 0.0.0.0] [--port 5000]
"""

import os
import sys
import json
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mc_quarry.config_manager import load_config, save_config
from mc_quarry.api_client import APIClient
from mc_quarry.downloader import (
    read_all_mod_info,
    filter_mods,
    execute_download,
    download_file,
    write_mod_info,
)
from mc_quarry.utils import DownloadStats, BColors
from mc_quarry.ui_manager import get_string

# Setup Flask app
app = Flask(
    __name__,
    template_folder=Path(__file__).parent / "mc_quarry" / "web" / "templates",
    static_folder=Path(__file__).parent / "mc_quarry" / "web" / "static",
)
app.config["SECRET_KEY"] = "mc-quarry-secret-key-change-in-production"
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
                if provider == "modrinth":
                    # Search for mod
                    search_result = client.search_modrinth(
                        mod_name, project_type, limit=1
                    )
                    if (
                        not search_result
                        or "hits" not in search_result
                        or not search_result["hits"]
                    ):
                        emit_log(f"❌ Not found: {mod_name}", "error")
                        all_stats.not_found.append(mod_name)
                        processed += 1
                        continue

                    hit = search_result["hits"][0]
                    project_slug = hit.get("slug", "")
                    project_id = hit.get("id", "")
                    title = hit.get("title", mod_name)

                    # Get version
                    # For resource packs, don't specify loader
                    loader = "fabric" if project_type == "mod" else None
                    version = client.find_modrinth_version(
                        project_id, mc_version, loader=loader
                    )

                    # If no version found with loader, try without loader (for resource packs)
                    if not version and loader:
                        version = client.find_modrinth_version(
                            project_id, mc_version, loader=None
                        )

                    # If still no version, try with force_latest
                    if not version:
                        version = client.find_modrinth_version(
                            project_id, mc_version, loader=loader, force_latest=True
                        )

                    if not version:
                        emit_log(f"❌ No compatible version: {title}", "error")
                        all_stats.failed.append((title, "No compatible version"))
                        processed += 1
                        continue

                    # Get file
                    file_info = client.pick_file_from_version(version)
                    if not file_info:
                        emit_log(f"❌ No file: {title}", "error")
                        all_stats.failed.append((title, "No file"))
                        processed += 1
                        continue

                    # Check if already installed
                    installed_data = installed.get(project_id) or installed.get(
                        project_slug
                    )
                    if (
                        installed_data
                        and installed_data.get("version_id") == version["id"]
                    ):
                        emit_log(f"✨ {title} — ✅ Up to date", "success")
                        all_stats.skipped_up_to_date += 1
                        processed += 1
                        emit_progress(processed, total_mods, title)
                        continue

                    # Download
                    emit_log(f"✨ {title} — 📥 Downloading...", "info")
                    dest_path = out_dir / file_info["filename"]

                    if download_file(file_info["url"], dest_path):
                        write_mod_info(
                            dest_path,
                            project_id,
                            project_slug,
                            version["id"],
                            version["name"],
                            file_info["filename"],
                            "modrinth",
                        )
                        emit_log(f"✨ {title} — ✅ Downloaded", "success")
                        all_stats.installed += 1
                    else:
                        emit_log(f"✨ {title} — ❌ Failed", "error")
                        all_stats.failed.append((title, "Download failed"))

                    processed += 1
                    emit_progress(processed, total_mods, title)
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
    categories = data.get("categories", ["mods", "light_qol_mods"])

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
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    main()
