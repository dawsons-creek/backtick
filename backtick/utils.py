"""
Utility functions for the backtick tool.

This module provides utility classes and functions for formatting files for clipboard.
"""

import io
import logging
import os
import mimetypes
from io import StringIO
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

from cachetools import LRUCache


class FileType:
    """File type constants."""
    TEXT = "text"
    BINARY = "binary"
    UNKNOWN = "unknown"


def detect_file_type(file_path: str) -> str:
    """
    Detect if a file is text or binary.

    Args:
        file_path: Path to the file

    Returns:
        A string indicating the file type: 'text', 'binary', or 'unknown'
    """
    # Check mime type first
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        main_type = mime_type.split('/')[0]
        if main_type == 'text':
            return FileType.TEXT
        elif main_type in ('audio', 'image', 'video', 'application'):
            return FileType.BINARY

    # If mime type doesn't give a clear answer, try to read the file
    try:
        with open(file_path, 'rb') as f:
            # Read the first 8KB of the file
            data = f.read(8192)

        # Count null bytes and control characters
        null_count = data.count(0)
        control_count = sum(1 for c in data if c < 32 and c != 9 and c != 10 and c != 13)

        # Heuristic: If more than 10% are null or control chars, likely binary
        total = len(data)
        if total == 0:
            return FileType.TEXT  # Empty file is considered text

        if (null_count + control_count) / total > 0.1:
            return FileType.BINARY
        return FileType.TEXT
    except Exception as e:
        logging.error(f"Error detecting file type for {file_path}: {e}")
        return FileType.UNKNOWN


class ClipboardFormatter:
    """Class to format staged files for clipboard with LRU caching."""

    def __init__(self, cache_size: int = 50, chunk_size: int = 4096):
        """
        Initialize the ClipboardFormatter.

        Args:
            cache_size: Maximum number of files to cache
            chunk_size: Size of chunks to read from files
        """
        self.file_cache = LRUCache(maxsize=cache_size)  # LRU cache with size limit
        self.chunk_size = chunk_size

    def format_files(self, files: List[str]) -> str:
        """
        Format a list of files for clipboard.

        Args:
            files: List of file paths to format

        Returns:
            A formatted string with all file contents
        """
        # Use StringIO for efficient string building
        buffer = StringIO()

        for file_path in files:
            try:
                # Check if the file is a text file
                file_type = detect_file_type(file_path)
                if file_type == FileType.BINARY:
                    # Skip binary files or handle differently
                    relative_path = os.path.relpath(file_path)
                    buffer.write(f"{relative_path}\n\n```\n[BINARY FILE - CONTENT NOT SHOWN]\n```\n\n")
                    continue
                elif file_type == FileType.UNKNOWN:
                    # Handle unknown file types
                    relative_path = os.path.relpath(file_path)
                    buffer.write(f"{relative_path}\n\n```\n[UNKNOWN FILE TYPE - CONTENT NOT SHOWN]\n```\n\n")
                    continue

                # Use cached content if available, otherwise read the file
                if file_path not in self.file_cache:
                    self.file_cache[file_path] = self._read_file_in_chunks(file_path)

                content = self.file_cache[file_path]

                # Add file path as a comment and wrap in code block
                relative_path = os.path.relpath(file_path)
                buffer.write(f"{relative_path}\n\n```\n{content}\n```\n\n")
            except Exception as e:
                buffer.write(f"Error reading {file_path}: {str(e)}\n\n")

        # Return the built string
        return buffer.getvalue().rstrip()

    def _read_file_in_chunks(self, file_path: str) -> str:
        """
        Reads a text file in chunks to avoid high memory usage.

        Args:
            file_path: Path to the file to read

        Returns:
            The file contents as a string
        """
        buffer = StringIO()
        try:
            with open(file_path, 'r', encoding="utf-8", errors="replace") as f:
                for chunk in iter(lambda: f.read(self.chunk_size), ''):
                    buffer.write(chunk)
        except Exception as e:
            return f"Error reading file: {str(e)}"

        return buffer.getvalue()

    def clear_cache(self) -> None:
        """Clear the file content cache."""
        self.file_cache.clear()