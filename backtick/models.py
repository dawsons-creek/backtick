"""
Models for the backtick tool.

This module provides the StagedFiles model class for managing files.
"""

import os
import concurrent.futures
import logging
from pathlib import Path
from typing import List, Optional, Set, Union

from swallow_framework import Model, state
from backtick.ignore import IgnoreHelper


class StagedFiles(Model):
    """Manages the list of staged files with automatic state observation."""

    files = state([])  # Reactive property using `state`

    def __init__(self, ignore_file_path: Union[str, Path] = ".backtickignore", max_workers: int = 4):
        """
        Initialize the StagedFiles model.

        Args:
            ignore_file_path: Path to the ignore file
            max_workers: Maximum number of worker threads for concurrent operations
        """
        super().__init__()
        self.base_dir = Path(os.getcwd())
        self.max_workers = max_workers
        ignore_file_path = Path(ignore_file_path)

        # Initialize the IgnoreHelper
        if ignore_file_path.exists():
            self.ignore_handler = IgnoreHelper.from_file(str(ignore_file_path))
        else:
            # Create an empty ignore handler if no file exists
            self.ignore_handler = IgnoreHelper.from_content("")

    def add_file(self, file_name: Union[str, Path]) -> bool:
        """
        Adds a file to the staged files list.

        Args:
            file_name: Path to the file to add

        Returns:
            True if the file was added, False otherwise
        """
        file_path = Path(file_name)
        relative_path = str(file_path.relative_to(self.base_dir) if file_path.is_absolute()
                         else file_path)

        if not file_path.exists():
            print(f"Error: File '{file_name}' does not exist.")
            return False

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

    def add_directory(self, dir_name: Union[str, Path], recursive: bool = True) -> int:
        """
        Adds all files from a directory to staged files.

        Args:
            dir_name: Path to the directory to add
            recursive: Whether to recursively add subdirectories (default is True)

        Returns:
            The number of files added
        """
        dir_path = Path(dir_name)
        # Handle absolute paths by making them relative to base_dir
        relative_dir = str(dir_path.relative_to(self.base_dir) if dir_path.is_absolute()
                        else dir_path)
        absolute_dir_path = self.base_dir / relative_dir

        if not absolute_dir_path.exists():
            print(f"Error: Directory '{dir_name}' does not exist.")
            return 0

        if not absolute_dir_path.is_dir():
            print(f"Error: '{dir_name}' is not a directory.")
            return 0

        # Get non-ignored files from the directory
        try:
            all_files = self.ignore_handler.filter_paths(
                str(absolute_dir_path), recursive=recursive
            )
        except OSError as e:
            print(f"Error scanning directory '{dir_name}': {e}")
            return 0

        if not all_files:
            print(f"No files found in directory '{dir_name}'.")
            return 0

        # Convert string paths to Path objects and filter files (exclude directories)
        file_paths = [Path(f) for f in all_files if Path(f).is_file()]

        if not file_paths:
            print(
                f"No files found in directory '{dir_name}' (only directories)."
            )
            return 0

        # Collect all new files first
        new_files = []
        for file_path in file_paths:
            relative_path = str(file_path.relative_to(self.base_dir) if file_path.is_absolute()
                             else file_path.relative_to(absolute_dir_path.parent))
            if relative_path not in self.files:
                new_files.append(relative_path)

        # Add new files to the list
        added_count = self._add_files_to_list(new_files)
        total_files = len(file_paths)
        skipped_count = total_files - added_count

        if skipped_count > 0:
            print(
                f"Added {added_count} files from directory '{dir_name}' (skipped {skipped_count} already staged files)."
            )
        else:
            print(f"Added {added_count} files from directory '{dir_name}'.")

        return added_count

    def add_directory_parallel(self, dir_name: Union[str, Path], recursive: bool = True) -> int:
        """
        Adds all files from a directory to staged files using parallel processing.

        Args:
            dir_name: Path to the directory to add
            recursive: Whether to recursively add subdirectories (default is True)

        Returns:
            The number of files added
        """
        dir_path = Path(dir_name)
        # Handle absolute paths by making them relative to base_dir
        relative_dir = str(dir_path.relative_to(self.base_dir) if dir_path.is_absolute()
                        else dir_path)
        absolute_dir_path = self.base_dir / relative_dir

        if not absolute_dir_path.exists():
            print(f"Error: Directory '{dir_name}' does not exist.")
            return 0

        if not absolute_dir_path.is_dir():
            print(f"Error: '{dir_name}' is not a directory.")
            return 0

        # Get non-ignored files from the directory
        try:
            all_files = self.ignore_handler.filter_paths(
                str(absolute_dir_path), recursive=recursive
            )
        except OSError as e:
            print(f"Error scanning directory '{dir_name}': {e}")
            return 0

        if not all_files:
            print(f"No files found in directory '{dir_name}'.")
            return 0

        # Convert string paths to Path objects and filter files (exclude directories)
        file_paths = [Path(f) for f in all_files if Path(f).is_file()]

        if not file_paths:
            print(
                f"No files found in directory '{dir_name}' (only directories)."
            )
            return 0

        # Get current file list for comparison
        current_files: Set[str] = set(self.files)
        added_files = []

        # Process files in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # Create a dictionary to map futures to file paths
            future_to_path = {
                executor.submit(self._process_file, file_path): file_path
                for file_path in file_paths
            }

            # Process futures as they complete
            for future in concurrent.futures.as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    relative_path = future.result()
                    if relative_path and relative_path not in current_files:
                        added_files.append(relative_path)
                except Exception as e:
                    logging.error(f"Error processing file {file_path}: {e}")

        # Add new files to the list
        added_count = self._add_files_to_list(added_files)
        total_files = len(file_paths)
        skipped_count = total_files - added_count

        if skipped_count > 0:
            print(
                f"Added {added_count} files from directory '{dir_name}' (skipped {skipped_count} already staged files)."
            )
        else:
            print(f"Added {added_count} files from directory '{dir_name}'.")

        return added_count

    def _process_file(self, file_path: Path) -> Optional[str]:
        """
        Process a single file for parallel directory scanning.

        Args:
            file_path: Path to the file to process

        Returns:
            The relative path (as string) if the file should be added, None otherwise
        """
        try:
            relative_path = str(file_path.relative_to(self.base_dir) if file_path.is_absolute()
                             else file_path)

            # Check if the file should be ignored
            if self.ignore_handler.is_ignored(relative_path):
                return None

            return relative_path
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")
            return None

    def _add_files_to_list(self, files_to_add: List[str]) -> int:
        """
        Helper method to add multiple files to the staged files list.

        Args:
            files_to_add: List of relative file paths to add

        Returns:
            Number of files added
        """
        if not files_to_add:
            return 0

        # Using the batch update feature of ObservableList if available
        if hasattr(self.files, "begin_batch_update"):
            self.files.begin_batch_update()
            for file_path in files_to_add:
                self.files.append(file_path)
            self.files.end_batch_update()
        else:
            # If batch update not available, add files one by one
            for file_path in files_to_add:
                self.files.append(file_path)

        return len(files_to_add)

    def remove_file(self, file_name: Union[str, Path]) -> bool:
        """
        Removes a file from the staged list.

        Args:
            file_name: Path to the file to remove

        Returns:
            True if the file was removed, False otherwise
        """
        file_path = Path(file_name)
        relative_path = str(file_path.relative_to(self.base_dir) if file_path.is_absolute()
                         else file_path)

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