#!/usr/bin/env python3
"""
Backfill metadata for existing images
Run this once to create metadata entries for all existing uploads
"""

import sys
from pathlib import Path
from datetime import datetime

# Add venv to path
sys.path.insert(0, '/var/www/vibe-screenshots/venv/lib/python3.12/site-packages')

from PIL import Image
import pillow_heif

# Register HEIF opener
pillow_heif.register_heif_opener()

from metadata_store import MetadataStore

def backfill_existing_images():
    """Create metadata entries for all existing images"""
    source_dir = Path("source")

    if not source_dir.exists():
        print(f"❌ Error: {source_dir} directory not found")
        return

    store = MetadataStore(source_dir)
    existing_metadata = store.get_all_metadata()

    # Image extensions to process
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}

    # Files to skip
    skip_files = {'lister.py', 'index.html', 'image_widths_heights.json', 'uploads_metadata.json'}

    processed = 0
    skipped = 0
    errors = 0

    print(f"🔍 Scanning {source_dir} for images...")

    for file_path in sorted(source_dir.iterdir()):
        # Skip if not a file or in skip list
        if not file_path.is_file() or file_path.name in skip_files:
            continue

        # Skip if not an image extension
        if file_path.suffix.lower() not in image_extensions:
            continue

        # Skip if already has metadata
        if file_path.name in existing_metadata:
            print(f"⏭️  Skipped (already has metadata): {file_path.name}")
            skipped += 1
            continue

        try:
            # Get image info
            with Image.open(file_path) as img:
                width, height = img.size
                format_type = img.format.lower() if img.format else 'unknown'

            # Get file size
            size_bytes = file_path.stat().st_size

            # Determine content type
            content_type = f"image/{format_type}"
            if format_type == 'jpeg':
                content_type = "image/jpeg"

            # Record metadata (using current timestamp as fallback)
            store.record_upload(
                filename=file_path.name,
                original_filename=file_path.name,  # We don't know the original
                size_bytes=size_bytes,
                dimensions=(width, height),
                content_type=content_type,
                additional_data={"backfilled": True}  # Mark as backfilled
            )

            print(f"✅ Added metadata: {file_path.name} ({width}x{height}, {size_bytes:,} bytes)")
            processed += 1

        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            errors += 1

    print(f"\n📊 Summary:")
    print(f"   Processed: {processed}")
    print(f"   Skipped (already had metadata): {skipped}")
    print(f"   Errors: {errors}")
    print(f"\n💾 Metadata saved to: {source_dir}/uploads_metadata.json")

if __name__ == "__main__":
    backfill_existing_images()
