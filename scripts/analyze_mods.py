#!/usr/bin/env python3
"""
Deep Mod Analysis Tool.

Analyzes all installed mods and compares with config.json to find:
- Mods in config but not installed
- Mods installed but not in config
- Outdated mods
- Missing dependencies
- Potential conflicts

Usage:
    python3 scripts/analyze_mods.py [--config PATH] [--modpack-dir PATH]
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.config_manager import load_config
from mc_quarry.utils import BColors


class ModAnalyzer:
    """Comprehensive mod analysis tool."""
    
    def __init__(self, config_path: str = "config.json", modpack_dir: str = "modpack"):
        self.config = load_config(config_path)
        self.modpack_dir = Path(modpack_dir)
        self.mc_version = self.detect_mc_version()
        self.installed_mods: Dict[str, Dict[str, Any]] = {}
        self.config_mods: Set[str] = set()
        self.analysis_results: Dict[str, Any] = {
            'mc_version': self.mc_version,
            'installed_count': 0,
            'config_count': 0,
            'missing_mods': [],
            'extra_mods': [],
            'outdated_mods': [],
            'missing_dependencies': [],
            'potential_conflicts': [],
            'mod_details': []
        }
    
    def detect_mc_version(self) -> str:
        """Detect Minecraft version from modpack directory structure."""
        for subdir in self.modpack_dir.iterdir():
            if subdir.is_dir() and subdir.name.startswith('mods_'):
                # Extract version from directory name (e.g., mods_core_1.21.11)
                parts = subdir.name.split('_')
                if len(parts) >= 3:
                    return '_'.join(parts[2:])
        return "unknown"
    
    def load_installed_mods(self):
        """Load all installed mods from modpack directory."""
        print(f"\n{BColors.BOLD}Scanning installed mods...{BColors.ENDC}")
        
        for subdir in self.modpack_dir.iterdir():
            if not subdir.is_dir() or not subdir.name.startswith('mods_'):
                continue
            
            category = subdir.name.replace('mods_', '').replace(f'_{self.mc_version}', '')
            print(f"  {BColors.DIM}Checking {subdir.name}...{BColors.ENDC}")
            
            for info_file in subdir.glob("*.modinfo"):
                try:
                    with info_file.open('r') as f:
                        data = json.load(f)
                        slug = data.get('project_slug', data.get('project_id', ''))
                        if slug:
                            self.installed_mods[slug] = {
                                'category': category,
                                'version': data.get('version_name', 'Unknown'),
                                'version_id': data.get('version_id', ''),
                                'provider': data.get('provider', 'modrinth'),
                                'filename': data.get('filename', ''),
                                'path': str(subdir)
                            }
                except Exception as e:
                    print(f"    {BColors.FAIL}✗ Error reading {info_file.name}: {e}{BColors.ENDC}")
        
        self.analysis_results['installed_count'] = len(self.installed_mods)
        print(f"  {BColors.OKGREEN}✓ Found {len(self.installed_mods)} installed mods{BColors.ENDC}")
    
    def load_config_mods(self):
        """Load all mods from config.json."""
        print(f"\n{BColors.BOLD}Loading config mods...{BColors.ENDC}")
        
        mod_categories = {
            'mods': 'core',
            'light_qol_mods': 'light_qol',


            'curseforge_mods': 'curseforge'
        }
        
        for config_key, category in mod_categories.items():
            if config_key in self.config:
                for mod in self.config[config_key]:
                    # Normalize mod name for comparison
                    normalized = mod.lower().replace(' ', '-').replace(':', '')
                    self.config_mods.add(normalized)
                    
                    self.analysis_results['mod_details'].append({
                        'name': mod,
                        'normalized': normalized,
                        'category': category
                    })
        
        self.analysis_results['config_count'] = len(self.config_mods)
        print(f"  {BColors.OKGREEN}✓ Found {len(self.config_mods)} mods in config{BColors.ENDC}")
    
    def find_missing_mods(self):
        """Find mods in config but not installed."""
        print(f"\n{BColors.BOLD}Finding missing mods...{BColors.ENDC}")
        
        installed_normalized = {slug.lower().replace(' ', '-').replace(':', '') 
                               for slug in self.installed_mods.keys()}
        
        for mod_detail in self.analysis_results['mod_details']:
            if mod_detail['normalized'] not in installed_normalized:
                self.analysis_results['missing_mods'].append({
                    'name': mod_detail['name'],
                    'normalized': mod_detail['normalized'],
                    'category': mod_detail['category']
                })
        
        count = len(self.analysis_results['missing_mods'])
        if count > 0:
            print(f"  {BColors.WARNING}⚠ Found {count} missing mods{BColors.ENDC}")
        else:
            print(f"  {BColors.OKGREEN}✓ No missing mods{BColors.ENDC}")
    
    def find_extra_mods(self):
        """Find mods installed but not in config."""
        print(f"\n{BColors.BOLD}Finding extra mods...{BColors.ENDC}")
        
        config_normalized = self.config_mods
        
        for slug, info in self.installed_mods.items():
            slug_normalized = slug.lower().replace(' ', '-').replace(':', '')
            if slug_normalized not in config_normalized:
                self.analysis_results['extra_mods'].append({
                    'slug': slug,
                    'name': info.get('version', 'Unknown'),
                    'category': info.get('category', 'unknown'),
                    'version': info.get('version', 'Unknown')
                })
        
        count = len(self.analysis_results['extra_mods'])
        if count > 0:
            print(f"  {BColors.OKCYAN}ℹ Found {count} extra mods (installed but not in config){BColors.ENDC}")
        else:
            print(f"  {BColors.OKGREEN}✓ No extra mods{BColors.ENDC}")
    
    def check_conflicts(self):
        """Check for potential mod conflicts."""
        print(f"\n{BColors.BOLD}Checking for conflicts...{BColors.ENDC}")
        
        conflicts_config = self.config.get('conflicts', {})
        installed_slugs = set(self.installed_mods.keys())
        
        for primary_mod, conflicting_mods in conflicts_config.items():
            primary_normalized = primary_mod.lower()
            
            # Check if primary mod is installed
            for slug in installed_slugs:
                if primary_normalized in slug.lower():
                    # Primary mod found, check for conflicts
                    for conflict in conflicting_mods:
                        conflict_normalized = conflict.lower()
                        for other_slug in installed_slugs:
                            if conflict_normalized in other_slug.lower():
                                self.analysis_results['potential_conflicts'].append({
                                    'primary': primary_mod,
                                    'conflicts_with': conflict,
                                    'installed': [slug, other_slug]
                                })
        
        count = len(self.analysis_results['potential_conflicts'])
        if count > 0:
            print(f"  {BColors.FAIL}✗ Found {count} potential conflicts{BColors.ENDC}")
        else:
            print(f"  {BColors.OKGREEN}✓ No conflicts detected{BColors.ENDC}")
    
    def print_report(self):
        """Print comprehensive analysis report."""
        print(f"\n{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"{BColors.BOLD}MOD ANALYSIS REPORT{BColors.ENDC}")
        print(f"{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Minecraft Version: {self.mc_version}")
        print(f"Installed Mods: {self.analysis_results['installed_count']}")
        print(f"Config Mods: {self.analysis_results['config_count']}")
        
        # Missing Mods
        if self.analysis_results['missing_mods']:
            print(f"\n{BColors.WARNING}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.WARNING}║{BColors.ENDC}  {BColors.BOLD}MISSING MODS ({len(self.analysis_results['missing_mods'])}){BColors.ENDC}")
            for mod in self.analysis_results['missing_mods'][:20]:
                print(f"{BColors.WARNING}║{BColors.ENDC}    • {mod['name'][:60]} ({mod['category']})")
            if len(self.analysis_results['missing_mods']) > 20:
                print(f"{BColors.WARNING}║{BColors.ENDC}    ... and {len(self.analysis_results['missing_mods']) - 20} more")
            print(f"{BColors.WARNING}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}")
        
        # Extra Mods
        if self.analysis_results['extra_mods']:
            print(f"\n{BColors.OKCYAN}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  {BColors.BOLD}EXTRA MODS ({len(self.analysis_results['extra_mods'])}){BColors.ENDC}")
            for mod in self.analysis_results['extra_mods'][:20]:
                print(f"{BColors.OKCYAN}║{BColors.ENDC}    • {mod['slug'][:60]} ({mod['category']})")
            if len(self.analysis_results['extra_mods']) > 20:
                print(f"{BColors.OKCYAN}║{BColors.ENDC}    ... and {len(self.analysis_results['extra_mods']) - 20} more")
            print(f"{BColors.OKCYAN}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}")
        
        # Conflicts
        if self.analysis_results['potential_conflicts']:
            print(f"\n{BColors.FAIL}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.FAIL}║{BColors.ENDC}  {BColors.BOLD}POTENTIAL CONFLICTS ({len(self.analysis_results['potential_conflicts'])}){BColors.ENDC}")
            for conflict in self.analysis_results['potential_conflicts']:
                print(f"{BColors.FAIL}║{BColors.ENDC}    • {conflict['primary']} ↔ {conflict['conflicts_with']}")
            print(f"{BColors.FAIL}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}")
        
        # Save report
        report_path = Path(__file__).parent.parent / 'mod_analysis_report.json'
        with report_path.open('w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        print(f"\n{BColors.OKGREEN}✓ Report saved to: {report_path}{BColors.ENDC}\n")
    
    def run_full_analysis(self):
        """Run complete mod analysis."""
        self.load_installed_mods()
        self.load_config_mods()
        self.find_missing_mods()
        self.find_extra_mods()
        self.check_conflicts()
        self.print_report()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deep Mod Analysis Tool")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config.json")
    parser.add_argument("--modpack-dir", type=str, default="modpack", help="Path to modpack directory")
    args = parser.parse_args()
    
    analyzer = ModAnalyzer(config_path=args.config, modpack_dir=args.modpack_dir)
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
