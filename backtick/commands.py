import os
from typing import Any, Dict

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
    """Command to add all files in a directory recursively to the staged files."""

    def __init__(self, model: StagedFiles):
        super().__init__(model)

    def execute(self, data: str) -> None:
        self.model.add_directory(data)


class RemoveCommand(Command):
    """Command to remove an entry from the list of staged files (can be a directory)."""

    def __init__(self, model: StagedFiles):
        super().__init__(model)

    def execute(self, data: str) -> None:
        try:
            # Try to interpret data as an index
            index = int(data) - 1
            if 0 <= index < len(self.model.files):
                file_to_remove = self.model.files[index]
                self.model.remove_file(file_to_remove)
            else:
                print(f"Error: Index '{data}' is out of range.")
        except ValueError:
            # If data is not an index, treat it as a file path
            self.model.remove_file(data)


class ClearFilesCommand(Command):
    """Command to clear all staged files."""

    def __init__(self, model: StagedFiles):
        super().__init__(model)

    def execute(self, data: Any = None) -> None:
        self.model.clear_files()


class CopyToClipboardCommand(Command):
    """Command to copy all staged file contents to clipboard."""

    def __init__(self, model: StagedFiles):
        super().__init__(model)
        self.formatter = ClipboardFormatter()  # Create an instance of the formatter

    def execute(self, data: Any = None) -> None:
        files = self.model.files
        if not files:
            print("No files are currently staged.")
            return

        # Format files for clipboard using the instance
        combined_content = self.formatter.format_files(files)

        # Copy to clipboard
        pyperclip.copy(combined_content)
        print(f"Copied {len(files)} file(s) to clipboard.")

