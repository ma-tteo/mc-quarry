#!/usr/bin/env python3
"""
Test Modrinth and CurseForge API connectivity.

Usage:
    python3 scripts/test_connection.py [--modrinth] [--curseforge] [--key YOUR_API_KEY]
"""
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mc_quarry.api_client import APIClient


def test_modrinth():
    """Test Modrinth API connectivity."""
    print("=" * 60)
    print("Testing Modrinth API...")
    print("=" * 60)

    client = APIClient()
    start = time.time()

    # Test search
    print("\n[1/3] Testing search API...")
    result = client.search_modrinth("sodium", "mod", limit=1)
    if result and "hits" in result:
        print(f"  ✅ Search OK - Found {len(result['hits'])} results")
        if result["hits"]:
            print(f"     First result: {result['hits'][0].get('title', 'Unknown')}")
    else:
        print("  ❌ Search failed")
        return False

    # Test project lookup
    print("\n[2/3] Testing project lookup...")
    project = client.get_modrinth_project("sodium")
    if project:
        print(f"  ✅ Project lookup OK - {project.get('title', 'Unknown')}")
        print(f"     ID: {project.get('id', 'Unknown')}")
    else:
        print("  ❌ Project lookup failed")
        return False

    # Test version lookup
    print("\n[3/3] Testing version lookup...")
    version = client.find_modrinth_version(
        project.get("id", ""),
        "1.21.1",
        loader="fabric"
    )
    if version:
        print(f"  ✅ Version lookup OK - {version.get('name', 'Unknown')}")
    else:
        print("  ❌ Version lookup failed")
        return False

    elapsed = time.time() - start
    print(f"\n✅ All Modrinth tests passed in {elapsed:.2f}s")
    return True


def test_curseforge(api_key: str):
    """Test CurseForge API connectivity."""
    print("=" * 60)
    print("Testing CurseForge API...")
    print("=" * 60)

    if not api_key:
        print("  ℹ️  No API key provided. Skipping CurseForge tests.")
        print("  ℹ️  Use --key YOUR_API_KEY to test CurseForge")
        return True  # Not a failure, just skipped

    client = APIClient(cf_api_key=api_key)
    start = time.time()

    # Test search
    print("\n[1/3] Testing search API...")
    result = client.search_curseforge("jei", class_id=6)
    if result:
        print(f"  ✅ Search OK - Found {result.get('name', 'Unknown')}")
    else:
        print("  ❌ Search failed")
        return False

    # Test file lookup
    print("\n[2/3] Testing file lookup...")
    file_info = client.get_latest_file_cf(result["id"], "1.21.1", mod_loader_type=4)
    if file_info:
        print(f"  ✅ File lookup OK - {file_info.get('fileName', 'Unknown')}")
    else:
        print("  ❌ File lookup failed")
        return False

    elapsed = time.time() - start
    print(f"\n✅ All CurseForge tests passed in {elapsed:.2f}s")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test API connectivity")
    parser.add_argument("--modrinth", action="store_true", help="Test Modrinth API only")
    parser.add_argument("--curseforge", action="store_true", help="Test CurseForge API only")
    parser.add_argument("--key", type=str, help="CurseForge API key")
    args = parser.parse_args()

    success = True

    if args.modrinth or not (args.modrinth or args.curseforge):
        if not test_modrinth():
            success = False

    if args.curseforge:
        if not test_curseforge(args.key or ""):
            success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
