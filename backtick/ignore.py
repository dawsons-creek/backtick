"""
Ignore handling functionality for the backtick tool.

This module provides classes for handling gitignore-style file filtering.
"""

import os
from typing import Iterable, List, Optional, Tuple, Set

import pathspec
from prompt_toolkit.completion import PathCompleter, Completion


class IgnoreHelper:
    """
    A class that implements gitignore-style file filtering using pathspec.

    This class parses gitignore pattern files and can determine whether a file
    or directory should be ignored based on those patterns.
    """

    def __init__(self, ignore_file_path: Optional[str] = None, ignore_content: Optional[str] = None):
        """
        Initialize the IgnoreHelper with patterns from a file or string content.

        Args:
            ignore_file_path: Path to a gitignore file to parse
            ignore_content: String content containing gitignore patterns
        """
        self.patterns = []

        if ignore_file_path and os.path.isfile(ignore_file_path):
            with open(ignore_file_path, "r") as f:
                self.spec = pathspec.PathSpec.from_lines(
                    pathspec.patterns.GitWildMatchPattern, f.readlines()
                )
        elif ignore_content:
            self.spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern, ignore_content.splitlines()
            )
        else:
            # Empty spec if no patterns
            self.spec = pathspec.PathSpec([])

    def is_ignored(self, file_path: str, is_dir: bool = False, base_dir: str = '.') -> bool:
        """
        Check if a file or directory should be ignored.

        Args:
            file_path: Path to the file or directory to check
            is_dir: Whether the path is a directory
            base_dir: Base directory to resolve relative paths from

        Returns:
            True if the file or directory should be ignored, False otherwise
        """
        # Normalize the path (convert to relative path if absolute)
        rel_path = os.path.relpath(file_path, base_dir)

        # Check if the path matches any ignore patterns
        return self.spec.match_file(rel_path)

    def filter_paths(self, root_dir: str, recursive: bool = True) -> List[str]:
        """
        Filter a directory, returning paths that are not ignored.

        Args:
            root_dir: Root directory to start filtering from
            recursive: Whether to recursively filter subdirectories

        Returns:
            List of paths that are not ignored
        """
        result = []
        root_dir = os.path.abspath(root_dir)

        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Remove ignored directories from dirnames to prevent recursion into them
            if not recursive:
                dirnames.clear()

            # Remove directories that should be ignored
            i = 0
            while i < len(dirnames):
                dir_path = os.path.join(dirpath, dirnames[i])
                if self.is_ignored(dir_path, True, root_dir):
                    dirnames.pop(i)
                else:
                    if recursive:  # Only add directories to result if recursive
                        result.append(dir_path)
                    i += 1

            # Add non-ignored files
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if not self.is_ignored(file_path, False, root_dir):
                    result.append(file_path)

        return result

    @classmethod
    def from_file(cls, ignore_file_path: str) -> 'IgnoreHelper':
        """
        Create an IgnoreHelper from a gitignore file.

        Args:
            ignore_file_path: Path to a gitignore file

        Returns:
            A new IgnoreHelper instance
        """
        return cls(ignore_file_path=ignore_file_path)

    @classmethod
    def from_content(cls, content: str) -> 'IgnoreHelper':
        """
        Create an IgnoreHelper from a string containing gitignore patterns.

        Args:
            content: String containing gitignore patterns

        Returns:
            A new IgnoreHelper instance
        """
        return cls(ignore_content=content)


# For backward compatibility
IgnoreHandler = IgnoreHelper


class IgnoreAwarePathCompleter(PathCompleter):
    """
    Path completer that respects gitignore rules.

    This class extends the prompt_toolkit PathCompleter to filter out paths that
    should be ignored according to gitignore patterns.
    """

    def __init__(
            self,
            only_directories: bool = False,
            expanduser: bool = False,
            file_filter: Optional[callable] = None,
            min_input_len: int = 0,
            ignore_file_path: str = ".backtickignore"
    ):
        """
        Initialize the IgnoreAwarePathCompleter.

        Args:
            only_directories: Only show directories in completion.
            expanduser: Expand the '~' character to the user's home directory.
            file_filter: Optional callable that takes a filename and returns
                         whether to include it in the completions.
            min_input_len: Minimum input length before offering completions.
            ignore_file_path: Path to the ignore file (default is ".backtickignore").
        """
        super().__init__(
            only_directories=only_directories,
            expanduser=expanduser,
            file_filter=file_filter,
            min_input_len=min_input_len
        )

        # Initialize the IgnoreHelper
        if os.path.exists(ignore_file_path):
            self.ignore_handler = IgnoreHelper.from_file(ignore_file_path)
        else:
            # Create an empty ignore handler if no file exists
            self.ignore_handler = IgnoreHelper.from_content("")

    def get_completions(
            self, document, complete_event
    ) -> Iterable[Completion]:
        """
        Get completions for the given document.
        Filter out paths that should be ignored according to gitignore patterns.

        Args:
            document: The Document instance for completion.
            complete_event: The complete_event that triggered this completion.

        Returns:
            An iterable of Completion instances.
        """
        # Get all completions from the parent class
        completions = list(super().get_completions(document, complete_event))

        # Filter out ignored paths
        filtered_completions = []
        for completion in completions:
            path = completion.text

            # Determine if this is a directory
            is_dir = path.endswith(os.sep)
            full_path = os.path.normpath(path)

            # Check if the path should be ignored
            if not self.ignore_handler.is_ignored(full_path, is_dir):
                filtered_completions.append(completion)

        return filtered_completions