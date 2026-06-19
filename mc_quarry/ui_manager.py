import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict

from .translations import (  # noqa: F401
    detect_language,
    get_string,
    get_string_no_ansi,
    set_selected_language,
)
from .utils import BOX_WIDTH, BColors, get_visual_length

logger = logging.getLogger("mc-quarry")


class TerminalUI:
    """
    Manages terminal output with a persistent progress bar at the bottom
    and scrolling logs above. Thread-safe.
    """

    def __init__(self):
        """Initialize the terminal UI with default values."""
        self._lock = threading.Lock()
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_status = "Initializing..."
        self.start_time = time.time()
        self._bar_length = 40
        self._spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_idx = 0
        self._last_update = 0

    def set_total(self, total: int):
        """Set the total number of tasks and reset progress."""
        with self._lock:
            self.total_tasks = total
            self.completed_tasks = 0
            self.start_time = time.time()

    def update_progress(self, increment: int = 1):
        """Advance the progress counter and redraw the progress bar."""
        with self._lock:
            self.completed_tasks += increment
            self._redraw_progress_bar()

    def set_status(self, message: str):
        """Update the status message displayed on the progress bar."""
        with self._lock:
            self.current_status = message
            self._redraw_progress_bar()

    def log(self, message: str):
        """Print a log message above the progress bar."""
        with self._lock:
            # Clear progress bar line
            sys.stdout.write("\r\033[K")
            # Print message
            sys.stdout.write(f"{message}\n")
            # Redraw progress bar
            self._redraw_progress_bar()

    def _redraw_progress_bar(self):
        """Redraw the progress bar at the current cursor position (bottom)."""
        if self.total_tasks == 0:
            return

        now = time.time()
        # Limit update rate to 10fps to prevent flickering
        if now - self._last_update < 0.1 and self.completed_tasks < self.total_tasks:
            return
        self._last_update = now

        percentage = self.completed_tasks / self.total_tasks
        filled_length = int(self._bar_length * percentage)

        # Color gradient based on percentage
        color = BColors.FAIL
        if percentage > 0.33:
            color = BColors.WARNING
        if percentage > 0.66:
            color = BColors.OKCYAN
        if percentage >= 1.0:
            color = BColors.OKGREEN

        bar = "█" * filled_length + "░" * (self._bar_length - filled_length)

        spinner = self._spinner[self._spinner_idx]
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner)

        # Format: [Spinner] [Bar] N/Total (Pct%) Status
        status_line = (
            f"\r{BColors.OKBLUE}{spinner}{BColors.ENDC} "
            f"{color}{bar}{BColors.ENDC} "
            f"{self.completed_tasks}/{self.total_tasks} "
            f"({int(percentage * 100)}%) "
            f"{BColors.DIM}{self.current_status[:40]}{BColors.ENDC}"
        )

        # Pad with spaces to clear previous line content
        try:
            term_width = os.get_terminal_size().columns
            padding = max(0, term_width - len(get_string_no_ansi(status_line)))
            sys.stdout.write(status_line + " " * padding)
        except (OSError, ValueError):
            # Fallback if terminal size cannot be determined
            sys.stdout.write(status_line)

        sys.stdout.flush()

    def finish(self):
        """Clean up the progress bar line."""
        with self._lock:
            sys.stdout.write("\r\033[K")  # Clear line
            sys.stdout.flush()


# Global UI instance
ui = TerminalUI()


def print_banner():
    """Print ASCII art banner."""
    banner = rf"""{BColors.OKCYAN}
    __  _________     ____                             
   /  |/  / ____/    / __ \__  ______ _____________  __
  / /|_/ / /  ______/ / / / / / / __ `/ ___/ ___/ / / /
 / /  / / /__/_____/ /_/ / /_/ / /_/ / /  / /  / /_/ / 
/_/  /_/\____/     \___\_\__,_/\__,_/_/  /_/   \__, /  
                                              /____/   
{BColors.ENDC}"""
    print(banner)


def print_section_header(title: str, icon: str = "", color: str = BColors.OKCYAN):
    """Print a section header with Unicode borders."""
    inner_width = BOX_WIDTH - 2
    content = f" {icon}  {title}" if icon else f" {title}"
    v_len = get_visual_length(content)
    padding = inner_width - v_len
    if padding < 0:
        padding = 0

    print(f"\n{color}╔{'═' * inner_width}╗{BColors.ENDC}")
    print(
        f"{color}║{BColors.ENDC}{BColors.BOLD}{content}{BColors.ENDC}{' ' * padding}{color}║{BColors.ENDC}"
    )
    print(f"{color}╚{'═' * inner_width}╝{BColors.ENDC}")


def print_progress_bar(current: int, total: int, width: int = 30, label: str = ""):
    """Print a progress bar with percentage. (Currently unused)"""
    if total == 0:
        return
    ratio = current / total
    filled = int(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(ratio * 100)

    if pct < 33:
        bar_color = BColors.FAIL
    elif pct < 66:
        bar_color = BColors.WARNING
    else:
        bar_color = BColors.OKGREEN

    line = f"\r  {bar_color}{bar}{BColors.ENDC}  {BColors.BOLD}{current}{BColors.ENDC}/{total}  {BColors.DIM}[{pct}%]{BColors.ENDC}"
    if label:
        line += f"  {BColors.DIM}{label}{BColors.ENDC}"
    sys.stdout.write(line + " " * 10)
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()


def detect_hardware() -> Dict[str, Any]:
    """Detect system hardware (GPU vendor and CPU core count)."""
    import subprocess

    hardware = {"gpu": "generic", "cpu_cores": os.cpu_count() or 1}

    try:
        if sys.platform == "linux":
            # Try lspci first (most common on Linux)
            try:
                output = (
                    subprocess.check_output(
                        ["lspci"], stderr=subprocess.STDOUT, timeout=10
                    )
                    .decode("utf-8")
                    .lower()
                )
                if "nvidia" in output:
                    hardware["gpu"] = "nvidia"
                elif "amd" in output or "ati" in output:
                    hardware["gpu"] = "amd"
                elif "intel" in output:
                    hardware["gpu"] = "intel"
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ) as e:
                # Fallback: check /sys/class/drm (works on most Linux without lspci)
                logger.debug(f"lspci failed, trying /sys/module fallback: {e}")
                try:
                    for driver in ["nvidia", "radeon", "amdgpu", "i915"]:
                        if Path(f"/sys/module/{driver}").exists():
                            hardware["gpu"] = (
                                "nvidia"
                                if driver == "nvidia"
                                else "amd"
                                if driver in ["radeon", "amdgpu"]
                                else "intel"
                            )
                            break
                except Exception as e:
                    logger.debug(f"Hardware detection via /sys/module failed: {e}")
        elif sys.platform == "win32":
            # Windows: use wmic
            try:
                output = (
                    subprocess.check_output(
                        ["wmic", "path", "win32_videocontroller", "get", "name"],
                        stderr=subprocess.STDOUT,
                        timeout=10,
                    )
                    .decode("utf-8", errors="ignore")
                    .lower()
                )
                if "nvidia" in output:
                    hardware["gpu"] = "nvidia"
                elif "amd" in output or "ati" in output or "radeon" in output:
                    hardware["gpu"] = "amd"
                elif "intel" in output:
                    hardware["gpu"] = "intel"
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ) as e:
                logger.debug(f"Windows GPU detection failed: {e}")
        elif sys.platform == "darwin":
            # macOS: use system_profiler
            try:
                output = (
                    subprocess.check_output(
                        ["system_profiler", "SPDisplaysDataType"],
                        stderr=subprocess.STDOUT,
                        timeout=10,
                    )
                    .decode("utf-8", errors="ignore")
                    .lower()
                )
                if "amd" in output or "radeon" in output:
                    hardware["gpu"] = "amd"
                elif "intel" in output:
                    hardware["gpu"] = "intel"
                elif "apple" in output:
                    hardware["gpu"] = "apple"  # Apple Silicon integrated
                elif "nvidia" in output:
                    hardware["gpu"] = "nvidia"
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ) as e:
                logger.debug(f"macOS GPU detection failed: {e}")
    except Exception as e:
        # Log unexpected errors but keep generic fallback
        logger.debug(f"Hardware detection failed: {e}")

    return hardware


def print_download_summary(stats: Any) -> None:
    """Print download summary with installed/updated/skipped/failed statistics."""
    inner_width = BOX_WIDTH - 2
    indent_val = 2

    def print_row(content, row_color=BColors.OKBLUE, indent=indent_val):
        """Print a formatted row inside the summary box."""
        v_len = get_visual_length(content)
        padding = inner_width - v_len - indent
        print(
            f"{row_color}║{BColors.ENDC}{' ' * indent}{content}{' ' * max(0, padding)}{row_color}║{BColors.ENDC}"
        )

    # Calculate totals
    total_processed = stats.installed + stats.updated + stats.skipped_up_to_date
    total_skipped = (
        stats.skipped_incompatible
        + len(stats.not_found)
        + len([f for f in stats.failed])
    )
    total = total_processed + total_skipped

    print(f"\n{BColors.OKBLUE}╔{'═' * inner_width}╗{BColors.ENDC}")

    # Title
    title = f" DOWNLOAD COMPLETE ({total} mods) "
    title_padding = (inner_width - len(title)) // 2
    print(
        f"{BColors.OKBLUE}║{BColors.ENDC}{' ' * title_padding}{BColors.BOLD}{BColors.OKCYAN}{title}{BColors.ENDC}{' ' * (inner_width - title_padding - len(title))}{BColors.OKBLUE}║{BColors.ENDC}"
    )

    print(f"{BColors.OKBLUE}╠{'═' * inner_width}╣{BColors.ENDC}")

    # ASCII ART Header
    content_header = [
        rf"{BColors.HEADER}{BColors.BOLD} ___ ___ ___ ___ ___ ___  _  _   ___ _   _ __  __ __  __   _   _____   __ {BColors.ENDC}",
        rf"{BColors.HEADER}{BColors.BOLD}/ __| __/ __/ __|_ _/ _ \| \| | / __| | | |  \/  |  \/  | /_\ | _ \ \ / / {BColors.ENDC}",
        rf"{BColors.HEADER}{BColors.BOLD}\__ \ _|\__ \__ \| | (_) | .` | \__ \ |_| | |\/| | |\/| |/ _ \|   /\ V /  {BColors.ENDC}",
        rf"{BColors.HEADER}{BColors.BOLD}|___/___|___/___/___\___/|_|\_| |___/\___/|_|  |_|_|  |_/_/ \_\_|_ \ |_|   {BColors.ENDC}",
    ]
    for line in content_header:
        print_row(line, indent=indent_val)

    print(f"{BColors.OKBLUE}╠{'═' * inner_width}╣{BColors.ENDC}")

    # Statistics
    print_row(
        f"{BColors.OKGREEN}✅ Installed:     {BColors.BOLD}{stats.installed:>5}{BColors.ENDC}"
    )
    print_row(
        f"{BColors.OKCYAN}🔄 Updated:       {BColors.BOLD}{stats.updated:>5}{BColors.ENDC}"
    )
    print_row(
        f"{BColors.OKBLUE}💤 Up to date:    {BColors.BOLD}{stats.skipped_up_to_date:>5}{BColors.ENDC}"
    )
    print_row(
        f"{BColors.WARNING}⚠️  Skipped:       {BColors.BOLD}{stats.skipped_incompatible:>5}{BColors.ENDC}"
    )

    # Show errors if any
    if stats.not_found or stats.failed:
        print(f"{BColors.OKBLUE}╠{'═' * inner_width}╣{BColors.ENDC}")

        # Not found
        if stats.not_found:
            print_row(
                f"{BColors.FAIL}❌ Not Found:    {BColors.BOLD}{len(stats.not_found):>5}{BColors.ENDC}"
            )
            for name in stats.not_found:
                safe_name = name[:40] + "..." if len(name) > 40 else name
                print_row(
                    f"{BColors.DIM}   • {safe_name}{BColors.ENDC}",
                    indent=indent_val + 2,
                )

        # Failed
        if stats.failed:
            print_row(
                f"{BColors.FAIL}❌ Failed:        {BColors.BOLD}{len(stats.failed):>5}{BColors.ENDC}"
            )
            for name, reason in stats.failed:
                safe_name = (
                    f"{name[:30]} ({reason[:20]})"
                    if len(name) > 30
                    else f"{name} ({reason})"
                )
                print_row(
                    f"{BColors.DIM}   • {safe_name}{BColors.ENDC}",
                    indent=indent_val + 2,
                )

    print(f"{BColors.OKBLUE}╚{'═' * inner_width}╝{BColors.ENDC}\n")


from . import translations as _translations  # noqa: E402, F811


def __getattr__(name: str):  # noqa: E402
    """Delegate selected_lang access to translations module for backward compat."""
    if name == "selected_lang":
        return _translations.selected_lang
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
