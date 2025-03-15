"""
Tests for the views in backtick/views.py.
"""

import io
import sys
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from swallow_framework import Context, EventDispatcher

from backtick.models import StagedFiles
from backtick.views import TerminalView


@pytest.fixture
def mock_model():
    """Fixture that returns a mocked StagedFiles model."""
    mock = Mock(spec=StagedFiles)

    # Create a mock for the files attribute with on_change method
    mock.files = Mock()
    mock.files.on_change = Mock()

    # Set default files list
    mock.files.__iter__ = lambda self: iter(["file1.py", "file2.py"])
    mock.files.__len__ = lambda self: 2

    return mock


@pytest.fixture
def mock_context():
    """Fixture that returns a mocked application context."""
    mock_event_dispatcher = Mock(spec=EventDispatcher)
    mock = Mock(spec=Context)
    mock.event_dispatcher = mock_event_dispatcher
    return mock


@contextmanager
def capture_stdout():
    """Context manager to capture stdout for testing print statements."""
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    try:
        yield captured_output
    finally:
        sys.stdout = old_stdout


class TestTerminalView:
    """Tests for the TerminalView class."""

    def test_init(self, mock_context, mock_model):
        """Test initialization correctly sets up view and watches model."""
        # Need to patch update to avoid side effects during initialization
        with patch.object(TerminalView, "update") as mock_update:
            # Execute - create a fresh instance
            view = TerminalView(mock_context, mock_model)

            # Verify model is being watched
            mock_model.files.on_change.assert_called_once()
            # The callback function that was registered should be view.update
            callback = mock_model.files.on_change.call_args[0][0]
            assert callback == view.update

            # Verify update was called with files during initialization
            mock_update.assert_called_once_with(mock_model.files)

    def test_show_help(self):
        """Test show_help displays the expected help information."""
        # Create a view with the init mocked to avoid side effects
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             capture_stdout() as captured:

            # Create instance and manually set required attributes
            view = TerminalView(None, None)
            # Add print_message method since we're bypassing __init__
            view.print_message = TerminalView.print_message.__get__(view)

            # Execute the method
            view.show_help()

            # Verify output contains key help text
            output = captured.getvalue()
            assert "Backtick - Collect file contents for the clipboard" in output
            assert "Commands:" in output
            assert "<file_path>" in output
            assert "<directory_path>" in output
            assert "<glob_pattern>" in output
            assert "l" in output
            assert "r <index>" in output
            assert "c" in output
            assert "h" in output
            assert "q" in output
            assert "`" in output

    def test_update(self):
        """Test update method calls list_files with the updated files."""
        # Setup - create view with mocked init and list_files
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             patch.object(TerminalView, "list_files") as mock_list_files:

            # Create instance
            view = TerminalView(None, None)
            files = ["test1.py", "test2.py"]

            # Execute
            view.update(files)

            # Verify
            mock_list_files.assert_called_once_with(files)

    def test_list_files_with_files(self):
        """Test list_files displays the staged files."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             capture_stdout() as captured:

            # Create instance and manually set required attributes
            view = TerminalView(None, None)
            # Add print_message method since we're bypassing __init__
            view.print_message = TerminalView.print_message.__get__(view)

            files = ["test1.py", "test2.py", "test3.py"]

            # Execute
            view.list_files(files)

            # Verify output
            output = captured.getvalue()
            assert "Staged Files (3 total):" in output
            assert "1. test1.py" in output
            assert "2. test2.py" in output
            assert "3. test3.py" in output

    def test_list_files_empty(self):
        """Test list_files displays a message when no files are staged."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             capture_stdout() as captured:

            # Create instance and manually set required attributes
            view = TerminalView(None, None)
            # Add print_message method since we're bypassing __init__
            view.print_message = TerminalView.print_message.__get__(view)

            files = []

            # Execute
            view.list_files(files)

            # Verify output
            output = captured.getvalue()
            assert "No files are staged." in output

    def test_show_error(self):
        """Test show_error displays an error message."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             capture_stdout() as captured:

            # Create instance and manually set required attributes
            view = TerminalView(None, None)
            # Add print_message method since we're bypassing __init__
            view.print_message = TerminalView.print_message.__get__(view)

            error_message = "Test error message"

            # Execute
            view.show_error(error_message)

            # Verify output
            output = captured.getvalue()
            assert f"Error: {error_message}" in output

    def test_show_info(self):
        """Test show_info displays an informational message."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             capture_stdout() as captured:

            # Create instance and manually set required attributes
            view = TerminalView(None, None)
            # Add print_message method since we're bypassing __init__
            view.print_message = TerminalView.print_message.__get__(view)

            info_message = "Test info message"

            # Execute
            view.show_info(info_message)

            # Verify output
            output = captured.getvalue()
            assert info_message in output

    def test_show_confirmation_yes(self):
        """Test show_confirmation returns True when user confirms."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             patch("builtins.input", return_value="y"):

            # Create instance
            view = TerminalView(None, None)

            # Execute
            result = view.show_confirmation("Confirm?", default=False)

            # Verify
            assert result is True

    def test_show_confirmation_no(self):
        """Test show_confirmation returns False when user declines."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             patch("builtins.input", return_value="n"):

            # Create instance
            view = TerminalView(None, None)

            # Execute
            result = view.show_confirmation("Confirm?", default=True)

            # Verify
            assert result is False

    def test_show_confirmation_default_true(self):
        """Test show_confirmation returns the default value (True) when user just presses Enter."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             patch("builtins.input", return_value=""):

            # Create instance
            view = TerminalView(None, None)

            # Execute
            result = view.show_confirmation("Confirm?", default=True)

            # Verify
            assert result is True

    def test_show_confirmation_default_false(self):
        """Test show_confirmation returns the default value (False) when user just presses Enter."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             patch("builtins.input", return_value=""):

            # Create instance
            view = TerminalView(None, None)

            # Execute
            result = view.show_confirmation("Confirm?", default=False)

            # Verify
            assert result is False

    def test_print_message_context_manager(self):
        """Test the print_message context manager adds a newline after the message."""
        # Setup - create view with mocked init
        with patch.object(TerminalView, "__init__", return_value=None) as mock_init, \
             capture_stdout() as captured:

            # Create instance
            view = TerminalView(None, None)

            # Execute
            with view.print_message():
                print("Test message", end="")  # No newline

            # Verify output ends with a newline
            output = captured.getvalue()
            assert output == "Test message\n"