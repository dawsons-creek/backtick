import fnmatch
import logging
import os
from pathlib import Path
from typing import List

from prompt_toolkit.completion import PathCompleter


class ClipboardFormatter:
    """Class to format staged files for clipboard with caching."""

    def __init__(self):
        self.file_cache = {}  # Cache to store file contents

    def format_files(self, files):
        result = []

        for file_path in files:
            try:
                # Use cached content if available, otherwise read the file
                if file_path not in self.file_cache:
                    with open(file_path, 'r') as f:
                        self.file_cache[file_path] = f.read()

                content = self.file_cache[file_path]

                # Add file path as a comment and wrap in code block
                relative_path = os.path.relpath(file_path)
                result.append(f"{relative_path}\n\n```\n{content}\n```\n\n")
            except Exception as e:
                result.append(f"Error reading {file_path}: {str(e)}\n\n")

        # Join all file contents
        return "".join(result).rstrip()

    def clear_cache(self):
        """Clear the file content cache."""
        self.file_cache.clear()


class IgnoreHandler:
    """Handles file ignoring functionality based on .backtickignore patterns."""

    def __init__(self):
        self.ignore_patterns: List[str] = []
        self.logger = logging.getLogger(__name__)
        self._load_ignore_patterns()

    def _load_ignore_patterns(self) -> None:
        """Load ignore patterns from .backtickignore file."""
        ignore_file_path = Path('.backtickignore')

        if not ignore_file_path.exists():
            self.logger.info("No .backtickignore file found.")
            return

        try:
            with open(ignore_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                self.ignore_patterns.append(line)

            self.logger.info(f"Loaded {len(self.ignore_patterns)} patterns from .backtickignore")
        except Exception as e:
            self.logger.error(f"Error reading .backtickignore file: {e}")

    def should_ignore(self, file_path: str) -> bool:
        """Determine if a file should be ignored based on ignore patterns."""
        if not self.ignore_patterns:
            return False

        # Normalize path with forward slashes
        file_path = file_path.replace('\\', '/')

        # Get just the filename part
        filename = os.path.basename(file_path)

        for pattern in self.ignore_patterns:
            self.logger.debug(f"Checking pattern: {pattern} for file: {file_path}")

            # Case 1: Exact filename match (e.g., "__init__.py")
            if pattern == filename:
                self.logger.debug(f"Ignoring {file_path} - exact filename match: {pattern}")
                return True

            # Case 2: Direct path match (e.g., "app/config.py")
            if fnmatch.fnmatch(file_path, pattern):
                self.logger.debug(f"Ignoring {file_path} - path matches pattern: {pattern}")
                return True

            # Case 3: Files in any directory matching pattern (e.g., "*/__init__.py")
            if pattern.startswith('*/') and filename == pattern[2:]:
                self.logger.debug(f"Ignoring {file_path} - matches single-level directory pattern: {pattern}")
                return True

            # Case 4: Files in any subdirectory matching pattern (e.g., "**/__init__.py")
            if pattern.startswith('**/') and filename == pattern[3:]:
                self.logger.debug(f"Ignoring {file_path} - matches multi-level directory pattern: {pattern}")
                return True

            # Case 5: Directory contains pattern (e.g., "node_modules/")
            if pattern.endswith('/') and (file_path.startswith(pattern) or f"{pattern}/" in file_path):
                self.logger.debug(f"Ignoring {file_path} - in ignored directory: {pattern}")
                return True

        return False

    def print_patterns(self) -> None:
        """Print all loaded ignore patterns for debugging."""
        if not self.ignore_patterns:
            print("No ignore patterns loaded.")
            return

        print("Loaded ignore patterns:")
        for i, pattern in enumerate(self.ignore_patterns, 1):
            print(f"{i}. {pattern}")


class IgnoreAwarePathCompleter(PathCompleter):
    """Enhanced path completer that respects ignore patterns."""

    def __init__(self, *args, **kwargs):
        # Force min_input_len to 1 to show suggestions after first character
        kwargs['min_input_len'] = 1
        self.ignore_handler = IgnoreHandler()

        # If a custom file_filter is provided, wrap it with our ignore filter
        original_file_filter = kwargs.get('file_filter', None)

        def ignore_filter(path):
            # Skip if already filtered by original filter
            if original_file_filter and not original_file_filter(path):
                return False

            # Check if this path should be ignored
            relative_path = os.path.relpath(path)
            return not self.ignore_handler.should_ignore(relative_path)

        kwargs['file_filter'] = ignore_filter
        super().__init__(*args, **kwargs)

