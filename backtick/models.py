import os
from swallow_framework import Model, state
from backtick.ignore import IgnoreHelper


class StagedFiles(Model):
    """Manages the list of staged files with automatic state observation."""

    files = state([])  # Reactive property using `state`

    def __init__(self, ignore_file_path=".backtickignore"):
        super().__init__()
        self.base_dir = os.getcwd()

        # Replace the old IgnoreHandler with our new IgnoreHelper
        if os.path.exists(ignore_file_path):
            self.ignore_handler = IgnoreHelper.from_file(ignore_file_path)
        else:
            # Create an empty ignore handler if no file exists
            self.ignore_handler = IgnoreHelper.from_content("")

    def add_file(self, file_name: str):
        """Adds a file to the staged files list."""
        relative_path = os.path.relpath(file_name, self.base_dir)

        # Use the new is_ignored method instead of should_ignore
        if self.ignore_handler.is_ignored(relative_path):
            print(f"Skipping ignored file: {relative_path}")
            return

        if relative_path not in self.files:
            self.files.append(relative_path)  # Auto-notifies watchers
            print(f"Added {file_name} to staged files.")

    def add_directory(self, dir_name: str):
        """Adds all files from a directory to staged files."""
        dir_path = os.path.relpath(dir_name, self.base_dir)
        absolute_dir_path = os.path.join(self.base_dir, dir_path)

        if not os.path.exists(absolute_dir_path):
            print(f"Error: Directory '{dir_name}' does not exist.")
            return

        if not os.path.isdir(absolute_dir_path):
            print(f"Error: '{dir_name}' is not a directory.")
            return

        # Use the filter_paths method from IgnoreHelper to get non-ignored files
        all_files = self.ignore_handler.filter_paths(absolute_dir_path)

        if not all_files:
            print(f"No files found in directory '{dir_name}'.")
            return

        # Filter files (exclude directories)
        file_paths = [f for f in all_files if os.path.isfile(f)]

        if not file_paths:
            print(f"No files found in directory '{dir_name}' (only directories).")
            return

        added_count = 0
        new_files = []

        # Collect all new files first
        for file_path in file_paths:
            relative_path = os.path.relpath(file_path, self.base_dir)
            if relative_path not in self.files:
                new_files.append(relative_path)
                added_count += 1

        # Using the batch update feature of ObservableList
        if hasattr(self.files, 'begin_batch_update'):
            self.files.begin_batch_update()
            for file_path in new_files:
                self.files.append(file_path)
            self.files.end_batch_update()
        else:
            # If batch update not available, add files one by one
            for file_path in new_files:
                self.files.append(file_path)

        total_files = len(file_paths)
        skipped_count = total_files - added_count

        if skipped_count > 0:
            print(f"Added {added_count} files from directory '{dir_name}' (skipped {skipped_count} already staged files).")
        else:
            print(f"Added {added_count} files from directory '{dir_name}'.")

    def remove_file(self, file_name: str):
        """Removes a file from the staged list."""
        relative_path = os.path.relpath(file_name, self.base_dir)

        if relative_path in self.files:
            self.files.remove(relative_path)  # Auto-notifies watchers
            print(f"File removed: {relative_path}")
        else:
            print(f"File not found: {relative_path}")

    def clear_files(self):
        """Clears all staged files."""
        self.files.clear()
        print("Cleared all staged files.")