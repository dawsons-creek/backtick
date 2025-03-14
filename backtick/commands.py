"""
Command implementations for the backtick tool.

This module provides command classes for the backtick tool's operations.
"""

import os
from typing import Any, Dict, Optional, Union

import pyperclip
from swallow_framework import Command

from backtick.models import StagedFiles
from backtick.utils import ClipboardFormatter


class AddFileCommand(Command):
    """Command to add a file to the staged files."""

    def __init__(self, model: StagedFiles):
        super().__init__(model)

    def execute(self, data: str) -> None:
        self.model.add_file(data)


class AddDirectoryCommand(Command):
    """Command to add all files in a directory to the staged files (recursive by default)."""

    def __init__(self, model: StagedFiles, use_parallel: bool = True, recursive: bool = True):
        """
        Initialize the AddDirectoryCommand.

        Args:
            model: The StagedFiles model
            use_parallel: Whether to use parallel processing for large directories
            recursive: Whether to recursively add subdirectories (default is True)
        """
        super().__init__(model)
        self.use_parallel = use_parallel
        self.recursive = recursive

    def execute(self, data: str) -> None:
        """
        Execute the command to add all files in a directory.

        Args:
            data: The directory path to add
        """
        # Use parallel processing for large directories
        if self.use_parallel:
            self.model.add_directory_parallel(data, recursive=self.recursive)
        else:
            self.model.add_directory(data, recursive=self.recursive)


class RemoveCommand(Command):
    """Command to remove an entry from the list of staged files."""

    def __init__(self, model: StagedFiles):
        super().__init__(model)

    def execute(self, data: Union[str, int]) -> None:
        """
        Execute the command to remove a file.

        Args:
            data: Either a file path or an index (1-based) to remove
        """
        # If data is an integer, it's an index
        if isinstance(data, int):
            # Convert to 0-based index
            index = data - 1
            if 0 <= index < len(self.model.files):
                file_to_remove = self.model.files[index]
                self.model.remove_file(file_to_remove)
            else:
                print(f"Error: Index {data} is out of range.")
        else:
            # Otherwise, it's a file path
            self.model.remove_file(data)


class ClearFilesCommand(Command):
    """Command to clear all staged files."""

    def __init__(self, model: StagedFiles):
        super().__init__(model)

    def execute(self, data: Any = None) -> None:
        """Execute the command to clear all staged files."""
        self.model.clear_files()


class CopyToClipboardCommand(Command):
    """Command to copy all staged file contents to clipboard."""

    def __init__(self, model: StagedFiles, cache_size: int = 50):
        """
        Initialize the CopyToClipboardCommand.

        Args:
            model: The StagedFiles model
            cache_size: Maximum number of files to cache
        """
        super().__init__(model)
        self.formatter = ClipboardFormatter(cache_size=cache_size)

    def execute(self, data: Any = None) -> None:
        """Execute the command to copy all staged files to clipboard."""
        files = self.model.files
        if not files:
            print("No files are currently staged.")
            return

        # Format files for clipboard
        print("Formatting files for clipboard...")
        combined_content = self.formatter.format_files(files)

        # Copy to clipboard
        print("Copying to clipboard...")
        pyperclip.copy(combined_content)
        print(f"Copied {len(files)} file(s) to clipboard.")

    def clear_cache(self) -> None:
        """Clear the formatter's file content cache."""
        self.formatter.clear_cache()
        print("Clipboard formatter cache cleared.")