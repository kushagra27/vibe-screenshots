#!/usr/bin/env python3
"""
Cleanup utility for metadata synchronization
Removes orphaned entries and ensures all metadata is in sync with actual files
"""

import sys
import json
import subprocess
from pathlib import Path

# Add venv to path
sys.path.insert(0, '/var/www/vibe-screenshots/venv/lib/python3.12/site-packages')

from PIL import Image
import pillow_heif
from metadata_store import MetadataStore

# Register HEIF opener
pillow_heif.register_heif_opener()

def cleanup_all_metadata(source_dir: Path, verbose: bool = True) -> dict:
    """
    Sync all metadata files with actual images on disk

    Returns:
        dict with cleanup statistics
    """
    stats = {
        'uploads_metadata_removed': 0,
        'image_widths_heights_regenerated': False,
        'total_images': 0,
        'errors': []
    }

    if not source_dir.exists():
        stats['errors'].append(f"Source directory not found: {source_dir}")
        return stats

    # Step 1: Clean up uploads_metadata.json
    if verbose:
        print("🧹 Step 1: Cleaning uploads_metadata.json...")

    try:
        store = MetadataStore(source_dir)
        removed = store.cleanup_orphaned_metadata()
        stats['uploads_metadata_removed'] = removed

        if verbose:
            if removed > 0:
                print(f"   ✅ Removed {removed} orphaned entries")
            else:
                print("   ✅ No orphaned entries found")
    except Exception as e:
        error_msg = f"Error cleaning uploads_metadata.json: {e}"
        stats['errors'].append(error_msg)
        if verbose:
            print(f"   ❌ {error_msg}")

    # Step 2: Regenerate image_widths_heights.json
    if verbose:
        print("\n🔄 Step 2: Regenerating image_widths_heights.json...")

    try:
        result = subprocess.run(
            [sys.executable, "lister.py"],
            cwd=source_dir,
            capture_output=True,
            text=True,
            check=True
        )

        stats['image_widths_heights_regenerated'] = True

        if verbose:
            print(f"   ✅ {result.stdout.strip()}")

        # Count actual images
        with open(source_dir / "image_widths_heights.json", 'r') as f:
            images = json.load(f)
            stats['total_images'] = len(images)

    except subprocess.CalledProcessError as e:
        error_msg = f"Error regenerating image_widths_heights.json: {e.stderr}"
        stats['errors'].append(error_msg)
        if verbose:
            print(f"   ❌ {error_msg}")
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        stats['errors'].append(error_msg)
        if verbose:
            print(f"   ❌ {error_msg}")

    # Step 3: Verify synchronization
    if verbose:
        print("\n🔍 Step 3: Verifying synchronization...")

    try:
        # Get list from uploads_metadata.json
        metadata_files = set(store.get_all_metadata().keys())

        # Get list from image_widths_heights.json
        with open(source_dir / "image_widths_heights.json", 'r') as f:
            image_list_files = set(img for img, _ in json.load(f))

        # Get actual files on disk
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}
        actual_files = {
            f.name for f in source_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        }

        # Check for mismatches
        only_in_metadata = metadata_files - actual_files
        only_in_image_list = image_list_files - actual_files
        only_on_disk = actual_files - metadata_files

        if verbose:
            if only_in_metadata:
                print(f"   ⚠️  In uploads_metadata but not on disk: {len(only_in_metadata)}")
                for f in list(only_in_metadata)[:3]:
                    print(f"      - {f}")

            if only_in_image_list:
                print(f"   ⚠️  In image_widths_heights but not on disk: {len(only_in_image_list)}")
                for f in list(only_in_image_list)[:3]:
                    print(f"      - {f}")

            if only_on_disk:
                print(f"   ℹ️  On disk but not in metadata: {len(only_on_disk)}")
                print(f"      (These will be added on next upload or manual backfill)")

            if not (only_in_metadata or only_in_image_list):
                print("   ✅ All metadata files are in sync!")

        stats['only_in_metadata'] = len(only_in_metadata)
        stats['only_in_image_list'] = len(only_in_image_list)
        stats['only_on_disk'] = len(only_on_disk)

    except Exception as e:
        error_msg = f"Error during verification: {e}"
        stats['errors'].append(error_msg)
        if verbose:
            print(f"   ❌ {error_msg}")

    return stats

def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Cleanup and sync metadata files')
    parser.add_argument('--source-dir', default='source', help='Source directory path')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    verbose = not args.quiet

    if verbose and not args.json:
        print("=" * 80)
        print("🧹 Metadata Cleanup Utility")
        print("=" * 80)
        print()

    stats = cleanup_all_metadata(source_dir, verbose=verbose and not args.json)

    if args.json:
        print(json.dumps(stats, indent=2))
    elif verbose:
        print()
        print("=" * 80)
        print("📊 Cleanup Summary")
        print("=" * 80)
        print(f"Total images: {stats['total_images']}")
        print(f"Orphaned entries removed: {stats['uploads_metadata_removed']}")
        print(f"Image list regenerated: {'Yes' if stats['image_widths_heights_regenerated'] else 'No'}")
        if stats['errors']:
            print(f"Errors: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"  - {error}")
        else:
            print("Errors: None")
        print()
        print("✅ Cleanup complete!")

    # Exit with error code if there were errors
    return 1 if stats['errors'] else 0

if __name__ == "__main__":
    sys.exit(main())
