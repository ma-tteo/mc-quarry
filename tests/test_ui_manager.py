"""Tests for mc_quarry.ui_manager."""

import subprocess
from unittest import mock

from mc_quarry.ui_manager import (
    TerminalUI,
    detect_hardware,
    detect_language,
    get_string,
    get_string_no_ansi,
    print_banner,
    print_download_summary,
    print_progress_bar,
    print_section_header,
    set_selected_language,
)
from mc_quarry.utils import BColors


class TestTerminalUI:
    """Tests for TerminalUI class."""

    def test_initial_state(self):
        ui = TerminalUI()
        assert ui.total_tasks == 0
        assert ui.completed_tasks == 0
        assert ui.current_status == "Initializing..."
        assert ui._bar_length == 40

    def test_set_total(self):
        ui = TerminalUI()
        ui.set_total(10)
        assert ui.total_tasks == 10
        assert ui.completed_tasks == 0

    def test_update_progress_increments(self):
        ui = TerminalUI()
        ui.set_total(5)
        ui.update_progress()
        assert ui.completed_tasks == 1
        ui.update_progress(2)
        assert ui.completed_tasks == 3

    def test_set_status(self):
        ui = TerminalUI()
        ui.set_status("Working...")
        assert ui.current_status == "Working..."

    def test_log_writes_to_stdout(self, capsys):
        ui = TerminalUI()
        ui.log("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out

    def test_finish_clears_line(self, capsys):
        ui = TerminalUI()
        ui.finish()
        captured = capsys.readouterr()
        assert "\033[K" in captured.out

    def test_redraw_progress_bar_early_return(self, capsys):
        """No output when total_tasks is 0."""
        ui = TerminalUI()
        ui._redraw_progress_bar()
        captured = capsys.readouterr()
        assert captured.out == ""


class TestGetString:
    """Tests for get_string translation lookup."""

    def test_basic_english(self):
        result = get_string("script_title", "en")
        assert "Modrinth" in result

    def test_italian_translation(self):
        result = get_string("script_title", "it")
        assert "Downloader Modpack" in result

    def test_language_fallback_to_english(self):
        """When translation missing for requested lang, falls back to en."""
        result = get_string("enter_mc_version", "de")
        assert "Please enter the Minecraft version" in result

    def test_missing_key_returns_key(self):
        result = get_string("nonexistent_key", "en")
        assert result == "nonexistent_key"

    def test_args_formatting(self):
        result = get_string("target_mc_version", "en", "1.21.1")
        assert "1.21.1" in result


class TestGetStringNoAnsi:
    """Tests for get_string_no_ansi ANSI stripping."""

    def test_strips_ansi_codes(self):
        result = get_string_no_ansi(f"{BColors.BOLD}hello{BColors.ENDC}")
        assert result == "hello"

    def test_plain_string_unchanged(self):
        result = get_string_no_ansi("hello world")
        assert result == "hello world"


class TestDetectLanguage:
    """Tests for detect_language."""

    @mock.patch("locale.getlocale")
    def test_italian_locale(self, mock_getlocale):
        mock_getlocale.return_value = ("it_IT", "UTF-8")
        assert detect_language() == "it"

    @mock.patch("locale.getlocale")
    def test_english_locale(self, mock_getlocale):
        mock_getlocale.return_value = ("en_US", "UTF-8")
        assert detect_language() == "en"

    @mock.patch("locale.getlocale")
    def test_exception_fallback(self, mock_getlocale):
        mock_getlocale.side_effect = Exception("test error")
        assert detect_language() == "en"


class TestSetSelectedLanguage:
    """Tests for set_selected_language."""

    def test_changes_global(self):
        import mc_quarry.ui_manager as uim

        original = uim.selected_lang
        set_selected_language("it")
        assert uim.selected_lang == "it"
        uim.selected_lang = original


class TestPrintBanner:
    """Tests for print_banner."""

    def test_prints_banner(self, capsys):
        print_banner()
        captured = capsys.readouterr()
        assert "____" in captured.out


class TestPrintSectionHeader:
    """Tests for print_section_header."""

    def test_without_icon(self, capsys):
        print_section_header("Test Section")
        captured = capsys.readouterr()
        assert "Test Section" in captured.out
        assert "╔" in captured.out

    def test_with_icon(self, capsys):
        print_section_header("Downloading", icon="📥")
        captured = capsys.readouterr()
        assert "Downloading" in captured.out
        assert "📥" in captured.out


class TestPrintProgressBar:
    """Tests for print_progress_bar."""

    def test_partial_progress(self, capsys):
        print_progress_bar(5, 10)
        captured = capsys.readouterr()
        assert "5" in captured.out
        assert "10" in captured.out

    def test_complete_adds_newline(self, capsys):
        print_progress_bar(10, 10)
        captured = capsys.readouterr()
        assert captured.out.endswith("\n")

    def test_zero_total_guard(self, capsys):
        """Returns early without output when total is 0."""
        print_progress_bar(0, 0)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestDetectHardware:
    """Tests for detect_hardware."""

    @mock.patch("sys.platform", "linux")
    @mock.patch("subprocess.check_output")
    def test_linux_nvidia(self, mock_check_output):
        mock_check_output.return_value = (
            b"VGA compatible controller: NVIDIA Corporation"
        )
        hw = detect_hardware()
        assert hw["gpu"] == "nvidia"

    @mock.patch("sys.platform", "linux")
    @mock.patch("subprocess.check_output")
    def test_linux_amd(self, mock_check_output):
        mock_check_output.return_value = (
            b"VGA compatible controller: Advanced Micro Devices"
        )
        hw = detect_hardware()
        assert hw["gpu"] == "amd"

    @mock.patch("sys.platform", "linux")
    @mock.patch("subprocess.check_output")
    def test_linux_intel(self, mock_check_output):
        # NOTE: avoid "ati" in mock value — it's a substring of
        # "Corporation" and would falsely match the AMD branch
        mock_check_output.return_value = (
            b"Intel integrated graphics controller"
        )
        hw = detect_hardware()
        assert hw["gpu"] == "intel"

    @mock.patch("sys.platform", "linux")
    @mock.patch("subprocess.check_output")
    @mock.patch("mc_quarry.ui_manager.Path.exists")
    def test_linux_fallback_sys_module_nvidia(
        self, mock_exists, mock_check_output
    ):
        mock_check_output.side_effect = FileNotFoundError("no lspci")
        # Path.exists mock receives no args through instance lookup;
        # iterable side_effect maps to driver order: nvidia, radeon, amdgpu, i915
        mock_exists.side_effect = [True, False, False, False]
        hw = detect_hardware()
        assert hw["gpu"] == "nvidia"

    @mock.patch("sys.platform", "win32")
    @mock.patch("subprocess.check_output")
    def test_windows_nvidia(self, mock_check_output):
        mock_check_output.return_value = b"NVIDIA GeForce RTX 3080"
        hw = detect_hardware()
        assert hw["gpu"] == "nvidia"

    @mock.patch("sys.platform", "darwin")
    @mock.patch("subprocess.check_output")
    def test_macos_apple_silicon(self, mock_check_output):
        mock_check_output.return_value = b"Chipset Model: Apple M2"
        hw = detect_hardware()
        assert hw["gpu"] == "apple"

    @mock.patch("sys.platform", "darwin")
    @mock.patch("subprocess.check_output")
    def test_macos_amd(self, mock_check_output):
        mock_check_output.return_value = b"AMD Radeon Pro 5500M"
        hw = detect_hardware()
        assert hw["gpu"] == "amd"

    @mock.patch("sys.platform", "linux")
    @mock.patch("subprocess.check_output")
    @mock.patch("mc_quarry.ui_manager.Path.exists")
    def test_linux_error_fallback_generic(
        self, mock_exists, mock_check_output
    ):
        """All detection paths fail, returns generic."""
        mock_check_output.side_effect = subprocess.CalledProcessError(
            1, "lspci"
        )
        mock_exists.return_value = False
        hw = detect_hardware()
        assert hw["gpu"] == "generic"

    @mock.patch("sys.platform", "linux")
    @mock.patch("subprocess.check_output")
    @mock.patch("mc_quarry.ui_manager.Path.exists")
    def test_linux_fallback_amd_radeon(
        self, mock_exists, mock_check_output
    ):
        """Fallback matches radeon driver to amd."""
        mock_check_output.side_effect = FileNotFoundError("no lspci")
        mock_exists.side_effect = [False, True, False, False]
        hw = detect_hardware()
        assert hw["gpu"] == "amd"

    @mock.patch("sys.platform", "linux")
    @mock.patch("subprocess.check_output")
    @mock.patch("mc_quarry.ui_manager.Path.exists")
    def test_linux_fallback_intel_i915(
        self, mock_exists, mock_check_output
    ):
        """Fallback matches i915 driver to intel."""
        mock_check_output.side_effect = FileNotFoundError("no lspci")
        mock_exists.side_effect = [False, False, False, True]
        hw = detect_hardware()
        assert hw["gpu"] == "intel"

    @mock.patch("sys.platform", "linux")
    @mock.patch("subprocess.check_output")
    @mock.patch("mc_quarry.ui_manager.Path.exists")
    def test_linux_fallback_amdgpu(
        self, mock_exists, mock_check_output
    ):
        """Fallback matches amdgpu driver to amd."""
        mock_check_output.side_effect = FileNotFoundError("no lspci")
        mock_exists.side_effect = [False, False, True, False]
        hw = detect_hardware()
        assert hw["gpu"] == "amd"


class TestPrintDownloadSummary:
    """Tests for print_download_summary."""

    def test_with_stats(self, capsys, stats):
        stats.installed = 5
        stats.updated = 3
        stats.skipped_up_to_date = 10
        stats.skipped_incompatible = 2
        print_download_summary(stats)
        captured = capsys.readouterr()
        assert "DOWNLOAD COMPLETE" in captured.out
        assert "Installed" in captured.out
        assert "Updated" in captured.out

    def test_empty_stats(self, capsys, stats):
        print_download_summary(stats)
        captured = capsys.readouterr()
        assert "DOWNLOAD COMPLETE" in captured.out

    def test_with_not_found_and_failed(self, capsys, stats):
        stats.not_found = ["missing_mod_1"]
        stats.failed = [("broken_mod", "timeout")]
        print_download_summary(stats)
        captured = capsys.readouterr()
        assert "Not Found" in captured.out
        assert "Failed" in captured.out
