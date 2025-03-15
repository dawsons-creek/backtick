"""
Tests for the StagedFiles model in backtick/models.py.
"""

import os
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, MagicMock

from backtick.models import StagedFiles
from backtick.ignore import IgnoreHelper


@pytest.fixture
def mock_ignore_helper():
    """Fixture that returns a mocked IgnoreHelper."""
    mock = Mock(spec=IgnoreHelper)
    mock.is_ignored.return_value = False
    mock.filter_paths.return_value = []
    return mock


@pytest.fixture
def staged_files(monkeypatch, mock_ignore_helper):
    """Fixture that returns a StagedFiles instance with mocked dependencies."""
    # Mock the Path.exists call to pretend the ignore file exists
    monkeypatch.setattr(Path, "exists", lambda self: True)

    # Mock the IgnoreHelper.from_file to return our mock
    monkeypatch.setattr(IgnoreHelper, "from_file", lambda path: mock_ignore_helper)

    # Create the StagedFiles instance
    model = StagedFiles(ignore_file_path=".backtickignore")

    # Mock the base directory
    model.base_dir = Path("/mock/base/dir")

    return model


class TestStagedFiles:
    """Tests for the StagedFiles class."""

    def test_init_with_ignore_file(self, monkeypatch):
        """Test initialization with an existing ignore file."""
        # Mock IgnoreHelper.from_file
        mock_from_file = Mock(return_value=Mock(spec=IgnoreHelper))
        monkeypatch.setattr(IgnoreHelper, "from_file", mock_from_file)

        # Mock Path.exists to return True
        monkeypatch.setattr(Path, "exists", lambda self: True)

        # Create StagedFiles
        model = StagedFiles(ignore_file_path="test_ignore_file")

        # Verify IgnoreHelper.from_file was called
        mock_from_file.assert_called_once_with("test_ignore_file")

        # Verify initial state
        assert len(model.files) == 0  # Check that the list is empty
        assert model.max_workers == 4  # Default value

    def test_init_without_ignore_file(self, monkeypatch):
        """Test initialization when ignore file doesn't exist."""
        # Mock IgnoreHelper.from_content
        mock_from_content = Mock(return_value=Mock(spec=IgnoreHelper))
        monkeypatch.setattr(IgnoreHelper, "from_content", mock_from_content)

        # Mock Path.exists to return False
        monkeypatch.setattr(Path, "exists", lambda self: False)

        # Create StagedFiles
        model = StagedFiles(ignore_file_path="nonexistent_file")

        # Verify IgnoreHelper.from_content was called with empty string
        mock_from_content.assert_called_once_with("")

    def test_add_file_success(self, staged_files, monkeypatch):
        """Test adding a file successfully."""
        # Setup
        file_path = Path("/mock/base/dir/test_file.py")
        relative_path = "test_file.py"

        # Mock Path.exists and relative_to
        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)
        monkeypatch.setattr(Path, "relative_to", lambda self, base: Path(relative_path))

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            result = staged_files.add_file(file_path)

            # Verify
            assert result is True
            assert relative_path in staged_files.files
            mock_print.assert_called_once_with(f"Added {file_path} to staged files.")

    def test_add_file_nonexistent(self, staged_files, monkeypatch):
        """Test adding a file that doesn't exist."""
        # Setup
        file_path = Path("/mock/base/dir/nonexistent.py")

        # Mock Path.exists to return False
        monkeypatch.setattr(Path, "exists", lambda self: False)

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            result = staged_files.add_file(file_path)

            # Verify
            assert result is False
            assert len(staged_files.files) == 0
            mock_print.assert_called_once_with(f"Error: File '{file_path}' does not exist.")

    def test_add_file_ignored(self, staged_files, monkeypatch):
        """Test adding a file that should be ignored."""
        # Setup
        file_path = Path("/mock/base/dir/ignored_file.py")
        relative_path = "ignored_file.py"

        # Mock Path methods
        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)
        monkeypatch.setattr(Path, "relative_to", lambda self, base: Path(relative_path))

        # Configure mock to ignore this file
        staged_files.ignore_handler.is_ignored.return_value = True

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            result = staged_files.add_file(file_path)

            # Verify
            assert result is False
            assert len(staged_files.files) == 0
            mock_print.assert_called_once_with(f"Skipping ignored file: {relative_path}")

    def test_add_file_duplicate(self, staged_files, monkeypatch):
        """Test adding a file that's already staged."""
        # Setup
        file_path = Path("/mock/base/dir/duplicate.py")
        relative_path = "duplicate.py"

        # Mock Path methods
        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)
        monkeypatch.setattr(Path, "relative_to", lambda self, base: Path(relative_path))

        # Add the file first
        staged_files.files.append(relative_path)

        # Execute
        result = staged_files.add_file(file_path)

        # Verify
        assert result is False  # Should return False for duplicate
        assert staged_files.files.count(relative_path) == 1  # Should not add duplicate

    def test_add_directory(self, staged_files, monkeypatch):
        """Test adding files from a directory."""
        # Setup
        dir_path = Path("/mock/base/dir/test_dir")

        # Mock file paths that will be returned by filter_paths
        file_paths = [
            "/mock/base/dir/test_dir/file1.py",
            "/mock/base/dir/test_dir/file2.py",
            "/mock/base/dir/test_dir/subdir/file3.py"
        ]

        # Mock Path methods
        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(Path, "is_dir", lambda self: True)
        monkeypatch.setattr(Path, "is_file", lambda self: True)
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)

        # Mock relative_to to simulate path relationships
        def mock_relative_to(self, base):
            if str(self).startswith(str(base)):
                return Path(str(self).replace(str(base) + "/", ""))
            return self

        monkeypatch.setattr(Path, "relative_to", mock_relative_to)

        # Configure mock to return our file paths
        staged_files.ignore_handler.filter_paths.return_value = file_paths

        # Mock the _add_files_to_list method to track calls and return value
        with patch.object(staged_files, '_add_files_to_list', return_value=3) as mock_add_files:
            # Mock print to avoid console output during tests
            with patch("builtins.print"):
                # Execute
                result = staged_files.add_directory(dir_path)

                # Verify
                assert result == 3  # Should return the number of files added
                # Check that _add_files_to_list was called (we're not testing its internals here)
                mock_add_files.assert_called_once()
                # Check that it was called with a list of the expected length
                assert len(mock_add_files.call_args[0][0]) == 3

    def test_add_directory_nonexistent(self, staged_files, monkeypatch):
        """Test adding a directory that doesn't exist."""
        # Setup
        dir_path = Path("/mock/base/dir/nonexistent_dir")

        # Mock Path.exists to return False
        monkeypatch.setattr(Path, "exists", lambda self: False)

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            result = staged_files.add_directory(dir_path)

            # Verify
            assert result == 0
            assert len(staged_files.files) == 0
            mock_print.assert_called_once_with(f"Error: Directory '{dir_path}' does not exist.")

    def test_add_directory_not_dir(self, staged_files, monkeypatch):
        """Test adding a path that exists but is not a directory."""
        # Setup
        path = Path("/mock/base/dir/not_a_dir")

        # Mock Path methods
        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(Path, "is_dir", lambda self: False)

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            result = staged_files.add_directory(path)

            # Verify
            assert result == 0
            assert len(staged_files.files) == 0
            mock_print.assert_called_once_with(f"Error: '{path}' is not a directory.")

    def test_add_directory_parallel(self, staged_files, monkeypatch):
        """Test adding files from a directory using parallel processing."""
        # Setup
        dir_path = Path("/mock/base/dir/test_dir")
        file_paths = [
            "/mock/base/dir/test_dir/file1.py",
            "/mock/base/dir/test_dir/file2.py"
        ]

        # Mock Path methods
        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(Path, "is_dir", lambda self: True)
        monkeypatch.setattr(Path, "is_file", lambda self: True)
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)

        # Mock relative_to to simulate path relationships
        def mock_relative_to(self, base):
            if str(self).startswith(str(base)):
                return Path(str(self).replace(str(base) + "/", ""))
            return self

        monkeypatch.setattr(Path, "relative_to", mock_relative_to)

        # Configure mock to return our file paths
        staged_files.ignore_handler.filter_paths.return_value = file_paths

        # Mock ThreadPoolExecutor
        mock_executor = MagicMock()
        future1 = Mock()
        future1.result.return_value = "test_dir/file1.py"
        future2 = Mock()
        future2.result.return_value = "test_dir/file2.py"

        # Setup the mock executor to return our futures
        mock_executor.__enter__.return_value.submit.side_effect = [future1, future2]

        # Mock concurrent.futures.as_completed to yield our "futures"
        def mock_as_completed(futures):
            for future in futures:
                yield future

        # Mock the _add_files_to_list method
        with patch.object(staged_files, '_add_files_to_list', return_value=2) as mock_add_files, \
                patch("concurrent.futures.ThreadPoolExecutor", return_value=mock_executor), \
                patch("concurrent.futures.as_completed", mock_as_completed), \
                patch("builtins.print"):

            # Execute
            result = staged_files.add_directory_parallel(dir_path)

            # Verify
            assert result == 2
            # Check that _add_files_to_list was called with the correct number of files
            mock_add_files.assert_called_once()
            assert len(mock_add_files.call_args[0][0]) == 2

    def test_process_file(self, staged_files, monkeypatch):
        """Test _process_file method."""
        # Setup
        file_path = Path("/mock/base/dir/test_file.py")
        expected_relative_path = "test_file.py"

        # Mock Path methods
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)
        monkeypatch.setattr(Path, "relative_to", lambda self, base: Path(expected_relative_path))

        # Execute
        result = staged_files._process_file(file_path)

        # Verify
        assert result == expected_relative_path
        staged_files.ignore_handler.is_ignored.assert_called_once_with(expected_relative_path)

    def test_process_file_ignored(self, staged_files, monkeypatch):
        """Test _process_file method with ignored file."""
        # Setup
        file_path = Path("/mock/base/dir/ignored_file.py")
        expected_relative_path = "ignored_file.py"

        # Mock Path methods
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)
        monkeypatch.setattr(Path, "relative_to", lambda self, base: Path(expected_relative_path))

        # Configure mock to ignore this file
        staged_files.ignore_handler.is_ignored.return_value = True

        # Execute
        result = staged_files._process_file(file_path)

        # Verify
        assert result is None
        staged_files.ignore_handler.is_ignored.assert_called_once_with(expected_relative_path)

    def test_add_files_to_list_empty(self, staged_files):
        """Test _add_files_to_list with empty list."""
        # Execute
        result = staged_files._add_files_to_list([])

        # Verify
        assert result == 0
        # Files list should remain unchanged
        assert len(staged_files.files) == 0

    def test_add_files_to_list_without_batch(self, staged_files):
        # Mock the methods to prevent any real logic from running
        staged_files.files.begin_batch_update = MagicMock(return_value=None)  # No-op mock
        staged_files.files.end_batch_update = MagicMock(return_value=None)  # No-op mock

        # Add files to the list without the batch update
        files_to_add = ["file1.txt", "file2.txt", "file3.txt"]
        for file in files_to_add:
            staged_files.add_file(file)

        # Assert that all files were added to the list
        assert all(file in staged_files.files for file in files_to_add)

        # Ensure begin_batch_update and end_batch_update were NOT called
        staged_files.files.begin_batch_update.assert_not_called()
        staged_files.files.end_batch_update.assert_not_called()

    def test_add_files_to_list_with_batch(self, staged_files):
        """Test _add_files_to_list with batch update capability."""
        # Setup - add batch update methods
        files_to_add = ["file1.py", "file2.py"]

        # Add batch update methods to the files list
        staged_files.files.begin_batch_update = Mock()
        staged_files.files.end_batch_update = Mock()

        # Execute
        result = staged_files._add_files_to_list(files_to_add)

        # Verify
        assert result == 2
        assert "file1.py" in staged_files.files
        assert "file2.py" in staged_files.files
        assert len(staged_files.files) == 2
        # Verify batch methods were called
        staged_files.files.begin_batch_update.assert_called_once()
        staged_files.files.end_batch_update.assert_called_once()

    def test_remove_file(self, staged_files, monkeypatch):
        """Test removing a file from the staged list."""
        # Setup
        file_path = Path("/mock/base/dir/test_file.py")
        relative_path = "test_file.py"

        # Add the file first
        staged_files.files.append(relative_path)

        # Mock Path methods
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)
        monkeypatch.setattr(Path, "relative_to", lambda self, base: Path(relative_path))

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            result = staged_files.remove_file(file_path)

            # Verify
            assert result is True
            assert relative_path not in staged_files.files
            mock_print.assert_called_once_with(f"File removed: {relative_path}")

    def test_remove_nonexistent_file(self, staged_files, monkeypatch):
        """Test removing a file that isn't in the staged list."""
        # Setup
        file_path = Path("/mock/base/dir/nonexistent.py")
        relative_path = "nonexistent.py"

        # Mock Path methods
        monkeypatch.setattr(Path, "is_absolute", lambda self: True)
        monkeypatch.setattr(Path, "relative_to", lambda self, base: Path(relative_path))

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            result = staged_files.remove_file(file_path)

            # Verify
            assert result is False
            mock_print.assert_called_once_with(f"File not found: {relative_path}")

    def test_clear_files(self, staged_files):
        """Test clearing all staged files."""
        # Setup
        staged_files.files = ["file1.py", "file2.py"]

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            staged_files.clear_files()

            # Verify
            assert len(staged_files.files) == 0
            mock_print.assert_called_once_with("Cleared all staged files.")

    def test_get_file_count(self, staged_files):
        """Test getting the count of staged files."""
        # Setup
        staged_files.files = ["file1.py", "file2.py", "file3.py"]

        # Execute
        count = staged_files.get_file_count()

        # Verify
        assert count == 3
