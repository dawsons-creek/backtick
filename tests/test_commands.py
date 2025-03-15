"""
Tests for the command implementations in backtick/commands.py.
"""

from unittest.mock import Mock, patch

import pytest

from backtick.commands import (
    AddFileCommand,
    AddDirectoryCommand,
    RemoveCommand,
    ClearFilesCommand,
    CopyToClipboardCommand
)
from backtick.models import StagedFiles
from backtick.utils import ClipboardFormatter


@pytest.fixture
def mock_model():
    """Fixture that returns a mocked StagedFiles model."""
    mock = Mock(spec=StagedFiles)
    # Set up the files attribute to simulate the files list
    mock.files = ["file1.py", "file2.py"]
    return mock


class TestAddFileCommand:
    """Tests for the AddFileCommand class."""

    def test_init(self, mock_model):
        """Test initialization of AddFileCommand."""
        # Execute
        command = AddFileCommand(mock_model)

        # Verify
        assert command.model == mock_model

    def test_execute(self, mock_model):
        """Test execute method of AddFileCommand."""
        # Setup
        command = AddFileCommand(mock_model)
        file_path = "test_file.py"

        # Execute
        command.execute(file_path)

        # Verify
        mock_model.add_file.assert_called_once_with(file_path)


class TestAddDirectoryCommand:
    """Tests for the AddDirectoryCommand class."""

    def test_init_defaults(self, mock_model):
        """Test initialization with default parameters."""
        # Execute
        command = AddDirectoryCommand(mock_model)

        # Verify
        assert command.model == mock_model
        assert command.use_parallel is True
        assert command.recursive is True

    def test_init_custom(self, mock_model):
        """Test initialization with custom parameters."""
        # Execute
        command = AddDirectoryCommand(mock_model, use_parallel=False, recursive=False)

        # Verify
        assert command.model == mock_model
        assert command.use_parallel is False
        assert command.recursive is False

    def test_execute_parallel(self, mock_model):
        """Test execute method with parallel processing."""
        # Setup
        command = AddDirectoryCommand(mock_model, use_parallel=True)
        dir_path = "test_dir"

        # Execute
        command.execute(dir_path)

        # Verify
        mock_model.add_directory_parallel.assert_called_once_with(dir_path, recursive=True)

    def test_execute_non_parallel(self, mock_model):
        """Test execute method without parallel processing."""
        # Setup
        command = AddDirectoryCommand(mock_model, use_parallel=False)
        dir_path = "test_dir"

        # Execute
        command.execute(dir_path)

        # Verify
        mock_model.add_directory.assert_called_once_with(dir_path, recursive=True)

    def test_execute_non_recursive(self, mock_model):
        """Test execute method with recursive=False."""
        # Setup
        command = AddDirectoryCommand(mock_model, recursive=False)
        dir_path = "test_dir"

        # Execute
        command.execute(dir_path)

        # Verify
        mock_model.add_directory_parallel.assert_called_once_with(dir_path, recursive=False)


class TestRemoveCommand:
    """Tests for the RemoveCommand class."""

    def test_init(self, mock_model):
        """Test initialization of RemoveCommand."""
        # Execute
        command = RemoveCommand(mock_model)

        # Verify
        assert command.model == mock_model

    def test_execute_with_path(self, mock_model):
        """Test execute method with a file path."""
        # Setup
        command = RemoveCommand(mock_model)
        file_path = "test_file.py"

        # Execute
        command.execute(file_path)

        # Verify
        mock_model.remove_file.assert_called_once_with(file_path)

    def test_execute_with_valid_index(self, mock_model):
        """Test execute method with a valid index."""
        # Setup
        command = RemoveCommand(mock_model)
        index = 1  # 1-based index

        # Execute
        command.execute(index)

        # Verify
        mock_model.remove_file.assert_called_once_with("file1.py")

    def test_execute_with_invalid_index(self, mock_model):
        """Test execute method with an out-of-range index."""
        # Setup
        command = RemoveCommand(mock_model)
        index = 10  # Out of range

        # Mock print to capture output
        with patch("builtins.print") as mock_print:
            # Execute
            command.execute(index)

            # Verify
            mock_model.remove_file.assert_not_called()
            mock_print.assert_called_once_with("Error: Index 10 is out of range.")


class TestClearFilesCommand:
    """Tests for the ClearFilesCommand class."""

    def test_init(self, mock_model):
        """Test initialization of ClearFilesCommand."""
        # Execute
        command = ClearFilesCommand(mock_model)

        # Verify
        assert command.model == mock_model

    def test_execute(self, mock_model):
        """Test execute method of ClearFilesCommand."""
        # Setup
        command = ClearFilesCommand(mock_model)

        # Execute
        command.execute()

        # Verify
        mock_model.clear_files.assert_called_once()


class TestCopyToClipboardCommand:
    """Tests for the CopyToClipboardCommand class."""

    def test_init_default(self, mock_model):
        """Test initialization with default parameters."""
        # Execute
        command = CopyToClipboardCommand(mock_model)

        # Verify
        assert command.model == mock_model
        assert isinstance(command.formatter, ClipboardFormatter)
        assert command.formatter.file_cache.maxsize == 50  # Default cache size

    def test_init_custom_cache(self, mock_model):
        """Test initialization with custom cache size."""
        # Execute
        cache_size = 100
        command = CopyToClipboardCommand(mock_model, cache_size=cache_size)

        # Verify
        assert isinstance(command.formatter, ClipboardFormatter)
        assert command.formatter.file_cache.maxsize == cache_size

    def test_execute_with_files(self, mock_model):
        """Test execute method with files in the model."""
        # Setup
        command = CopyToClipboardCommand(mock_model)
        mock_formatter = Mock(spec=ClipboardFormatter)
        command.formatter = mock_formatter

        # Mock the formatter and pyperclip.copy
        mock_formatter.format_files.return_value = "Formatted content"

        with patch("backtick.commands.pyperclip.copy") as mock_copy, \
                patch("builtins.print") as mock_print:
            # Execute
            command.execute()

            # Verify
            mock_formatter.format_files.assert_called_once_with(mock_model.files)
            mock_copy.assert_called_once_with("Formatted content")
            # Check that appropriate messages were printed
            assert any("Formatting files for clipboard" in call_args[0][0] for call_args in mock_print.call_args_list)
            assert any("Copying to clipboard" in call_args[0][0] for call_args in mock_print.call_args_list)
            assert any("Copied 2 file(s) to clipboard" in call_args[0][0] for call_args in mock_print.call_args_list)

    def test_execute_no_files(self, mock_model):
        """Test execute method with no files in the model."""
        # Setup
        command = CopyToClipboardCommand(mock_model)
        # Set model.files to empty list
        mock_model.files = []

        with patch("backtick.commands.pyperclip.copy") as mock_copy, \
                patch("builtins.print") as mock_print:
            # Execute
            command.execute()

            # Verify
            mock_copy.assert_not_called()
            mock_print.assert_called_once_with("No files are currently staged.")

    def test_clear_cache(self, mock_model):
        """Test clear_cache method."""
        # Setup
        command = CopyToClipboardCommand(mock_model)
        mock_formatter = Mock(spec=ClipboardFormatter)
        command.formatter = mock_formatter

        with patch("builtins.print") as mock_print:
            # Execute
            command.clear_cache()

            # Verify
            mock_formatter.clear_cache.assert_called_once()
            mock_print.assert_called_once_with("Clipboard formatter cache cleared.")