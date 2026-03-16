import re
import unicodedata
import threading
from typing import List, Tuple, Optional, Any

class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    MAGENTA = '\033[35m'
    BRIGHT_WHITE = '\033[97m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BG_GREEN = '\033[42m'
    BG_RED = '\033[41m'
    BG_BLUE = '\033[44m'
    BG_CYAN = '\033[46m'
    BG_YELLOW = '\033[43m'

BOX_WIDTH = 82

def get_visual_length(text: str) -> int:
    """Calculates visual length of a string, accounting for wide characters and ANSI codes."""
    ansi_escape = re.compile(r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe target
            [@-Z\\-_]
        |     # or [ [target parameter]... [intermediate character]... target
            \[
            [0-?]*  # parameter
            [ -/]*  # intermediate
            [@-~]   # final
        )
    ''', re.VERBOSE)
    clean_text = ansi_escape.sub('', text)
    
    length = 0
    i = 0
    while i < len(clean_text):
        char = clean_text[i]
        cp = ord(char)
        
        # Skip Variation Selectors and Zero Width Joiners
        if 0xFE00 <= cp <= 0xFE0F or cp == 0x200D:
            i += 1
            continue
            
        # East Asian Width lookup
        width = unicodedata.east_asian_width(char)
        
        # 'W' (Wide), 'F' (Fullwidth) are definitely 2
        # 'A' (Ambiguous) is usually 2 in modern terminals for emojis
        if width in ('W', 'F', 'A') or (0x2600 <= cp <= 0x27BF) or (0x1F300 <= cp <= 0x1F9FF):
            length += 2
        else:
            length += 1
        i += 1
    return length

def format_time(seconds: float) -> str:
    """Format seconds into human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"

def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    return "".join(c for c in name if c.isalnum() or c in " .-_()[]'").strip()

class DownloadStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.installed = 0
        self.updated = 0
        self.skipped_up_to_date = 0
        self.skipped_incompatible = 0
        self.failed: List[Tuple[str, str]] = []
        self.not_found: List[str] = []

    def add_installed(self):
        with self.lock: self.installed += 1
    def add_updated(self):
        with self.lock: self.updated += 1
    def add_skipped_up_to_date(self):
        with self.lock: self.skipped_up_to_date += 1
    def add_skipped_incompatible(self):
        with self.lock: self.skipped_incompatible += 1
    def add_failed(self, name: str, reason: str):
        with self.lock: self.failed.append((name, reason))
    def add_not_found(self, name: str):
        with self.lock: self.not_found.append(name)
