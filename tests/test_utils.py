"""Tests for mc_quarry.utils."""

from mc_quarry.utils import BOX_WIDTH, BColors, get_visual_length, sanitize_filename


class TestBColors:
    def test_basic_colors_defined(self):
        assert BColors.HEADER
        assert BColors.OKBLUE
        assert BColors.OKGREEN
        assert BColors.WARNING
        assert BColors.FAIL
        assert BColors.ENDC

    def test_bold_italic_dim(self):
        assert BColors.BOLD
        assert BColors.ITALIC
        assert BColors.DIM

    def test_bright_colors_defined(self):
        assert BColors.BRIGHT_WHITE
        assert BColors.BRIGHT_GREEN
        assert BColors.BRIGHT_RED
        assert BColors.BRIGHT_YELLOW
        assert BColors.BRIGHT_MAGENTA
        # BRIGHT_CYAN and BRIGHT_BLUE removed as duplicates


class TestDownloadStats:
    def test_initial_state(self, stats):
        assert stats.installed == 0
        assert stats.updated == 0
        assert stats.skipped_up_to_date == 0
        assert stats.skipped_incompatible == 0
        assert stats.failed == []
        assert stats.not_found == []

    def test_add_installed(self, stats):
        stats.add_installed()
        assert stats.installed == 1

    def test_add_updated(self, stats):
        stats.add_updated()
        assert stats.updated == 1

    def test_add_skipped_up_to_date(self, stats):
        stats.add_skipped_up_to_date()
        assert stats.skipped_up_to_date == 1

    def test_add_skipped_incompatible(self, stats):
        stats.add_skipped_incompatible()
        assert stats.skipped_incompatible == 1

    def test_add_failed(self, stats):
        stats.add_failed("test-mod", "connection error")
        assert stats.failed == [("test-mod", "connection error")]

    def test_add_not_found(self, stats):
        stats.add_not_found("missing-mod")
        assert stats.not_found == ["missing-mod"]

    def test_thread_safety(self, stats):
        """Basic smoke test that thread lock doesn't hang."""
        import threading
        threads = [
            threading.Thread(target=stats.add_installed)
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert stats.installed == 10


class TestGetVisualLength:
    def test_plain_ascii(self):
        assert get_visual_length("hello") == 5

    def test_empty_string(self):
        assert get_visual_length("") == 0

    def test_ansi_codes_stripped(self):
        # ANSI codes should not count toward visual length
        assert get_visual_length(f"{BColors.BOLD}hello{BColors.ENDC}") == 5

    def test_wide_characters(self):
        # CJK characters are typically wide (2 cells)
        length = get_visual_length("测试")
        assert length == 4  # 2 Chinese chars × 2

    def test_emoji_double_width(self):
        length = get_visual_length("✅")
        assert length >= 1  # emoji is at least 1, possibly 2


class TestSanitizeFilename:
    def test_basic_filename(self):
        assert sanitize_filename("test_mod.jar") == "test_mod.jar"

    def test_removes_invalid_chars(self):
        assert sanitize_filename("test<>mod|.jar") == "testmod.jar"

    def test_allows_safe_chars(self):
        assert sanitize_filename("test-mod_1.0.jar") == "test-mod_1.0.jar"

    def test_quotes(self):
        assert sanitize_filename("test'mod'.jar") == "test'mod'.jar"


class TestBoxWidth:
    def test_box_width_constant(self):
        assert BOX_WIDTH == 82
