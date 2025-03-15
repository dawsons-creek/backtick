"""
Tests for the command-line interface in backtick/cli.py.
"""

import sys
from unittest.mock import Mock, patch, call, mock_open

import pytest
from swallow_framework import Event

from backtick.cli import parse_args, cli, main
from backtick.commands import (
    AddFileCommand,
    AddDirectoryCommand,
    CopyToClipboardCommand
)


class TestParseArgs:
    """Tests for the parse_args function."""

    def test_parse_args_empty(self):
        """Test parsing empty arguments."""
        # Mock sys.argv
        with patch("sys.argv", ["backtick"]):
            # Execute
            args = parse_args()

            # Verify
            assert args.paths == []
            assert not args.no_recursive
            assert args.ignore_file == ".backtickignore"
            assert not args.print
            assert args.output is None
            assert not args.verbose

    def test_parse_args_with_paths(self):
        """Test parsing arguments with file and directory paths."""
        # Mock sys.argv
        with patch("sys.argv", ["backtick", "file1.py", "dir1", "dir2/file2.py"]):
            # Execute
            args = parse_args()

            # Verify
            assert args.paths == ["file1.py", "dir1", "dir2/file2.py"]
            assert not args.no_recursive

    def test_parse_args_with_flags(self):
        """Test parsing arguments with various flags."""
        # Mock sys.argv
        with patch("sys.argv", [
            "backtick", "-n", "-i", "custom_ignore", "--print", "-v", "file.py"
        ]):
            # Execute
            args = parse_args()

            # Verify
            assert args.paths == ["file.py"]
            assert args.no_recursive
            assert args.ignore_file == "custom_ignore"
            assert args.print
            assert args.output is None
            assert args.verbose

    def test_parse_args_with_output(self):
        """Test parsing arguments with output file."""
        # Mock sys.argv
        with patch("sys.argv", ["backtick", "-o", "output.md", "file.py"]):
            # Execute
            args = parse_args()

            # Verify
            assert args.paths == ["file.py"]
            assert args.output == "output.md"


class TestCli:
    """Tests for the cli function."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture that mocks all external dependencies for the cli function."""
        # Create mocks
        mock_model = Mock()
        mock_model.files = ["file1.py", "file2.py"]
        mock_model.get_file_count.return_value = 2

        mock_event_dispatcher = Mock()
        mock_context = Mock()
        mock_add_file_cmd = Mock(spec=AddFileCommand)
        mock_add_dir_cmd = Mock(spec=AddDirectoryCommand)
        mock_copy_cmd = Mock(spec=CopyToClipboardCommand)

        # Setup default formatter for copy command
        mock_formatter = Mock()
        mock_formatter.format_files.return_value = "Formatted content"
        mock_copy_cmd.formatter = mock_formatter

        # Apply patches
        with patch("backtick.cli.EventDispatcher", return_value=mock_event_dispatcher), \
             patch("backtick.cli.StagedFiles", return_value=mock_model), \
             patch("backtick.cli.Context", return_value=mock_context), \
             patch("backtick.cli.AddFileCommand", return_value=mock_add_file_cmd), \
             patch("backtick.cli.AddDirectoryCommand", return_value=mock_add_dir_cmd), \
             patch("backtick.cli.CopyToClipboardCommand", return_value=mock_copy_cmd), \
             patch("backtick.cli.parse_args"), \
             patch("builtins.print"), \
             patch("os.path.isfile"), \
             patch("os.path.isdir"):

            # Return all mocks
            yield {
                "model": mock_model,
                "event_dispatcher": mock_event_dispatcher,
                "context": mock_context,
                "add_file_cmd": mock_add_file_cmd,
                "add_dir_cmd": mock_add_dir_cmd,
                "copy_cmd": mock_copy_cmd
            }

    def test_cli_no_paths(self, mock_dependencies):
        """Test cli function with no paths specified."""
        # Configure mock_parse_args to return empty paths
        parse_args_mock = sys.modules["backtick.cli"].parse_args
        args = Mock()
        args.paths = []
        parse_args_mock.return_value = args

        # Execute
        result = cli()

        # Verify
        assert result == 1  # Should return error code
        # Verify error message was printed
        print_mock = sys.modules["builtins"].print
        print_mock.assert_called_with("Error: No files or directories specified.")

    def test_cli_with_files(self, mock_dependencies):
        """Test cli function with file paths."""
        # Configure mock_parse_args
        parse_args_mock = sys.modules["backtick.cli"].parse_args
        args = Mock()
        args.paths = ["file1.py", "file2.py"]
        args.no_recursive = False
        args.ignore_file = ".backtickignore"
        args.print = False
        args.output = None
        args.verbose = False
        parse_args_mock.return_value = args

        # Configure os.path mocks
        isfile_mock = sys.modules["os.path"].isfile
        isdir_mock = sys.modules["os.path"].isdir
        isfile_mock.side_effect = lambda path: path.endswith(".py")
        isdir_mock.return_value = False

        # Execute
        result = cli()

        # Verify
        assert result == 0  # Should return success code

        # Verify StagedFiles was created with correct args
        staged_files_mock = sys.modules["backtick.cli"].StagedFiles
        staged_files_mock.assert_called_once_with(ignore_file_path=".backtickignore")

        # Verify AddFileCommand was mapped and dispatched
        context_mock = mock_dependencies["context"]
        assert "ADD_FILE" in [call_args[0][0] for call_args in context_mock.map_command.call_args_list]

        # Verify dispatch was called for each file
        # The actual calls are with Event objects, not direct strings
        from swallow_framework import Event
        expected_calls = [
            call(Event(name="ADD_FILE", data="file1.py")),
            call(Event(name="ADD_FILE", data="file2.py")),
            call(Event(name="COPY_TO_CLIPBOARD", data=None))
        ]
        context_mock.dispatch.assert_has_calls(expected_calls, any_order=False)

    def test_cli_with_directories(self, mock_dependencies):
        """Test cli function with directory paths."""
        # Configure mock_parse_args
        parse_args_mock = sys.modules["backtick.cli"].parse_args
        args = Mock()
        args.paths = ["dir1", "dir2"]
        args.no_recursive = False
        args.ignore_file = ".backtickignore"
        args.print = False
        args.output = None
        args.verbose = False
        parse_args_mock.return_value = args

        # Configure os.path mocks
        isfile_mock = sys.modules["os.path"].isfile
        isdir_mock = sys.modules["os.path"].isdir
        isfile_mock.return_value = False
        isdir_mock.return_value = True

        # Execute
        result = cli()

        # Verify
        assert result == 0  # Should return success code

        # Verify AddDirectoryCommand was mapped and dispatched
        context_mock = mock_dependencies["context"]
        assert "ADD_DIRECTORY" in [call_args[0][0] for call_args in context_mock.map_command.call_args_list]

        # Verify dispatch was called for each directory
        expected_calls = [
            call(Event(name="ADD_DIRECTORY", data="dir1")),
            call(Event(name="ADD_DIRECTORY", data="dir2")),
            call(Event(name="COPY_TO_CLIPBOARD", data=None))
        ]
        context_mock.dispatch.assert_has_calls(expected_calls, any_order=False)

    def test_cli_print_option(self, mock_dependencies):
        """Test cli function with --print option."""
        # Configure mock_parse_args
        parse_args_mock = sys.modules["backtick.cli"].parse_args
        args = Mock()
        args.paths = ["file1.py"]
        args.no_recursive = False
        args.ignore_file = ".backtickignore"
        args.print = True
        args.output = None
        args.verbose = False
        parse_args_mock.return_value = args

        # Configure os.path mocks
        isfile_mock = sys.modules["os.path"].isfile
        isdir_mock = sys.modules["os.path"].isdir
        isfile_mock.return_value = True
        isdir_mock.return_value = False

        # Execute
        result = cli()

        # Verify
        assert result == 0  # Should return success code

        # Verify content was formatted but not copied to clipboard
        copy_cmd_mock = mock_dependencies["copy_cmd"]
        assert copy_cmd_mock.formatter.format_files.called

        # Verify print was called with the formatted content
        print_mock = sys.modules["builtins"].print
        print_mock.assert_any_call(copy_cmd_mock.formatter.format_files.return_value)

        # Verify COPY_TO_CLIPBOARD was not dispatched
        context_mock = mock_dependencies["context"]
        # Check that no Event with name="COPY_TO_CLIPBOARD" was passed to dispatch
        assert not any(args[0][0].name == "COPY_TO_CLIPBOARD" if hasattr(args[0][0], 'name') else False
                       for args in context_mock.dispatch.call_args_list)

    def test_cli_output_option(self, mock_dependencies):
        """Test cli function with --output option."""
        # Configure mock_parse_args
        parse_args_mock = sys.modules["backtick.cli"].parse_args
        args = Mock()
        args.paths = ["file1.py"]
        args.no_recursive = False
        args.ignore_file = ".backtickignore"
        args.print = False
        args.output = "output.md"
        args.verbose = False
        parse_args_mock.return_value = args

        # Configure os.path mocks
        isfile_mock = sys.modules["os.path"].isfile
        isdir_mock = sys.modules["os.path"].isdir
        isfile_mock.return_value = True
        isdir_mock.return_value = False

        # Mock file open
        with patch("builtins.open", mock_open()) as mock_file:
            # Execute
            result = cli()

            # Verify
            assert result == 0  # Should return success code

            # Verify file was opened and written to
            mock_file.assert_called_once_with("output.md", 'w', encoding='utf-8')
            mock_file.return_value.write.assert_called_once_with("Formatted content")

            # Verify COPY_TO_CLIPBOARD was not dispatched
            context_mock = mock_dependencies["context"]
            assert not any(args[0][0] == "COPY_TO_CLIPBOARD" for args in context_mock.dispatch.call_args_list)

    def test_cli_no_staged_files(self, mock_dependencies):
        """Test cli function when no files were staged."""
        # Configure mock_parse_args
        parse_args_mock = sys.modules["backtick.cli"].parse_args
        args = Mock()
        args.paths = ["file1.py"]
        args.no_recursive = False
        args.ignore_file = ".backtickignore"
        args.print = False
        args.output = None
        args.verbose = False
        parse_args_mock.return_value = args

        # Configure os.path mocks
        isfile_mock = sys.modules["os.path"].isfile
        isdir_mock = sys.modules["os.path"].isdir
        isfile_mock.return_value = True
        isdir_mock.return_value = False

        # Set get_file_count to return 0
        mock_dependencies["model"].get_file_count.return_value = 0

        # Execute
        result = cli()

        # Verify
        assert result == 1  # Should return error code

        # Verify error message was printed
        print_mock = sys.modules["builtins"].print
        print_mock.assert_any_call("No files were staged. Nothing to copy.")


class TestMain:
    """Tests for the main function."""

    def test_main_success(self):
        """Test main function with successful cli execution."""
        # Mock cli function to return success
        with patch("backtick.cli.cli", return_value=0) as mock_cli:
            # Execute
            result = main()

            # Verify
            assert result == 0
            mock_cli.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """Test main function with KeyboardInterrupt."""
        # Mock cli function to raise KeyboardInterrupt
        with patch("backtick.cli.cli", side_effect=KeyboardInterrupt), \
             patch("builtins.print") as mock_print:
            # Execute
            result = main()

            # Verify
            assert result == 130  # Standard exit code for SIGINT
            mock_print.assert_called_once_with("\nOperation cancelled.")

    def test_main_exception(self):
        """Test main function with general exception."""
        # Mock cli function to raise Exception
        error_message = "Test exception"
        with patch("backtick.cli.cli", side_effect=Exception(error_message)), \
             patch("builtins.print") as mock_print:
            # Execute
            result = main()

            # Verify
            assert result == 1  # Error exit code
            mock_print.assert_called_once_with(f"Error: {error_message}")