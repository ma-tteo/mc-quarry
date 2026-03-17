#!/usr/bin/env python3
"""
Test hardware detection on the current system.

Usage:
    python3 scripts/test_hardware.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.ui_manager import detect_hardware


def main():
    import platform

    print("=" * 60)
    print("Hardware Detection Test")
    print("=" * 60)

    print(f"\nPlatform: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")

    print("\nDetecting hardware...")
    hardware = detect_hardware()

    print(f"\nResults:")
    print(f"  GPU: {hardware['gpu']}")
    print(f"  CPU Cores: {hardware['cpu_cores']}")

    # Validate results
    valid_gpus = ["nvidia", "amd", "intel", "apple", "generic"]
    if hardware["gpu"] not in valid_gpus:
        print(f"\n  ⚠️  Unknown GPU type: {hardware['gpu']}")
    else:
        print(f"\n  ✅ GPU detection successful")

    if hardware["cpu_cores"] < 1:
        print(f"  ❌ Invalid CPU core count: {hardware['cpu_cores']}")
    else:
        print(f"  ✅ CPU detection successful")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
