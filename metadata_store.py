#!/usr/bin/env python3
"""
Metadata storage for uploaded images
Tracks upload timestamp and other metadata for future extensibility
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import threading

class MetadataStore:
    """Thread-safe metadata storage for uploaded images"""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.metadata_file = storage_path / "uploads_metadata.json"
        self.lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create metadata file if it doesn't exist"""
        if not self.metadata_file.exists():
            with self.lock:
                self.metadata_file.write_text("{}")

    def _read_metadata(self) -> Dict[str, Any]:
        """Read metadata from file"""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write_metadata(self, data: Dict[str, Any]):
        """Write metadata to file"""
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def record_upload(
        self,
        filename: str,
        original_filename: str,
        size_bytes: int,
        dimensions: tuple[int, int],
        content_type: str,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """
        Record metadata for an uploaded image

        Args:
            filename: UUID-based filename stored on disk
            original_filename: Original filename from upload
            size_bytes: File size in bytes
            dimensions: (width, height) tuple
            content_type: MIME type
            additional_data: Optional dict of extra metadata
        """
        with self.lock:
            metadata = self._read_metadata()

            entry = {
                "uploaded_at": datetime.utcnow().isoformat() + "Z",
                "original_filename": original_filename,
                "size_bytes": size_bytes,
                "dimensions": list(dimensions),
                "content_type": content_type
            }

            # Add any additional metadata
            if additional_data:
                entry.update(additional_data)

            metadata[filename] = entry
            self._write_metadata(metadata)

    def get_metadata(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific file"""
        with self.lock:
            metadata = self._read_metadata()
            return metadata.get(filename)

    def get_all_metadata(self) -> Dict[str, Any]:
        """Get all metadata"""
        with self.lock:
            return self._read_metadata()

    def delete_metadata(self, filename: str):
        """Delete metadata for a specific file"""
        with self.lock:
            metadata = self._read_metadata()
            if filename in metadata:
                del metadata[filename]
                self._write_metadata(metadata)

    def cleanup_orphaned_metadata(self) -> int:
        """
        Remove metadata entries for files that no longer exist
        Returns number of entries cleaned up
        """
        with self.lock:
            metadata = self._read_metadata()
            existing_files = {f.name for f in self.storage_path.iterdir() if f.is_file()}

            # Find metadata entries without corresponding files
            orphaned = [
                filename for filename in metadata.keys()
                if filename not in existing_files and filename != "uploads_metadata.json"
            ]

            # Remove orphaned entries
            for filename in orphaned:
                del metadata[filename]

            if orphaned:
                self._write_metadata(metadata)

            return len(orphaned)
