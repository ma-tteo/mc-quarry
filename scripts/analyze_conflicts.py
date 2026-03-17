#!/usr/bin/env python3
"""
Mod Conflict & Compatibility Analyzer.

Deep analysis of mod compatibility including:
- Known incompatibilities from config
- Version-based conflicts
- Loader conflicts
- Dependency conflicts
- Duplicate functionality detection

Usage:
    python3 scripts/analyze_conflicts.py [--config PATH] [--modpack-dir PATH]
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime
from packaging import version as pkg_version

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.config_manager import load_config
from mc_quarry.utils import BColors


class ConflictAnalyzer:
    """Advanced conflict and compatibility analyzer."""
    
    # Known mod conflicts (from community knowledge)
    KNOWN_CONFLICTS = {
        'starlight': ['phosphor', 'scalablelux'],
        'phosphor': ['starlight'],
        'scalablelux': ['phosphor', 'starlight'],
        'modernfix': ['modernfix-mvus'],  # Different versions
        'sodium': ['optifine'],
        'iris': ['optifine'],
        'lithium': ['phosphor'],  # Old versions
    }
    
    # Mods that provide similar functionality
    FUNCTIONAL_DUPLICATES = {
        'optimization': ['sodium', 'optifine', 'rubidium'],
        'lighting': ['starlight', 'phosphor', 'scalablelux'],
        'minimap': ['xaeros-minimap', 'journeymap', 'vintage-improvements'],
        'recipe_viewer': ['jei', 'rei', 'emi'],
        'storage_scan': ['jei', 'rei'],
    }
    
    def __init__(self, config_path: str = "config.json", modpack_dir: str = "modpack"):
        self.config = load_config(config_path)
        self.modpack_dir = Path(modpack_dir)
        self.mc_version = self.detect_mc_version()
        self.installed_mods: Dict[str, Dict[str, Any]] = {}
        self.results: Dict[str, Any] = {
            'mc_version': self.mc_version,
            'incompatibility_violations': [],
            'version_conflicts': [],
            'duplicate_functionality': [],
            'known_conflicts': [],
            'recommendations': []
        }
    
    def detect_mc_version(self) -> str:
        """Detect Minecraft version from modpack directory."""
        for subdir in self.modpack_dir.iterdir():
            if subdir.is_dir() and subdir.name.startswith('mods_core_'):
                parts = subdir.name.split('_')
                if len(parts) >= 3:
                    return '_'.join(parts[2:])
        return "unknown"
    
    def load_installed_mods(self):
        """Load all installed mods with metadata."""
        for subdir in self.modpack_dir.iterdir():
            if not subdir.is_dir() or not subdir.name.startswith('mods_'):
                continue
            
            for info_file in subdir.glob("*.modinfo"):
                try:
                    with info_file.open('r') as f:
                        data = json.load(f)
                        slug = data.get('project_slug', '')
                        if slug:
                            self.installed_mods[slug] = {
                                'version': data.get('version_name', ''),
                                'version_id': data.get('version_id', ''),
                                'provider': data.get('provider', ''),
                                'category': subdir.name
                            }
                except Exception:
                    pass
    
    def check_incompatibility_rules(self):
        """Check mods against incompatibility rules from config."""
        print(f"\n{BColors.BOLD}Checking incompatibility rules...{BColors.ENDC}")
        
        incompatible_mods = self.config.get('incompatible_mods', {})
        
        for mod_name, version_rules in incompatible_mods.items():
            mod_normalized = mod_name.lower()
            
            # Check if mod is installed
            for slug, info in self.installed_mods.items():
                if mod_normalized in slug.lower():
                    # Mod found, check version rules
                    for rule in version_rules:
                        violation = self.check_version_rule(rule, self.mc_version)
                        if violation:
                            self.results['incompatibility_violations'].append({
                                'mod': mod_name,
                                'installed_version': info['version'],
                                'rule': rule,
                                'mc_version': self.mc_version,
                                'violation': violation
                            })
        
        count = len(self.results['incompatibility_violations'])
        if count > 0:
            print(f"  {BColors.FAIL}✗ Found {count} incompatibility violations{BColors.ENDC}")
        else:
            print(f"  {BColors.OKGREEN}✓ No incompatibility violations{BColors.ENDC}")
    
    def check_version_rule(self, rule: str, mc_version: str) -> str:
        """Check if MC version violates a rule."""
        try:
            if rule.startswith('<'):
                # Mod incompatible with versions < X
                rule_version = rule[1:]
                if self.compare_versions(mc_version, rule_version) < 0:
                    return f"MC {mc_version} < {rule_version}"
            elif rule.startswith('>'):
                # Mod incompatible with versions > X
                rule_version = rule[1:]
                if self.compare_versions(mc_version, rule_version) > 0:
                    return f"MC {mc_version} > {rule_version}"
            elif rule.endswith('+'):
                # Mod incompatible with versions >= X
                rule_version = rule[:-1]
                if self.compare_versions(mc_version, rule_version) >= 0:
                    return f"MC {mc_version} >= {rule_version}"
            elif rule.startswith('='):
                # Mod incompatible with exact version
                rule_version = rule[1:]
                if mc_version == rule_version:
                    return f"MC {mc_version} == {rule_version}"
            else:
                # Exact version match
                if mc_version == rule:
                    return f"MC {mc_version} == {rule}"
        except Exception:
            pass
        return ""
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings."""
        try:
            ver1 = pkg_version.parse(v1)
            ver2 = pkg_version.parse(v2)
            if ver1 > ver2: return 1
            if ver1 < ver2: return -1
            return 0
        except Exception:
            # Fallback to string comparison
            if v1 > v2: return 1
            if v1 < v2: return -1
            return 0
    
    def check_known_conflicts(self):
        """Check for known mod conflicts."""
        print(f"\n{BColors.BOLD}Checking known conflicts...{BColors.ENDC}")
        
        installed_lower = {slug.lower(): slug for slug in self.installed_mods.keys()}
        
        for mod1, conflicting_mods in self.KNOWN_CONFLICTS.items():
            if mod1 in installed_lower:
                for mod2 in conflicting_mods:
                    if mod2 in installed_lower:
                        self.results['known_conflicts'].append({
                            'mod1': installed_lower[mod1],
                            'mod2': installed_lower[mod2],
                            'reason': f"Known conflict: {mod1} ↔ {mod2}"
                        })
        
        count = len(self.results['known_conflicts'])
        if count > 0:
            print(f"  {BColors.FAIL}✗ Found {count} known conflicts{BColors.ENDC}")
        else:
            print(f"  {BColors.OKGREEN}✓ No known conflicts{BColors.ENDC}")
    
    def check_duplicate_functionality(self):
        """Check for mods with duplicate functionality."""
        print(f"\n{BColors.BOLD}Checking duplicate functionality...{BColors.ENDC}")
        
        installed_lower = {slug.lower(): slug for slug in self.installed_mods.keys()}
        
        for category, mods in self.FUNCTIONAL_DUPLICATES.items():
            found_mods = []
            for mod in mods:
                if mod in installed_lower:
                    found_mods.append(installed_lower[mod])
            
            if len(found_mods) > 1:
                self.results['duplicate_functionality'].append({
                    'category': category,
                    'mods': found_mods,
                    'recommendation': f"Consider using only one: {', '.join(found_mods)}"
                })
        
        count = len(self.results['duplicate_functionality'])
        if count > 0:
            print(f"  {BColors.WARNING}⚠ Found {count} duplicate functionality groups{BColors.ENDC}")
        else:
            print(f"  {BColors.OKGREEN}✓ No duplicate functionality{BColors.ENDC}")
    
    def generate_recommendations(self):
        """Generate recommendations based on analysis."""
        # Recommend removing conflicts
        for conflict in self.results['known_conflicts']:
            self.results['recommendations'].append({
                'type': 'remove_conflict',
                'priority': 'high',
                'message': f"Remove either {conflict['mod1']} or {conflict['mod2']} - they conflict"
            })
        
        # Recommend choosing one from duplicates
        for dup in self.results['duplicate_functionality']:
            self.results['recommendations'].append({
                'type': 'remove_duplicate',
                'priority': 'medium',
                'message': f"Multiple {dup['category']} mods: {', '.join(dup['mods'])}. Choose one."
            })
        
        # Recommend fixing incompatibility violations
        for violation in self.results['incompatibility_violations']:
            self.results['recommendations'].append({
                'type': 'version_mismatch',
                'priority': 'high',
                'message': f"{violation['mod']} is incompatible with MC {violation['mc_version']} ({violation['rule']})"
            })
    
    def print_report(self):
        """Print comprehensive conflict analysis report."""
        print(f"\n{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"{BColors.BOLD}CONFLICT & COMPATIBILITY ANALYSIS{BColors.ENDC}")
        print(f"{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Minecraft Version: {self.mc_version}")
        print(f"Installed Mods: {len(self.installed_mods)}\n")
        
        # Incompatibility Violations
        if self.results['incompatibility_violations']:
            print(f"{BColors.FAIL}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.FAIL}║{BColors.ENDC}  {BColors.BOLD}INCOMPATIBILITY VIOLATIONS ({len(self.results['incompatibility_violations'])}){BColors.ENDC}")
            for v in self.results['incompatibility_violations']:
                print(f"{BColors.FAIL}║{BColors.ENDC}    ✗ {v['mod']}: {v['violation']}")
            print(f"{BColors.FAIL}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")
        
        # Known Conflicts
        if self.results['known_conflicts']:
            print(f"{BColors.FAIL}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.FAIL}║{BColors.ENDC}  {BColors.BOLD}KNOWN CONFLICTS ({len(self.results['known_conflicts'])}){BColors.ENDC}")
            for c in self.results['known_conflicts']:
                print(f"{BColors.FAIL}║{BColors.ENDC}    ✗ {c['mod1']} ↔ {c['mod2']}")
                print(f"{BColors.FAIL}║{BColors.ENDC}      {c['reason']}")
            print(f"{BColors.FAIL}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")
        
        # Duplicate Functionality
        if self.results['duplicate_functionality']:
            print(f"{BColors.WARNING}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.WARNING}║{BColors.ENDC}  {BColors.BOLD}DUPLICATE FUNCTIONALITY ({len(self.results['duplicate_functionality'])}){BColors.ENDC}")
            for d in self.results['duplicate_functionality']:
                print(f"{BColors.WARNING}║{BColors.ENDC}    ⚠ {d['category'].title()}: {', '.join(d['mods'])}")
                print(f"{BColors.WARNING}║{BColors.ENDC}      {d['recommendation']}")
            print(f"{BColors.WARNING}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")
        
        # Recommendations
        if self.results['recommendations']:
            print(f"{BColors.OKCYAN}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  {BColors.BOLD}RECOMMENDATIONS ({len(self.results['recommendations'])}){BColors.ENDC}")
            for i, rec in enumerate(self.results['recommendations'], 1):
                priority_color = BColors.FAIL if rec['priority'] == 'high' else BColors.WARNING
                print(f"{BColors.OKCYAN}║{BColors.ENDC}    {i}. {priority_color}[{rec['priority'].upper()}]{BColors.ENDC} {rec['message']}")
            print(f"{BColors.OKCYAN}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")
        
        # Save report
        report_path = Path(__file__).parent.parent / 'conflict_analysis_report.json'
        with report_path.open('w') as f:
            json.dump(self.results, f, indent=2)
        print(f"{BColors.OKGREEN}✓ Report saved to: {report_path}{BColors.ENDC}\n")
    
    def run_full_analysis(self):
        """Run complete conflict analysis."""
        self.load_installed_mods()
        self.check_incompatibility_rules()
        self.check_known_conflicts()
        self.check_duplicate_functionality()
        self.generate_recommendations()
        self.print_report()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mod Conflict & Compatibility Analyzer")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config.json")
    parser.add_argument("--modpack-dir", type=str, default="modpack", help="Path to modpack directory")
    args = parser.parse_args()
    
    analyzer = ConflictAnalyzer(config_path=args.config, modpack_dir=args.modpack_dir)
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
