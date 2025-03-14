"""
Models for the backtick tool.

This module provides the StagedFiles model class for managing files.
"""

import os
import concurrent.futures
from typing import List, Optional

from swallow_framework import Model, state
from backtick.ignore import IgnoreHelper


class StagedFiles(Model):
    """Manages the list of staged files with automatic state observation."""

    files = state([])  # Reactive property using `state`

    def __init__(self, ignore_file_path: str = ".backtickignore", max_workers: int = 4):
        """
        Initialize the StagedFiles model.

        Args:
            ignore_file_path: Path to the ignore file
            max_workers: Maximum number of worker threads for concurrent operations
        """
        super().__init__()
        self.base_dir = os.getcwd()
        self.max_workers = max_workers

        # Initialize the IgnoreHelper
        if os.path.exists(ignore_file_path):
            self.ignore_handler = IgnoreHelper.from_file(ignore_file_path)
        else:
            # Create an empty ignore handler if no file exists
            self.ignore_handler = IgnoreHelper.from_content("")

    def add_file(self, file_name: str) -> bool:
        """
        Adds a file to the staged files list.

        Args:
            file_name: Path to the file to add

        Returns:
            True if the file was added, False otherwise
        """
        relative_path = os.path.relpath(file_name, self.base_dir)

        # Check if the path should be ignored
        if self.ignore_handler.is_ignored(relative_path):
            print(f"Skipping ignored file: {relative_path}")
            return False

        # Check if the file already exists in the list
        if relative_path not in self.files:
            self.files.append(relative_path)  # Auto-notifies watchers
            print(f"Added {file_name} to staged files.")
            return True

        return False

    def add_directory(self, dir_name: str, recursive: bool = True) -> int:
        """
        Adds all files from a directory to staged files.

        Args:
            dir_name: Path to the directory to add
            recursive: Whether to recursively add subdirectories (default is True)

        Returns:
            The number of files added
        """
        dir_path = os.path.relpath(dir_name, self.base_dir)
        absolute_dir_path = os.path.join(self.base_dir, dir_path)

        if not os.path.exists(absolute_dir_path):
            print(f"Error: Directory '{dir_name}' does not exist.")
            return 0

        if not os.path.isdir(absolute_dir_path):
            print(f"Error: '{dir_name}' is not a directory.")
            return 0

        # Get non-ignored files from the directory
        all_files = self.ignore_handler.filter_paths(absolute_dir_path, recursive=recursive)

        if not all_files:
            print(f"No files found in directory '{dir_name}'.")
            return 0

        # Filter files (exclude directories)
        file_paths = [f for f in all_files if os.path.isfile(f)]

        if not file_paths:
            print(f"No files found in directory '{dir_name}' (only directories).")
            return 0

        # Collect all new files first
        new_files = []
        for file_path in file_paths:
            relative_path = os.path.relpath(file_path, self.base_dir)
            if relative_path not in self.files:
                new_files.append(relative_path)

        # Using the batch update feature of ObservableList if available
        if new_files:
            if hasattr(self.files, 'begin_batch_update'):
                self.files.begin_batch_update()
                for file_path in new_files:
                    self.files.append(file_path)
                self.files.end_batch_update()
            else:
                # If batch update not available, add files one by one
                for file_path in new_files:
                    self.files.append(file_path)

        added_count = len(new_files)
        total_files = len(file_paths)
        skipped_count = total_files - added_count

        if skipped_count > 0:
            print(f"Added {added_count} files from directory '{dir_name}' (skipped {skipped_count} already staged files).")
        else:
            print(f"Added {added_count} files from directory '{dir_name}'.")

        return added_count

    def add_directory_parallel(self, dir_name: str, recursive: bool = True) -> int:
        """
        Adds all files from a directory to staged files using parallel processing.

        Args:
            dir_name: Path to the directory to add
            recursive: Whether to recursively add subdirectories (default is True)

        Returns:
            The number of files added
        """
        dir_path = os.path.relpath(dir_name, self.base_dir)
        absolute_dir_path = os.path.join(self.base_dir, dir_path)

        if not os.path.exists(absolute_dir_path):
            print(f"Error: Directory '{dir_name}' does not exist.")
            return 0

        if not os.path.isdir(absolute_dir_path):
            print(f"Error: '{dir_name}' is not a directory.")
            return 0

        # Get non-ignored files from the directory
        all_files = self.ignore_handler.filter_paths(absolute_dir_path, recursive=recursive)

        if not all_files:
            print(f"No files found in directory '{dir_name}'.")
            return 0

        # Filter files (exclude directories)
        file_paths = [f for f in all_files if os.path.isfile(f)]

        if not file_paths:
            print(f"No files found in directory '{dir_name}' (only directories).")
            return 0

        # Get current file list for comparison
        current_files = set(self.files)
        added_files = []

        # Process files in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create a dictionary to map futures to file paths
            future_to_path = {
                executor.submit(self._process_file, file_path): file_path
                for file_path in file_paths
            }

            # Process futures as they complete
            for future in concurrent.futures.as_completed(future_to_path):
                relative_path = future.result()
                if relative_path and relative_path not in current_files:
                    added_files.append(relative_path)

        # Add all new files in a batch if possible
        if added_files:
            if hasattr(self.files, 'begin_batch_update'):
                self.files.begin_batch_update()
                for file_path in added_files:
                    self.files.append(file_path)
                self.files.end_batch_update()
            else:
                # If batch update not available, add files one by one
                for file_path in added_files:
                    self.files.append(file_path)

        # Report results
        added_count = len(added_files)
        total_files = len(file_paths)
        skipped_count = total_files - added_count

        if skipped_count > 0:
            print(f"Added {added_count} files from directory '{dir_name}' (skipped {skipped_count} already staged files).")
        else:
            print(f"Added {added_count} files from directory '{dir_name}'.")

        return added_count

    def _process_file(self, file_path: str) -> Optional[str]:
        """
        Process a single file for parallel directory scanning.

        Args:
            file_path: Path to the file to process

        Returns:
            The relative path if the file should be added, None otherwise
        """
        relative_path = os.path.relpath(file_path, self.base_dir)

        # Check if the file should be ignored
        if self.ignore_handler.is_ignored(relative_path):
            return None

        return relative_path

    def remove_file(self, file_name: str) -> bool:
        """
        Removes a file from the staged list.

        Args:
            file_name: Path to the file to remove

        Returns:
            True if the file was removed, False otherwise
        """
        relative_path = os.path.relpath(file_name, self.base_dir)

        if relative_path in self.files:
            self.files.remove(relative_path)  # Auto-notifies watchers
            print(f"File removed: {relative_path}")
            return True
        else:
            print(f"File not found: {relative_path}")
            return False

    def clear_files(self) -> None:
        """Clears all staged files."""
        self.files.clear()
        print("Cleared all staged files.")

    def get_file_count(self) -> int:
        """
        Get the number of staged files.

        Returns:
            The number of staged files
        """
        return len(self.files)