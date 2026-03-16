import re
import unicodedata
import threading
from typing import List, Tuple, Optional

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
    """Formatta i secondi in un formato leggibile."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"

def sanitize_filename(name: str) -> str:
    """Rimuove caratteri invalidi per i nomi dei file."""
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

    def print_summary(self):
        from .ui_manager import print_section_header # Local import to avoid circular dependency
        inner_width = BOX_WIDTH - 2
        indent_val = 2
        
        def print_row(content, row_color=BColors.OKBLUE, indent=indent_val):
            v_len = get_visual_length(content)
            padding = inner_width - v_len - indent 
            print(f"{row_color}║{BColors.ENDC}{' ' * indent}{content}{' ' * max(0, padding)}{row_color}║{BColors.ENDC}")

        print(f"\n{BColors.OKBLUE}╔{'═' * inner_width}╗{BColors.ENDC}")
        # ASCII ART Header
        content_header = [
            fr"{BColors.HEADER}{BColors.BOLD} ___ ___ ___ ___ ___ ___  _  _   ___ _   _ __  __ __  __   _   _____   __ {BColors.ENDC}",
            fr"{BColors.HEADER}{BColors.BOLD}/ __| __/ __/ __|_ _/ _ \| \| | / __| | | |  \/  |  \/  | /_\ | _ \ \ / / {BColors.ENDC}",
            fr"{BColors.HEADER}{BColors.BOLD}\__ \ _|\__ \__ \| | (_) | .` | \__ \ |_| | |\/| | |\/| |/ _ \|   /\ V /  {BColors.ENDC}",
            fr"{BColors.HEADER}{BColors.BOLD}|___/___|___/___/___\___/|_|\_| |___/\___/|_|  |_|_|  |_/_/ \_\_|_ \ |_|   {BColors.ENDC}"
        ]
        for line in content_header:
            print_row(line, indent=indent_val)
            
        print(f"{BColors.OKBLUE}╠{'═' * inner_width}╣{BColors.ENDC}")
        
        print_row(f"{BColors.OKGREEN}✅ Installed: {BColors.BOLD}{self.installed}{BColors.ENDC}")
        print_row(f"{BColors.OKCYAN}🔄 Updated:   {BColors.BOLD}{self.updated}{BColors.ENDC}")
        print_row(f"{BColors.OKBLUE}💤 Up to date:{BColors.BOLD}{self.skipped_up_to_date}{BColors.ENDC}")
        print_row(f"{BColors.WARNING}⚠️ Incompat.: {BColors.BOLD}{self.skipped_incompatible}{BColors.ENDC}")
        
        if self.not_found or self.failed:
            print(f"{BColors.OKBLUE}╠{'═' * inner_width}╣{BColors.ENDC}")
            max_label_len = inner_width - indent_val - 4
            for name in self.not_found:
                safe_name = name[:max_label_len-12] + "..." if len(name) > max_label_len-12 else name
                print_row(f"{BColors.FAIL}❌ NOT FOUND: {BColors.ENDC}{BColors.BOLD}{safe_name}{BColors.ENDC}")
            for name, reason in self.failed:
                detail = f" ({reason})" if reason else ""
                available = inner_width - indent_val - 15
                full_text = f"{name}{detail}"
                if len(full_text) > available:
                    safe_text = full_text[:available-3] + "..."
                else:
                    safe_text = full_text
                print_row(f"{BColors.FAIL}❌ FAILED:    {BColors.ENDC}{BColors.BOLD}{safe_text}{BColors.ENDC}")
        
        print(f"{BColors.OKBLUE}╚{'═' * inner_width}╝{BColors.ENDC}\n")
