"""
Tests for the StagedFiles model in backtick/models.py.
"""

import os
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
    # Mock the os.path.exists call to pretend the ignore file exists
    monkeypatch.setattr(os.path, "exists", lambda path: True)

    # Mock the IgnoreHelper.from_file to return our mock
    monkeypatch.setattr(IgnoreHelper, "from_file", lambda path: mock_ignore_helper)

    # Create the StagedFiles instance
    model = StagedFiles(ignore_file_path=".backtickignore")

    # Mock the base directory
    model.base_dir = "/mock/base/dir"

    return model


class TestStagedFiles:
    """Tests for the StagedFiles class."""

    def test_init_with_ignore_file(self, monkeypatch):
        """Test initialization with an existing ignore file."""
        # Mock IgnoreHelper.from_file
        mock_from_file = Mock(return_value=Mock(spec=IgnoreHelper))
        monkeypatch.setattr(IgnoreHelper, "from_file", mock_from_file)

        # Mock os.path.exists to return True
        monkeypatch.setattr(os.path, "exists", lambda path: True)

        # Create StagedFiles
        model = StagedFiles(ignore_file_path="test_ignore_file")

        # Verify IgnoreHelper.from_file was called
        mock_from_file.assert_called_once_with("test_ignore_file")

        # Verify initial state
        assert len(model.files) == 0  # Check that the list is empty instead of comparing types
        # Alternative: assert list(model.files) == []
        assert model.max_workers == 4  # Default value

    def test_init_without_ignore_file(self, monkeypatch):
        """Test initialization when ignore file doesn't exist."""
        # Mock IgnoreHelper.from_content
        mock_from_content = Mock(return_value=Mock(spec=IgnoreHelper))
        monkeypatch.setattr(IgnoreHelper, "from_content", mock_from_content)

        # Mock os.path.exists to return False
        monkeypatch.setattr(os.path, "exists", lambda path: False)

        # Create StagedFiles
        model = StagedFiles(ignore_file_path="nonexistent_file")

        # Verify IgnoreHelper.from_content was called with empty string
        mock_from_content.assert_called_once_with("")

    def test_add_file_success(self, staged_files, monkeypatch):
        """Test adding a file successfully."""
        # Setup
        file_path = "/mock/base/dir/test_file.py"
        relative_path = "test_file.py"

        # Mock os.path functions
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        monkeypatch.setattr(os.path, "relpath", lambda path, start: relative_path)

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
        file_path = "/mock/base/dir/nonexistent.py"

        # Mock os.path.exists to return False
        monkeypatch.setattr(os.path, "exists", lambda path: False)

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
        file_path = "/mock/base/dir/ignored_file.py"
        relative_path = "ignored_file.py"

        # Mock os.path functions
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        monkeypatch.setattr(os.path, "relpath", lambda path, start: relative_path)

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
        file_path = "/mock/base/dir/duplicate.py"
        relative_path = "duplicate.py"

        # Mock os.path functions
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        monkeypatch.setattr(os.path, "relpath", lambda path, start: relative_path)

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
        dir_path = "/mock/base/dir/test_dir"
        relative_dir = "test_dir"

        # Mock file paths that will be returned by filter_paths
        file_paths = [
            "/mock/base/dir/test_dir/file1.py",
            "/mock/base/dir/test_dir/file2.py",
            "/mock/base/dir/test_dir/subdir/file3.py"
        ]

        # Mock os.path functions
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        monkeypatch.setattr(os.path, "isdir", lambda path: True)
        monkeypatch.setattr(os.path, "isfile", lambda path: True)  # All paths are files
        monkeypatch.setattr(os.path, "relpath",
                            lambda path, start=None: path.replace("/mock/base/dir/", ""))

        # Configure mock to return our file paths
        staged_files.ignore_handler.filter_paths.return_value = file_paths

        # Mock print to avoid console output during tests
        with patch("builtins.print") as mock_print:
            # Execute
            result = staged_files.add_directory(dir_path)

            # Verify
            assert result == 3  # Should return the number of files added
            assert len(staged_files.files) == 3
            assert "test_dir/file1.py" in staged_files.files
            assert "test_dir/file2.py" in staged_files.files
            assert "test_dir/subdir/file3.py" in staged_files.files

    def test_add_directory_nonexistent(self, staged_files, monkeypatch):
        """Test adding a directory that doesn't exist."""
        # Setup
        dir_path = "/mock/base/dir/nonexistent_dir"

        # Mock os.path.exists to return False
        monkeypatch.setattr(os.path, "exists", lambda path: False)

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
        path = "/mock/base/dir/not_a_dir"

        # Mock os.path functions
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        monkeypatch.setattr(os.path, "isdir", lambda path: False)

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
        dir_path = "/mock/base/dir/test_dir"
        file_paths = [
            "/mock/base/dir/test_dir/file1.py",
            "/mock/base/dir/test_dir/file2.py"
        ]

        # Mock os.path functions
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        monkeypatch.setattr(os.path, "isdir", lambda path: True)
        monkeypatch.setattr(os.path, "isfile", lambda path: True)
        monkeypatch.setattr(os.path, "relpath",
                            lambda path, start=None: path.replace("/mock/base/dir/", ""))

        # Configure mock to return our file paths
        staged_files.ignore_handler.filter_paths.return_value = file_paths

        # Mock ThreadPoolExecutor
        mock_executor = MagicMock()
        mock_executor.__enter__.return_value.submit.side_effect = \
            lambda func, path: Mock(result=lambda: func(path))

        # Mock concurrent.futures.as_completed to yield our "futures"
        def mock_as_completed(futures):
            for future in futures:
                yield future

        # Setup process_file method to return relative paths
        staged_files._process_file = lambda path: path.replace("/mock/base/dir/", "")

        # Apply mocks
        with patch("concurrent.futures.ThreadPoolExecutor", return_value=mock_executor), \
                patch("concurrent.futures.as_completed", mock_as_completed), \
                patch("builtins.print"):
            # Execute
            result = staged_files.add_directory_parallel(dir_path)

            # Verify
            assert result == 2
            assert "test_dir/file1.py" in staged_files.files
            assert "test_dir/file2.py" in staged_files.files

    def test_remove_file(self, staged_files, monkeypatch):
        """Test removing a file from the staged list."""
        # Setup
        file_path = "/mock/base/dir/test_file.py"
        relative_path = "test_file.py"

        # Add the file first
        staged_files.files.append(relative_path)

        # Mock os.path.relpath
        monkeypatch.setattr(os.path, "relpath", lambda path, start: relative_path)

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
        file_path = "/mock/base/dir/nonexistent.py"
        relative_path = "nonexistent.py"

        # Mock os.path.relpath
        monkeypatch.setattr(os.path, "relpath", lambda path, start: relative_path)

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
