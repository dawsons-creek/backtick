import os
import re
import fnmatch
from pathlib import Path
from typing import List, Set, Optional, Tuple


class IgnoreHelper:
    """
    A class that implements gitignore-style file filtering.

    This class parses gitignore pattern files and can determine whether a file
    or directory should be ignored based on those patterns.
    """

    def __init__(self, ignore_file_path: Optional[str] = None, ignore_content: Optional[str] = None):
        """
        Initialize the GitIgnoreHelper with patterns from a file or string content.

        Args:
            ignore_file_path: Path to a gitignore file to parse
            ignore_content: String content containing gitignore patterns
        """
        self.include_patterns: List[str] = []
        self.exclude_patterns: List[str] = []

        if ignore_file_path and os.path.isfile(ignore_file_path):
            with open(ignore_file_path, 'r') as f:
                self._parse_patterns(f.read())
        elif ignore_content:
            self._parse_patterns(ignore_content)

    def _parse_patterns(self, content: str) -> None:
        """
        Parse gitignore patterns from content string.

        Args:
            content: String containing gitignore patterns
        """
        for line in content.splitlines():
            # Skip blank lines and comments
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue

            # Handle negation
            if line.startswith('!'):
                self.include_patterns.append(self._convert_pattern_to_regex(line[1:]))
            else:
                self.exclude_patterns.append(self._convert_pattern_to_regex(line))

    def _convert_pattern_to_regex(self, pattern: str) -> str:
        """
        Convert a gitignore pattern to a regex pattern.

        Args:
            pattern: A gitignore pattern

        Returns:
            A regular expression pattern string
        """
        # Remove trailing spaces unless escaped with backslash
        pattern = re.sub(r'(?<!\\)\\s+$', '', pattern)

        # Handle patterns with escaped leading characters (like \# or \!)
        if pattern.startswith('\\'):
            pattern = pattern[1:]

        # Flag to check if the pattern matches only directories
        dir_only = pattern.endswith('/')
        if dir_only:
            pattern = pattern[:-1]

        # Create a regex pattern based on gitignore rules
        regex = ''

        # Check if pattern starts with slash, meaning it matches only in the current directory
        if pattern.startswith('/'):
            regex += '^'
            pattern = pattern[1:]
        # If it contains a slash but doesn't start with one, it still anchors to the current directory
        elif '/' in pattern:
            regex += '(?:^|/)'
        # Otherwise, it can match anywhere in the path
        else:
            regex += '(?:^|/)'

        # Handle the pattern parts
        i = 0
        while i < len(pattern):
            c = pattern[i]

            # Handle special characters
            if c == '*':
                # Handle ** pattern (matches across directories)
                if i + 1 < len(pattern) and pattern[i + 1] == '*':
                    if (i + 2 < len(pattern) and pattern[i + 2] == '/'):
                        # **/ matches zero or more directories
                        regex += '(?:.*/)?'
                        i += 3
                    elif i == 0 and i + 2 == len(pattern):
                        # ** matches everything
                        regex += '.*'
                        i += 2
                    else:
                        # Regular * character
                        regex += '[^/]*'
                        i += 1
                else:
                    # Single * matches anything except /
                    regex += '[^/]*'
                    i += 1
            elif c == '?':
                # ? matches any character except /
                regex += '[^/]'
                i += 1
            elif c == '[':
                # Character class
                end = pattern.find(']', i)
                if end == -1:
                    regex += '\\['
                    i += 1
                else:
                    # Include the character class as is (fnmatch style)
                    charclass = pattern[i:end + 1]
                    regex += charclass
                    i = end + 1
            elif c == '/':
                # Directory separator
                regex += '/'
                i += 1
            else:
                # Escape regex special characters
                if c in '.^$+(){}|':
                    regex += '\\'
                regex += c
                i += 1

        # If pattern doesn't end with /, it can match both files and directories
        if not pattern.endswith('/'):
            if dir_only:
                regex += '/$'
            else:
                regex += '(?:$|/)'
        else:
            regex += '$'

        return regex

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
        if rel_path == '.':
            rel_path = ''

        # Convert backslashes to forward slashes for consistency
        rel_path = rel_path.replace('\\', '/')
        if is_dir and not rel_path.endswith('/'):
            rel_path += '/'

        # Check patterns in order with negations
        ignored = False

        # First check exclusion patterns
        for pattern in self.exclude_patterns:
            if re.search(pattern, rel_path):
                ignored = True
                break

        # If ignored, check if it's re-included by a negation pattern
        if ignored:
            for pattern in self.include_patterns:
                if re.search(pattern, rel_path):
                    # Can't re-include if parent directory is excluded
                    parent_dir = os.path.dirname(rel_path)
                    if parent_dir and self.is_ignored(parent_dir, True, base_dir):
                        return True
                    return False

        return ignored

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
        Create a GitIgnoreHelper from a gitignore file.

        Args:
            ignore_file_path: Path to a gitignore file

        Returns:
            A new GitIgnoreHelper instance
        """
        return cls(ignore_file_path=ignore_file_path)

    @classmethod
    def from_content(cls, content: str) -> 'IgnoreHelper':
        """
        Create a GitIgnoreHelper from a string containing gitignore patterns.

        Args:
            content: String containing gitignore patterns

        Returns:
            A new GitIgnoreHelper instance
        """
        return cls(ignore_content=content)


# Example usage
if __name__ == "__main__":
    # Create a gitignore helper from a file
    ignore_helper = IgnoreHelper.from_file(".gitignore")

    # Or create from a string with patterns
    patterns = """
    # Ignore all log files
    *.log
    # Ignore build directory
    /build/
    # But include special log files
    !important.log
    """
    ignore_helper = IgnoreHelper.from_content(patterns)

    # Check if a file should be ignored
    print(ignore_helper.is_ignored("test.log"))  # True
    print(ignore_helper.is_ignored("build/output.txt"))  # True
    print(ignore_helper.is_ignored("important.log"))  # False

    # Get all non-ignored files in a directory
    files = ignore_helper.filter_paths("./my_project")
    for file in files:
        print(file)