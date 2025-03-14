"""
Views for the backtick tool.

This module provides terminal interface classes for the backtick tool.
"""

from contextlib import contextmanager
from typing import List, Optional, Callable

from swallow_framework import View, Context
from backtick.models import StagedFiles


class TerminalView(View):
    """Represents the user interface for the staged files app."""

    def __init__(self, context: Context, model: StagedFiles):
        """
        Initialize the TerminalView and auto-watches the model.

        Args:
            context: The application context
            model: The StagedFiles model to watch
        """
        super().__init__(context)  # Make sure to call parent constructor
        self.model = model

        # Watch for changes to the files property using the cleaner API
        self.model.files.on_change(self.update)

        # Initial update
        self.update(model.files)

    def show_help(self) -> None:
        """Displays the help menu with available commands."""
        with self.print_message():
            print("Backtick - Collect file contents for the clipboard\n")
            print("Commands:")
            print("  <file_path>         Add a file to the staged list")
            print("  <directory_path>    Add all files in a directory")
            print("  <glob_pattern>      Add files matching a glob pattern (e.g., *.py)")
            print("  l                   List all staged files")
            print("  r <index>           Remove a file by index")
            print("  c                   Clear all staged files")
            print("  h                   Show this help message")
            print("  q                   Quit the program")
            print("  `                   Copy all staged files to clipboard and quit")

    def update(self, files: list) -> None:
        """
        Updates the view when the model changes.

        Args:
            files: The updated list of files
        """
        self.list_files(files)

    def list_files(self, files: list) -> None:
        """
        Displays the list of staged files.

        Args:
            files: The list of files to display
        """
        with self.print_message():
            if not files:
                print("No files are staged.")
            else:
                print(f"\nStaged Files ({len(files)} total):")
                for i, file in enumerate(files, 1):
                    print(f"{i}. {file}")

    def show_error(self, message: str) -> None:
        """
        Display an error message.

        Args:
            message: The error message to display
        """
        with self.print_message():
            print(f"Error: {message}")

    def show_info(self, message: str) -> None:
        """
        Display an informational message.

        Args:
            message: The informational message to display
        """
        with self.print_message():
            print(message)

    def show_confirmation(self, message: str, default: bool = False) -> bool:
        """
        Ask for user confirmation.

        Args:
            message: The confirmation message to display
            default: The default response if the user just presses Enter

        Returns:
            True if the user confirmed, False otherwise
        """
        default_str = "Y/n" if default else "y/N"
        response = input(f"{message} [{default_str}]: ").strip().lower()

        if not response:
            return default

        return response.startswith('y')

    @contextmanager
    def print_message(self) -> None:
        """Context manager for printing messages with consistent formatting."""
        yield
        print()  # Add a newline after each message block