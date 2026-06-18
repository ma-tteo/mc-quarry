#!/usr/bin/env python3
"""
Comprehensive Modrinth & CurseForge API Analysis Tool.

Analyzes all mods in config.json and provides detailed statistics about:
- API response times
- Rate limiting status
- Mod compatibility
- Version availability
- Download sizes

Usage:
    python3 scripts/analyze_apis.py [--modrinth] [--curseforge] [--key API_KEY] [--full]
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.api_client import APIClient
from mc_quarry.config_manager import load_config
from mc_quarry.utils import BColors


class APIAnalyzer:
    """Comprehensive API analysis tool."""

    def __init__(self, cf_api_key: str = ""):
        self.client = APIClient(cf_api_key=cf_api_key)
        self.results: Dict[str, Any] = {
            'modrinth': {'total': 0, 'success': 0, 'failed': 0, 'times': [], 'rate_limited': 0},
            'curseforge': {'total': 0, 'success': 0, 'failed': 0, 'times': [], 'rate_limited': 0},
            'mods': [],
            'errors': []
        }
        self.start_time = time.time()

    def analyze_modrinth_mod(self, mod_name: str, mc_version: str = "1.21.11") -> Dict[str, Any]:
        """Analyze a single mod on Modrinth."""
        result = {
            'name': mod_name,
            'provider': 'modrinth',
            'found': False,
            'has_version': False,
            'response_time': 0,
            'versions_available': 0,
            'latest_version': None,
            'error': None
        }

        start = time.time()
        try:
            # Search
            search_result = self.client.search_modrinth(mod_name, 'mod', limit=1)
            search_time = time.time() - start

            if not search_result or 'hits' not in search_result or not search_result['hits']:
                result['error'] = 'Not found in search'
                self.results['modrinth']['failed'] += 1
                return result

            hit = search_result['hits'][0]
            result['found'] = True
            result['slug'] = hit.get('slug', '')
            result['title'] = hit.get('title', '')
            result['search_time'] = search_time

            # Get project details
            project = self.client.get_modrinth_project(hit['slug'])
            if project:
                result['project_id'] = project.get('id', '')
                result['categories'] = project.get('categories', [])
                result['license'] = project.get('license', 'Unknown')

                # Get versions
                versions = self.client.find_modrinth_version(
                    result['project_id'],
                    mc_version,
                    loader='fabric'
                )
                if versions:
                    result['has_version'] = True
                    result['latest_version'] = versions.get('name', 'Unknown')
                    result['version_id'] = versions.get('id', '')

                    # Count total versions
                    all_versions = self.client.get_json(
                        f"https://api.modrinth.com/v2/project/{result['project_id']}/version"
                    )
                    if isinstance(all_versions, list):
                        result['versions_available'] = len(all_versions)

            result['response_time'] = time.time() - start
            self.results['modrinth']['times'].append(result['response_time'])
            self.results['modrinth']['success'] += 1

        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = time.time() - start
            self.results['modrinth']['failed'] += 1
            self.results['errors'].append(f"Modrinth - {mod_name}: {e}")

        return result

    def analyze_curseforge_mod(self, mod_name: str, mc_version: str = "1.21.11") -> Dict[str, Any]:
        """Analyze a single mod on CurseForge."""
        result = {
            'name': mod_name,
            'provider': 'curseforge',
            'found': False,
            'has_version': False,
            'response_time': 0,
            'download_count': 0,
            'error': None
        }

        if not self.client.cf_api_key:
            result['error'] = 'No API key provided'
            return result

        start = time.time()
        try:
            # Search
            project = self.client.search_curseforge(mod_name, class_id=6)

            if not project:
                result['error'] = 'Not found'
                self.results['curseforge']['failed'] += 1
                return result

            result['found'] = True
            result['project_id'] = project.get('id', '')
            result['slug'] = project.get('slug', '')
            result['title'] = project.get('name', '')
            result['download_count'] = project.get('downloadCount', 0)
            result['game_versions'] = project.get('latestFilesIndexes', [])[:5]  # Last 5 versions

            # Get latest file
            latest_file = self.client.get_latest_file_cf(
                project['id'], mc_version, mod_loader_type=4
            )
            if latest_file:
                result['has_version'] = True
                result['latest_version'] = latest_file.get('displayName', 'Unknown')
                result['file_size'] = latest_file.get('fileLength', 0) / (1024*1024)  # MB

            result['response_time'] = time.time() - start
            self.results['curseforge']['times'].append(result['response_time'])
            self.results['curseforge']['success'] += 1

        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = time.time() - start
            self.results['curseforge']['failed'] += 1
            self.results['errors'].append(f"CurseForge - {mod_name}: {e}")

        return result

    def run_full_analysis(self, config: Dict[str, Any], mc_version: str = "1.21.11"):
        """Run comprehensive analysis on all mods in config."""
        all_mods = []

        # Collect all mods from all categories
        for key in ['core_mods', 'utility_mods', 'light_qol_mods', 'curseforge_mods']:
            if key in config:
                for mod in config[key]:
                    if mod not in all_mods:
                        all_mods.append(mod)

        print(f"\n{BColors.BOLD}Analyzing {len(all_mods)} mods...{BColors.ENDC}\n")

        for i, mod in enumerate(all_mods, 1):
            # Skip URLs
            if mod.startswith('http'):
                continue

            # Determine provider
            is_curseforge = key == 'curseforge_mods' or 'curseforge' in mod.lower()

            if is_curseforge and self.client.cf_api_key:
                result = self.analyze_curseforge_mod(mod, mc_version)
            else:
                result = self.analyze_modrinth_mod(mod, mc_version)

            self.results['mods'].append(result)
            self.results[result['provider']]['total'] += 1

            # Progress indicator
            if result['found']:
                status = f"{BColors.OKGREEN}✓{BColors.ENDC}"
            else:
                status = f"{BColors.FAIL}✗{BColors.ENDC}"
            if result.get('has_version'):
                version_info = f"→ {result.get('latest_version', 'N/A')}"
            else:
                version_info = ""
            print(f"  [{i}/{len(all_mods)}] {status} {mod[:50]:<50} {version_info}")

            # Rate limiting delay
            time.sleep(0.3)

    def print_report(self):
        """Print comprehensive analysis report."""
        total_time = time.time() - self.start_time

        print(f"\n{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"{BColors.BOLD}API ANALYSIS REPORT{BColors.ENDC}")
        print(f"{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total analysis time: {total_time:.2f}s\n")

        # Modrinth Stats
        mr = self.results['modrinth']
        if mr['total'] > 0:
            avg_time = sum(mr['times']) / len(mr['times']) if mr['times'] else 0
            _mr_prefix = f"{BColors.OKCYAN}║{BColors.ENDC}  {BColors.BOLD}"
            print(f"{BColors.OKCYAN}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{_mr_prefix}MODRINTH API STATISTICS{BColors.ENDC}")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Total mods tested:    {mr['total']:<5}")
            mr_pct = mr['success'] / mr['total'] * 100
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Successful:           "
                  f"{mr['success']:<5} ({mr_pct:.1f}%)")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Failed:               {mr['failed']:<5}")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Rate limited:         {mr['rate_limited']:<5}")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Avg response time:    {avg_time*1000:.0f}ms")
            if mr['times']:
                _mr_min = min(mr['times']) * 1000
                _mr_max = max(mr['times']) * 1000
                print(f"{BColors.OKCYAN}║{BColors.ENDC}  Min response time:    {_mr_min:.0f}ms")
                print(f"{BColors.OKCYAN}║{BColors.ENDC}  Max response time:    {_mr_max:.0f}ms")
            else:
                print("")
                print("")
            print(f"{BColors.OKCYAN}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")

        # CurseForge Stats
        cf = self.results['curseforge']
        if cf['total'] > 0 and self.client.cf_api_key:
            avg_time = sum(cf['times']) / len(cf['times']) if cf['times'] else 0
            _cf_prefix = f"{BColors.OKCYAN}║{BColors.ENDC}  {BColors.BOLD}"
            print(f"{BColors.OKCYAN}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{_cf_prefix}CURSEFORGE API STATISTICS{BColors.ENDC}")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Total mods tested:    {cf['total']:<5}")
            cf_pct = cf['success'] / cf['total'] * 100
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Successful:           "
                  f"{cf['success']:<5} ({cf_pct:.1f}%)")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Failed:               {cf['failed']:<5}")
            print(f"{BColors.OKCYAN}║{BColors.ENDC}  Avg response time:    {avg_time*1000:.0f}ms")
            print(f"{BColors.OKCYAN}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")

        # Errors
        if self.results['errors']:
            _err_count = len(self.results['errors'])
            _err_prefix = f"{BColors.WARNING}║{BColors.ENDC}  {BColors.BOLD}"
            print(f"{BColors.WARNING}╔══════════════════════════════════════════════════════════════╗{BColors.ENDC}")
            print(f"{_err_prefix}ERRORS ({_err_count}){BColors.ENDC}")
            for error in self.results['errors'][:10]:  # Show first 10
                print(f"{BColors.WARNING}║{BColors.ENDC}    • {error[:65]}")
            if len(self.results['errors']) > 10:
                _extra = len(self.results['errors']) - 10
                print(f"{BColors.WARNING}║{BColors.ENDC}    ... and {_extra} more")
            print(f"{BColors.WARNING}╚══════════════════════════════════════════════════════════════╝{BColors.ENDC}\n")

        # Save report
        report_path = Path(__file__).parent.parent / 'api_analysis_report.json'
        with report_path.open('w') as f:
            json.dump(self.results, f, indent=2)
        print(f"{BColors.OKGREEN}✓ Report saved to: {report_path}{BColors.ENDC}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Comprehensive API Analysis Tool")
    parser.add_argument("--modrinth", action="store_true", help="Analyze Modrinth only")
    parser.add_argument("--curseforge", action="store_true", help="Analyze CurseForge only")
    parser.add_argument("--key", type=str, help="CurseForge API key")
    parser.add_argument("--version", type=str, default="1.21.11", help="Minecraft version")
    parser.add_argument("--full", action="store_true", help="Full analysis (all mods)")
    args = parser.parse_args()

    config = load_config()
    api_key = args.key or config.get('curseforge_api_key', '')

    analyzer = APIAnalyzer(cf_api_key=api_key)

    if args.full:
        analyzer.run_full_analysis(config, args.version)
    else:
        # Quick test with sample mods
        print(f"{BColors.BOLD}Quick API Test{BColors.ENDC}\n")

        if not args.curseforge:
            print(f"{BColors.OKCYAN}Testing Modrinth...{BColors.ENDC}")
            result = analyzer.analyze_modrinth_mod("sodium", args.version)
            if result['found']:
                status = f"{BColors.OKGREEN}✓{BColors.ENDC}"
            else:
                status = f"{BColors.FAIL}✗{BColors.ENDC}"
            mr_response_ms = result['response_time'] * 1000
            print(f"  {status} Sodium: {result.get('latest_version', 'N/A')}"
                  f" ({mr_response_ms:.0f}ms)\n")

        if args.curseforge and api_key:
            print(f"{BColors.OKCYAN}Testing CurseForge...{BColors.ENDC}")
            result = analyzer.analyze_curseforge_mod("jei", args.version)
            if result['found']:
                status = f"{BColors.OKGREEN}✓{BColors.ENDC}"
            else:
                status = f"{BColors.FAIL}✗{BColors.ENDC}"
            cf_response_ms = result['response_time'] * 1000
            print(f"  {status} JEI: {result.get('latest_version', 'N/A')}"
                  f" ({cf_response_ms:.0f}ms)\n")

    analyzer.print_report()


if __name__ == "__main__":
    main()
