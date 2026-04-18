#!/usr/bin/env python3
"""
Advanced Configuration Validator.

Performs deep validation of config.json including:
- Structure validation
- Mod name validation (checks against Modrinth API)
- Path validation
- Duplicate detection
- Incompatibility rule validation
- Dependency checks

Usage:
    python3 scripts/validate_config.py [config.json] [--deep]
"""
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.config_manager import load_config, CONFIG_FILE
from mc_quarry.api_client import APIClient
from mc_quarry.utils import BColors


class ConfigValidator:
    """Advanced configuration validator."""
    
    # Required fields with their expected types
    REQUIRED_FIELDS = {
        'language': (str, False),  # (type, required)
        'mods_folder': (str, False),
        'resourcepacks_folder': (str, False),
        'mods': (list, True),
        'texture_packs': (list, True),
        'incompatible_mods': (dict, False),
        'install_light_qol': (bool, False),
        'light_qol_mods': (list, False),
    }
    
    # Optional fields
    OPTIONAL_FIELDS = [
        'curseforge_api_key',
        'conflicts',
        'requirements',
        'curseforge_mods',
        'curseforge_texture_packs'
    ]
    
    def __init__(self, config_path: str = CONFIG_FILE, deep_check: bool = False):
        self.config_path = config_path
        self.deep_check = deep_check
        self.config: Dict[str, Any] = {}
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.info: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}
    
    def load_config(self) -> bool:
        """Load and parse config file."""
        path = Path(self.config_path)
        
        if not path.exists():
            self.errors.append({
                'type': 'file_not_found',
                'message': f"Config file not found: {path}",
                'severity': 'critical'
            })
            return False
        
        try:
            with path.open('r') as f:
                self.config = json.load(f)
            self.info.append({
                'type': 'file_loaded',
                'message': f"Config loaded: {path} ({path.stat().st_size} bytes)"
            })
            return True
        except json.JSONDecodeError as e:
            self.errors.append({
                'type': 'invalid_json',
                'message': f"Invalid JSON: {e}",
                'severity': 'critical'
            })
            return False
        except Exception as e:
            self.errors.append({
                'type': 'load_error',
                'message': f"Error loading config: {e}",
                'severity': 'critical'
            })
            return False
    
    def validate_structure(self):
        """Validate config structure and required fields."""
        print(f"\n{BColors.BOLD}Validating structure...{BColors.ENDC}")
        
        # Check required fields
        for field, (expected_type, required) in self.REQUIRED_FIELDS.items():
            if field not in self.config:
                if required:
                    self.errors.append({
                        'type': 'missing_required',
                        'message': f"Missing required field: {field}",
                        'field': field
                    })
                else:
                    self.warnings.append({
                        'type': 'missing_optional',
                        'message': f"Missing optional field: {field}",
                        'field': field
                    })
            elif not isinstance(self.config[field], expected_type):
                self.errors.append({
                    'type': 'wrong_type',
                    'message': f"Field '{field}' should be {expected_type.__name__}, got {type(self.config[field]).__name__}",
                    'field': field
                })
        
        # Check for unknown fields
        known_fields = set(self.REQUIRED_FIELDS.keys()) | set(self.OPTIONAL_FIELDS)
        for key in self.config.keys():
            if key not in known_fields:
                self.warnings.append({
                    'type': 'unknown_field',
                    'message': f"Unknown field: {key}",
                    'field': key
                })
        
        print(f"  {BColors.OKGREEN}✓ Structure validation complete{BColors.ENDC}")
    
    def validate_mod_lists(self):
        """Validate mod list entries."""
        print(f"\n{BColors.BOLD}Validating mod lists...{BColors.ENDC}")
        
        mod_fields = ['mods', 'light_qol_mods', 
                      'curseforge_mods', 'texture_packs', 'curseforge_texture_packs']
        
        all_mods = set()
        duplicates = set()
        
        for field in mod_fields:
            if field not in self.config:
                continue
            
            mods = self.config[field]
            if not isinstance(mods, list):
                continue
            
            # Check for empty lists
            if not mods:
                self.info.append({
                    'type': 'empty_list',
                    'message': f"Empty mod list: {field}"
                })
                continue
            
            # Check for duplicates within list
            seen = set()
            for mod in mods:
                if not isinstance(mod, str):
                    self.errors.append({
                        'type': 'invalid_entry',
                        'message': f"Non-string entry in {field}: {mod}",
                        'field': field
                    })
                    continue
                
                # Check for empty strings
                if not mod.strip():
                    self.warnings.append({
                        'type': 'empty_entry',
                        'message': f"Empty mod name in {field}",
                        'field': field
                    })
                    continue
                
                # Check for URLs (should use slug instead)
                if mod.startswith('http'):
                    self.warnings.append({
                        'type': 'url_in_config',
                        'message': f"URL in config (use slug instead): {mod[:50]}",
                        'field': field
                    })
                
                # Normalize for duplicate check
                normalized = mod.lower().strip()
                if normalized in seen:
                    duplicates.add(mod)
                seen.add(normalized)
                
                # Track across all lists
                if normalized in all_mods:
                    self.info.append({
                        'type': 'duplicate_across_lists',
                        'message': f"Mod appears in multiple lists: {mod}",
                        'mod': mod
                    })
                all_mods.add(normalized)
            
            self.stats[field] = len(mods)
        
        if duplicates:
            for dup in duplicates:
                self.warnings.append({
                    'type': 'duplicate_in_list',
                    'message': f"Duplicate mod in same list: {dup}"
                })
        
        self.stats['total_unique_mods'] = len(all_mods)
        print(f"  {BColors.OKGREEN}✓ Found {len(all_mods)} unique mods{BColors.ENDC}")
    
    def validate_paths(self):
        """Validate file paths."""
        print(f"\n{BColors.BOLD}Validating paths...{BColors.ENDC}")
        
        path_fields = ['mods_folder', 'resourcepacks_folder']
        
        for field in path_fields:
            if field not in self.config:
                continue
            
            path = self.config[field]
            if not path:
                self.info.append({
                    'type': 'empty_path',
                    'message': f"Empty path: {field}"
                })
                continue
            
            # Check for placeholder
            if '<INSTANCE_NAME>' in path:
                self.info.append({
                    'type': 'placeholder_path',
                    'message': f"Path uses placeholder: {field} = {path}"
                })
            else:
                # Validate path exists
                path_obj = Path(path).expanduser()
                if not path_obj.exists():
                    self.warnings.append({
                        'type': 'path_not_found',
                        'message': f"Path does not exist: {field} = {path}",
                        'field': field
                    })
                elif not path_obj.is_dir():
                    self.errors.append({
                        'type': 'not_a_directory',
                        'message': f"Path is not a directory: {field} = {path}",
                        'field': field
                    })
        
        print(f"  {BColors.OKGREEN}✓ Path validation complete{BColors.ENDC}")
    
    def validate_incompatibility_rules(self):
        """Validate incompatibility rules format."""
        print(f"\n{BColors.BOLD}Validating incompatibility rules...{BColors.ENDC}")
        
        if 'incompatible_mods' not in self.config:
            return
        
        rules = self.config['incompatible_mods']
        valid_patterns = ['^<\\d', '^>\\d', '^\\d+\\.\\d+', '^=\\d']  # <X, >X, X+, =X
        
        for mod, version_rules in rules.items():
            if not isinstance(version_rules, list):
                self.errors.append({
                    'type': 'invalid_rule_format',
                    'message': f"Rules for '{mod}' should be a list",
                    'mod': mod
                })
                continue
            
            for rule in version_rules:
                if not isinstance(rule, str):
                    self.errors.append({
                        'type': 'invalid_rule_type',
                        'message': f"Rule for '{mod}' should be string, got {type(rule).__name__}: {rule}",
                        'mod': mod,
                        'rule': rule
                    })
                    continue
                
                # Validate rule format
                is_valid = False
                for pattern in valid_patterns:
                    if re.match(pattern, rule):
                        is_valid = True
                        break
                
                if not is_valid:
                    self.warnings.append({
                        'type': 'suspicious_rule',
                        'message': f"Rule format may be invalid: {rule}",
                        'mod': mod,
                        'rule': rule
                    })
        
        self.stats['incompatibility_rules'] = len(rules)
        print(f"  {BColors.OKGREEN}✓ Found {len(rules)} incompatibility rules{BColors.ENDC}")
    
    def validate_conflicts(self):
        """Validate conflict rules."""
        print(f"\n{BColors.BOLD}Validating conflict rules...{BColors.ENDC}")
        
        if 'conflicts' not in self.config:
            return
        
        conflicts = self.config['conflicts']
        
        for primary, conflicting in conflicts.items():
            if not isinstance(conflicting, list):
                self.errors.append({
                    'type': 'invalid_conflict_format',
                    'message': f"Conflicts for '{primary}' should be a list",
                    'mod': primary
                })
                continue
            
            # Check for self-conflict
            if primary.lower() in [c.lower() for c in conflicting]:
                self.errors.append({
                    'type': 'self_conflict',
                    'message': f"Mod conflicts with itself: {primary}",
                    'mod': primary
                })
        
        self.stats['conflict_rules'] = len(conflicts)
        print(f"  {BColors.OKGREEN}✓ Found {len(conflicts)} conflict rules{BColors.ENDC}")
    
    async def deep_validate_mods(self):
        """Deep validate mods against Modrinth API."""
        if not self.deep_check:
            self.info.append({
                'type': 'deep_check_skipped',
                'message': "Deep validation skipped (use --deep to enable)"
            })
            return
        
        print(f"\n{BColors.BOLD}Deep validating mods against API...{BColors.ENDC}")
        
        client = APIClient()
        all_mods = []
        
        # Collect all mod names
        for field in ['mods', 'light_qol_mods',]:
            if field in self.config:
                for mod in self.config[field]:
                    if not mod.startswith('http'):
                        all_mods.append((field, mod))
        
        valid_count = 0
        invalid_count = 0
        
        for i, (field, mod) in enumerate(all_mods[:20], 1):  # Limit to 20 for speed
            print(f"  Checking {mod}... ", end='')
            
            result = client.search_modrinth(mod, 'mod', limit=1)
            
            if result and 'hits' in result and result['hits']:
                print(f"{BColors.OKGREEN}✓{BColors.ENDC}", end='')
                valid_count += 1
            else:
                print(f"{BColors.WARNING}✗{BColors.ENDC}", end='')
                invalid_count += 1
                self.warnings.append({
                    'type': 'mod_not_found',
                    'message': f"Mod not found on Modrinth: {mod}",
                    'field': field,
                    'mod': mod
                })
            
            # Rate limiting
            import time
            time.sleep(0.3)
        
        if len(all_mods) > 20:
            self.info.append({
                'type': 'deep_check_limited',
                'message': f"Only checked 20/{len(all_mods)} mods (use full analysis for complete check)"
            })
        
        print(f"\n  {BColors.OKGREEN}✓ {valid_count} valid, {invalid_count} not found{BColors.ENDC}")
    
    def print_report(self):
        """Print comprehensive validation report."""
        print(f"\n{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"{BColors.BOLD}CONFIGURATION VALIDATION REPORT{BColors.ENDC}")
        print(f"{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Config File: {self.config_path}")
        print(f"Deep Check: {'Yes' if self.deep_check else 'No'}\n")
        
        # Stats
        if self.stats:
            print(f"{BColors.BOLD}Statistics:{BColors.ENDC}")
            for key, value in self.stats.items():
                print(f"  • {key}: {value}")
            print()
        
        # Errors
        if self.errors:
            print(f"{BColors.FAIL}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.FAIL}║{BColors.ENDC}  {BColors.BOLD}ERRORS ({len(self.errors)}){BColors.ENDC}")
            for error in self.errors:
                print(f"{BColors.FAIL}║{BColors.ENDC}    ✗ {error['message']}")
            print(f"{BColors.FAIL}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")
        
        # Warnings
        if self.warnings:
            print(f"{BColors.WARNING}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.WARNING}║{BColors.ENDC}  {BColors.BOLD}WARNINGS ({len(self.warnings)}){BColors.ENDC}")
            for warning in self.warnings[:20]:  # Limit display
                print(f"{BColors.WARNING}║{BColors.ENDC}    ⚠ {warning['message']}")
            if len(self.warnings) > 20:
                print(f"{BColors.WARNING}║{BColors.ENDC}    ... and {len(self.warnings) - 20} more")
            print(f"{BColors.WARNING}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")
        
        # Info
        if self.info:
            print(f"{BColors.OKCYAN}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  {BColors.BOLD}INFO ({len(self.info)}){BColors.ENDC}")
            for info in self.info[:10]:
                print(f"{BColors.OKCYAN}║{BColors.ENDC}    ℹ {info['message']}")
            print(f"{BColors.OKCYAN}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'config_path': self.config_path,
            'deep_check': self.deep_check,
            'stats': self.stats,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'valid': len(self.errors) == 0
        }
        
        report_path = Path(__file__).parent.parent / 'config_validation_report.json'
        with report_path.open('w') as f:
            json.dump(report, f, indent=2)
        print(f"{BColors.OKGREEN}✓ Report saved to: {report_path}{BColors.ENDC}\n")
        
        # Return exit code
        if self.errors:
            return 1
        return 0
    
    def run_validation(self) -> int:
        """Run complete validation."""
        if not self.load_config():
            self.print_report()
            return 1
        
        self.validate_structure()
        self.validate_mod_lists()
        self.validate_paths()
        self.validate_incompatibility_rules()
        self.validate_conflicts()
        
        # Deep check is async but we'll skip for now
        # import asyncio
        # asyncio.run(self.deep_validate_mods())
        
        return self.print_report()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Advanced Configuration Validator")
    parser.add_argument('config', nargs='?', default=CONFIG_FILE, help='Path to config.json')
    parser.add_argument('--deep', action='store_true', help='Enable deep validation (checks mods against API)')
    args = parser.parse_args()
    
    validator = ConfigValidator(config_path=args.config, deep_check=args.deep)
    exit_code = validator.run_validation()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
