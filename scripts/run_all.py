#!/usr/bin/env python3
"""
Master Script - Run All Analysis Tools.

Executes all analysis scripts in sequence and generates a comprehensive summary report.

Usage:
    python3 scripts/run_all.py [--config PATH] [--modpack-dir PATH] [--api-key KEY] [--mc-version VERSION]
"""
import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.utils import BColors


class AnalysisRunner:
    """Master analysis runner."""
    
    SCRIPTS = [
        {
            'name': 'Validate Config',
            'file': 'validate_config.py',
            'description': 'Validates config.json structure and content',
            'critical': True
        },
        {
            'name': 'Test Hardware',
            'file': 'test_hardware.py',
            'description': 'Tests hardware detection',
            'critical': False
        },
        {
            'name': 'Test Connection',
            'file': 'test_connection.py',
            'description': 'Tests API connectivity',
            'critical': True
        },
        {
            'name': 'Analyze APIs',
            'file': 'analyze_apis.py',
            'description': 'Deep API analysis with statistics',
            'critical': False
        },
        {
            'name': 'Analyze Mods',
            'file': 'analyze_mods.py',
            'description': 'Compares installed vs configured mods',
            'critical': True
        },
        {
            'name': 'Analyze Conflicts',
            'file': 'analyze_conflicts.py',
            'description': 'Checks for mod conflicts and compatibility',
            'critical': True
        }
    ]
    
    def __init__(self, args: Dict[str, Any]):
        self.args = args
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.scripts_dir = Path(__file__).parent
    
    def run_script(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single analysis script."""
        print(f"\n{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"{BColors.BOLD}Running: {script['name']}{BColors.ENDC}")
        print(f"{BColors.DIM}{script['description']}{BColors.ENDC}")
        print(f"{BColors.HEADER}{'='*70}{BColors.ENDC}\n")
        
        result = {
            'name': script['name'],
            'file': script['file'],
            'success': False,
            'exit_code': -1,
            'duration': 0,
            'output': '',
            'critical': script['critical']
        }
        
        import time
        start = time.time()
        
        try:
            # Build command
            cmd = [sys.executable, str(self.scripts_dir / script['file'])]
            
            # Add arguments
            if self.args.get('config'):
                cmd.extend(['--config', self.args['config']])
            if self.args.get('modpack_dir'):
                cmd.extend(['--modpack-dir', self.args['modpack_dir']])
            if self.args.get('api_key'):
                cmd.extend(['--key', self.args['api_key']])
            if self.args.get('mc_version'):
                cmd.extend(['--version', self.args['mc_version']])
            if script['file'] == 'analyze_apis.py':
                cmd.append('--full')
            if script['file'] == 'validate_config.py':
                # Don't use --deep for speed
                pass
            
            # Run script
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per script
                cwd=str(Path(__file__).parent.parent)  # Run from project root
            )
            
            result['exit_code'] = proc.returncode
            # Consider success if exit code is 0 or 2 (warnings)
            result['success'] = (proc.returncode in [0, 2])
            result['output'] = proc.stdout
            if proc.stderr:
                result['output'] += f"\nSTDERR:\n{proc.stderr}"
            
        except subprocess.TimeoutExpired:
            result['output'] = "ERROR: Script timed out (5 minutes)"
        except Exception as e:
            result['output'] = f"ERROR: {str(e)}"
        
        result['duration'] = time.time() - start
        
        # Print summary
        status = f"{BColors.OKGREEN}✓ SUCCESS{BColors.ENDC}" if result['success'] else f"{BColors.FAIL}✗ FAILED{BColors.ENDC}"
        if result['critical'] and not result['success']:
            status = f"{BColors.FAIL}✗ CRITICAL FAILURE{BColors.ENDC}"
        
        print(f"\n{status} ({result['duration']:.1f}s)")
        
        return result
    
    def run_all(self):
        """Run all analysis scripts."""
        print(f"\n{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"{BColors.BOLD}MC QUARRY - COMPREHENSIVE ANALYSIS SUITE{BColors.ENDC}")
        print(f"{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Configuration: {self.args.get('config', 'config.json')}")
        print(f"Modpack Dir: {self.args.get('modpack_dir', 'modpack')}")
        print(f"Minecraft Version: {self.args.get('mc_version', '1.21.11')}")
        print(f"Scripts to run: {len(self.SCRIPTS)}")
        
        for script in self.SCRIPTS:
            result = self.run_script(script)
            self.results.append(result)
        
        self.generate_summary()
    
    def generate_summary(self):
        """Generate comprehensive summary report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        success_count = sum(1 for r in self.results if r['success'])
        fail_count = len(self.results) - success_count
        critical_fails = sum(1 for r in self.results if r['critical'] and not r['success'])
        
        print(f"\n\n{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"{BColors.BOLD}ANALYSIS SUMMARY{BColors.ENDC}")
        print(f"{BColors.HEADER}{'='*70}{BColors.ENDC}")
        print(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Duration: {total_duration:.1f}s")
        print(f"\n{BColors.BOLD}Results:{BColors.ENDC}")
        print(f"  Successful: {success_count}/{len(self.results)}")
        print(f"  Failed: {fail_count}")
        print(f"  Critical Failures: {critical_fails}")
        
        # Detailed results table
        print(f"\n{BColors.BOLD}Script Results:{BColors.ENDC}")
        print(f"{'Script':<25} {'Status':<15} {'Duration':<12}")
        print(f"{'-'*52}")
        
        for result in self.results:
            status = "✓ Success" if result['success'] else "✗ Failed"
            if result['critical'] and not result['success']:
                status = "✗ CRITICAL"
            
            status_color = BColors.OKGREEN if result['success'] else BColors.FAIL
            if result['critical'] and not result['success']:
                status_color = BColors.FAIL
            
            print(f"{result['name']:<25} {status_color}{status}{BColors.ENDC:<15} {result['duration']:.1f}s")
        
        # Save summary
        summary = {
            'start_time': self.start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'total_duration_seconds': total_duration,
            'configuration': self.args,
            'scripts': self.results,
            'summary': {
                'total_scripts': len(self.results),
                'successful': success_count,
                'failed': fail_count,
                'critical_failures': critical_fails
            }
        }
        
        summary_path = Path(__file__).parent.parent / 'analysis_summary.json'
        with summary_path.open('w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{BColors.OKGREEN}✓ Summary saved to: {summary_path}{BColors.ENDC}")
        
        # Generate markdown report
        self.generate_markdown_report(summary)
        
        # Exit with error if critical failures
        if critical_fails > 0:
            print(f"\n{BColors.FAIL}⚠ CRITICAL FAILURES DETECTED - Review reports above{BColors.ENDC}\n")
            sys.exit(1)
        elif fail_count > 0:
            print(f"\n{BColors.WARNING}⚠ Some scripts failed - Review reports above{BColors.ENDC}\n")
            sys.exit(2)
        else:
            print(f"\n{BColors.OKGREEN}✓ All analyses completed successfully!{BColors.ENDC}\n")
            sys.exit(0)
    
    def generate_markdown_report(self, summary: Dict[str, Any]):
        """Generate a markdown report for GitHub/issues."""
        md_path = Path(__file__).parent.parent / 'ANALYSIS_REPORT.md'
        
        with md_path.open('w') as f:
            f.write("# MC Quarry - Analysis Report\n\n")
            f.write(f"**Generated:** {summary['end_time']}\n")
            f.write(f"**Total Duration:** {summary['total_duration_seconds']:.1f}s\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Scripts Run:** {summary['summary']['total_scripts']}\n")
            f.write(f"- **Successful:** {summary['summary']['successful']}\n")
            f.write(f"- **Failed:** {summary['summary']['failed']}\n")
            f.write(f"- **Critical Failures:** {summary['summary']['critical_failures']}\n\n")
            
            f.write("## Configuration\n\n")
            f.write(f"- Config File: `{summary['configuration'].get('config', 'config.json')}`\n")
            f.write(f"- Modpack Dir: `{summary['configuration'].get('modpack_dir', 'modpack')}`\n")
            f.write(f"- MC Version: `{summary['configuration'].get('mc_version', '1.21.11')}`\n\n")
            
            f.write("## Results\n\n")
            f.write("| Script | Status | Duration |\n")
            f.write("|--------|--------|----------|\n")
            
            for script in summary['scripts']:
                status = "✅ Pass" if script['success'] else "❌ Fail"
                if script['critical'] and not script['success']:
                    status = "🔴 CRITICAL"
                f.write(f"| {script['name']} | {status} | {script['duration']:.1f}s |\n")
            
            f.write("\n---\n*Generated by run_all.py*\n")
        
        print(f"{BColors.OKGREEN}✓ Markdown report saved to: {md_path}{BColors.ENDC}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MC Quarry - Master Analysis Runner")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config.json")
    parser.add_argument("--modpack-dir", type=str, default="modpack", help="Path to modpack directory")
    parser.add_argument("--api-key", type=str, help="CurseForge API key")
    parser.add_argument("--mc-version", type=str, default="1.21.11", help="Minecraft version")
    parser.add_argument("--skip", type=str, nargs='*', help="Scripts to skip (by name)")
    args = parser.parse_args()
    
    # Convert to dict
    args_dict = vars(args)
    
    # Filter scripts if skip provided
    if args.skip:
        runner = AnalysisRunner(args_dict)
        runner.SCRIPTS = [s for s in runner.SCRIPTS if s['name'] not in args.skip]
        runner.run_all()
    else:
        runner = AnalysisRunner(args_dict)
        runner.run_all()


if __name__ == "__main__":
    main()
