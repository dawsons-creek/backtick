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
