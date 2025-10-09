# Metadata System Documentation

## Overview

The screenshot gallery now includes a comprehensive metadata tracking system that records information about each uploaded image and automatically keeps all metadata files synchronized.

## Metadata Files

### 1. `source/uploads_metadata.json`
**Purpose:** Stores detailed metadata for each uploaded image

**Structure:**
```json
{
  "filename.png": {
    "uploaded_at": "2025-10-09T22:33:33.867600Z",
    "original_filename": "my_screenshot.png",
    "size_bytes": 287,
    "dimensions": [100, 100],
    "content_type": "image/png"
  }
}
```

**Fields:**
- `uploaded_at`: ISO 8601 timestamp
- `original_filename`: Original filename before UUID rename
- `size_bytes`: File size in bytes
- `dimensions`: [width, height] in pixels
- `content_type`: MIME type (e.g., "image/png")
- `backfilled`: (optional) true if added via backfill script

### 2. `source/image_widths_heights.json`
**Purpose:** Quick lookup for gallery display (used by static gallery)

**Structure:**
```json
[
  ["filename.png", [width, height]],
  ...
]
```

## Automatic Cleanup

Both upload servers (`upload_app.py` and `railway_app.py`) **automatically clean up metadata** after every upload:

1. **Removes orphaned entries** from `uploads_metadata.json` (files that no longer exist)
2. **Regenerates** `image_widths_heights.json` from actual files on disk
3. **Ensures sync** between metadata and actual images

**Response includes cleanup stats:**
```json
{
  "uploaded_count": 1,
  "uploaded_files": ["abc123.png"],
  "errors": [],
  "cleanup": {
    "success": true,
    "orphaned_removed": 0,
    "output": "Successfully created image_widths_heights.json with 13 files."
  }
}
```

## Manual Cleanup

If you manually delete images, run the cleanup utility:

```bash
# Verbose output
python3 cleanup_metadata.py

# Quiet mode
python3 cleanup_metadata.py --quiet

# JSON output (for scripting)
python3 cleanup_metadata.py --json

# Custom source directory
python3 cleanup_metadata.py --source-dir /path/to/source
```

**Cleanup performs:**
- ✅ Removes orphaned metadata entries
- ✅ Regenerates image_widths_heights.json
- ✅ Verifies all metadata is in sync
- ✅ Reports statistics

## Backfilling Existing Images

To add metadata for images that existed before this system:

```bash
python3 backfill_metadata.py
```

This was already run once to backfill all 13 existing images with current timestamp.

## Using the Metadata API

### Python (metadata_store.py)

```python
from pathlib import Path
from metadata_store import MetadataStore

store = MetadataStore(Path("source"))

# Get metadata for specific file
metadata = store.get_metadata("abc123.png")
print(metadata['uploaded_at'])

# Get all metadata
all_meta = store.get_all_metadata()

# Record new upload
store.record_upload(
    filename="newimage.png",
    original_filename="screenshot.png",
    size_bytes=12345,
    dimensions=(800, 600),
    content_type="image/png"
)

# Clean up orphaned entries
removed = store.cleanup_orphaned_metadata()
print(f"Removed {removed} orphaned entries")
```

## Future Features Enabled

With metadata in place, you can now easily add:

- **Sort by date**: Display newest/oldest images first
- **Date filters**: Show images from specific date ranges
- **File size analytics**: Track storage usage
- **Original filename search**: Find images by their original name
- **Upload statistics**: Daily/weekly upload counts
- **Auto-delete old images**: Remove images older than X days
- **Duplicate detection**: Find images with same dimensions/size

## File Structure

```
vibe-screenshots/
├── metadata_store.py          # Core metadata storage module
├── cleanup_metadata.py        # Cleanup utility (standalone)
├── backfill_metadata.py       # One-time backfill script
├── upload_app.py              # Development upload server (auto-cleanup)
├── railway_app.py             # Production server (auto-cleanup)
└── source/
    ├── uploads_metadata.json  # Detailed metadata
    └── image_widths_heights.json  # Display dimensions
```

## Best Practices

1. **Never manually edit metadata files** - Use the API or cleanup utility
2. **Run cleanup after manual deletions** - Or just upload something (auto-cleanup)
3. **Backup metadata periodically** - It's valuable historical data
4. **Don't commit uploads_metadata.json** - Already in `.gitignore`

## Troubleshooting

### Blank thumbnails in gallery
**Cause:** Orphaned entries in `image_widths_heights.json`
**Solution:** Run `python3 cleanup_metadata.py`

### Metadata out of sync
**Cause:** Manual file operations
**Solution:** Run `python3 cleanup_metadata.py`

### Missing metadata for old images
**Cause:** Images uploaded before metadata system
**Solution:** Run `python3 backfill_metadata.py`

## Technical Details

- **Thread-safe**: Uses file-based locking
- **Atomic operations**: Metadata writes are atomic
- **Error handling**: Graceful degradation if cleanup fails
- **Performance**: Minimal overhead (~100ms per cleanup)
