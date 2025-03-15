"""
Tests for the interactive shell functionality in backtick/main.py.
"""

import os
import sys
import glob
import pytest
from unittest.mock import Mock, patch, MagicMock, call, ANY

from backtick.main import (
    setup_completers,
    setup_key_bindings,
    setup_prompt_session,
    initialize_environment,
    initialize_mvc,
    is_glob_pattern,
    handle_glob_pattern,
    handle_path_input,
    create_command_handlers,
    handle_remove_command,
    handle_user_input,
    main_loop,
    main
)
from backtick.models import StagedFiles
from backtick.views import TerminalView
from backtick.commands import (
    AddFileCommand,
    AddDirectoryCommand,
    CopyToClipboardCommand,
    ClearFilesCommand,
    RemoveCommand
)
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer
from prompt_toolkit.key_binding import KeyBindings
from swallow_framework import Event, EventDispatcher, Context


class TestSetupFunctions:
    """Tests for the setup functions in main.py."""

    def test_setup_completers(self):
        """Test that setup_completers returns a properly configured completer."""
        # Execute
        with patch('backtick.main.WordCompleter') as mock_word_completer, \
             patch('backtick.main.IgnoreAwarePathCompleter') as mock_path_completer, \
             patch('backtick.main.merge_completers') as mock_merge:

            mock_word_completer.return_value = "word_completer"
            mock_path_completer.return_value = "path_completer"
            mock_merge.return_value = "merged_completer"

            result = setup_completers()

            # Verify
            mock_word_completer.assert_called_once()
            mock_path_completer.assert_called_once_with(expanduser=True)
            mock_merge.assert_called_once_with(["word_completer", "path_completer"])
            assert result == "merged_completer"

    def test_setup_key_bindings(self):
        """Test that setup_key_bindings creates appropriate key bindings."""
        # Execute
        kb = setup_key_bindings()

        # Verify
        assert isinstance(kb, KeyBindings)

        # Check for Ctrl+X binding - we need to check the key in each binding's keys
        ctrl_x_exists = any('c-x' in str(binding.keys) for binding in kb.bindings)
        assert ctrl_x_exists, "Ctrl+X binding not found"

        # Check for Tab binding (which might be represented as c-i)
        tab_exists = any('tab' in str(binding.keys).lower() or 'c-i' in str(binding.keys).lower()
                        for binding in kb.bindings)
        assert tab_exists, "Tab binding not found"

    def test_setup_prompt_session(self):
        """Test that setup_prompt_session creates a properly configured prompt session."""
        # Setup
        mock_completer = Mock(spec=Completer)
        mock_kb = Mock(spec=KeyBindings)

        # Execute
        with patch('backtick.main.PromptSession') as mock_session, \
             patch('backtick.main.os.path.expanduser', return_value='~/.backtick_history'), \
             patch('backtick.main.FileHistory') as mock_history, \
             patch('backtick.main.Style') as mock_style:

            setup_prompt_session(mock_completer, mock_kb)

            # Verify
            mock_session.assert_called_once()
            mock_history.assert_called_once()
            mock_style.from_dict.assert_called_once()

    def test_initialize_environment(self):
        """Test that initialize_environment sets up all necessary components."""
        # Execute
        with patch('backtick.main.setup_completers') as mock_completers, \
             patch('backtick.main.setup_key_bindings') as mock_kb, \
             patch('backtick.main.setup_prompt_session') as mock_session:

            mock_completers.return_value = "completers"
            mock_kb.return_value = "kb"
            mock_session.return_value = "session"

            result = initialize_environment()

            # Verify
            mock_completers.assert_called_once()
            mock_kb.assert_called_once()
            mock_session.assert_called_once_with("completers", "kb")
            assert result == "session"

    def test_initialize_mvc(self):
        """Test that initialize_mvc sets up the MVC components correctly."""
        # Execute
        with patch('backtick.main.EventDispatcher') as mock_dispatcher, \
             patch('backtick.main.StagedFiles') as mock_model_class, \
             patch('backtick.main.Context') as mock_context_class, \
             patch('backtick.main.TerminalView') as mock_view_class, \
             patch('backtick.main.AddFileCommand') as mock_add_file, \
             patch('backtick.main.AddDirectoryCommand') as mock_add_dir, \
             patch('backtick.main.RemoveCommand') as mock_remove, \
             patch('backtick.main.ClearFilesCommand') as mock_clear, \
             patch('backtick.main.CopyToClipboardCommand') as mock_copy:

            # Create mock instances
            mock_dispatcher_instance = Mock()
            mock_model_instance = Mock()
            mock_context_instance = Mock()
            mock_view_instance = Mock()

            # Configure the mocks
            mock_dispatcher.return_value = mock_dispatcher_instance
            mock_model_class.return_value = mock_model_instance
            mock_context_class.return_value = mock_context_instance
            mock_view_class.return_value = mock_view_instance

            # Execute
            model, view, context = initialize_mvc()

            # Verify
            mock_dispatcher.assert_called_once()
            mock_model_class.assert_called_once()
            mock_context_class.assert_called_once_with(mock_dispatcher_instance)
            mock_view_class.assert_called_once_with(mock_context_instance, mock_model_instance)

            # Verify command mapping
            assert mock_context_instance.map_command.call_count == 5
            mock_context_instance.map_command.assert_any_call("ADD_FILE", ANY)
            mock_context_instance.map_command.assert_any_call("ADD_DIRECTORY", ANY)
            mock_context_instance.map_command.assert_any_call("REMOVE", ANY)
            mock_context_instance.map_command.assert_any_call("CLEAR_FILES", ANY)
            mock_context_instance.map_command.assert_any_call("COPY_TO_CLIPBOARD", ANY)

            # Verify return values
            assert model == mock_model_instance
            assert view == mock_view_instance
            assert context == mock_context_instance


class TestGlobAndPathHandling:
    """Tests for glob pattern and path handling functions."""

    @pytest.mark.parametrize("pattern,expected", [
        ("*.py", True),
        ("file?.txt", True),
        ("dir/[abc].js", True),
        ("dir/{src,lib}/*.ts", True),
        ("plainfile.txt", False),
        ("dir/subdir/file.txt", False),
        (".gitignore", False),
    ])
    def test_is_glob_pattern(self, pattern, expected):
        """Test that is_glob_pattern correctly identifies glob patterns."""
        # Execute
        result = is_glob_pattern(pattern)

        # Verify
        assert result == expected

    def test_handle_glob_pattern_with_matches(self):
        """Test handling glob patterns that match files."""
        # Setup
        pattern = "*.py"
        mock_context = Mock(spec=Context)
        matched_paths = ["file1.py", "file2.py"]

        # Execute
        with patch('backtick.main.glob.glob', return_value=matched_paths), \
             patch('backtick.main.os.path.isfile', return_value=True), \
             patch('backtick.main.os.path.isdir', return_value=False), \
             patch('builtins.print') as mock_print:

            handle_glob_pattern(pattern, mock_context)

            # Verify
            assert mock_context.dispatch.call_count == 2
            # Verify files were dispatched
            mock_context.dispatch.assert_has_calls([
                call(Event("ADD_FILE", "file1.py")),
                call(Event("ADD_FILE", "file2.py"))
            ])
            # Verify summary was printed
            mock_print.assert_called_once_with("Added 2 files and 0 directories matching '*.py'")

    def test_handle_glob_pattern_no_matches(self):
        """Test handling glob patterns that don't match any files."""
        # Setup
        pattern = "*.xyz"
        mock_context = Mock(spec=Context)

        # Execute
        with patch('backtick.main.glob.glob', return_value=[]), \
             patch('builtins.print') as mock_print:

            handle_glob_pattern(pattern, mock_context)

            # Verify
            mock_context.dispatch.assert_not_called()
            mock_print.assert_called_once_with(f"No paths match the pattern '{pattern}'")

    def test_handle_path_input_file(self):
        """Test handling a file path input."""
        # Setup
        file_path = "test_file.txt"
        mock_context = Mock(spec=Context)

        # Execute
        with patch('backtick.main.is_glob_pattern', return_value=False), \
             patch('backtick.main.os.path.expanduser', return_value=file_path), \
             patch('backtick.main.os.path.isdir', return_value=False), \
             patch('backtick.main.os.path.isfile', return_value=True):

            handle_path_input(file_path, mock_context)

            # Verify
            mock_context.dispatch.assert_called_once_with(Event("ADD_FILE", file_path))

    def test_handle_path_input_directory(self):
        """Test handling a directory path input."""
        # Setup
        dir_path = "test_dir"
        mock_context = Mock(spec=Context)

        # Execute
        with patch('backtick.main.is_glob_pattern', return_value=False), \
             patch('backtick.main.os.path.expanduser', return_value=dir_path), \
             patch('backtick.main.os.path.isdir', return_value=True):

            handle_path_input(dir_path, mock_context)

            # Verify
            mock_context.dispatch.assert_called_once_with(Event("ADD_DIRECTORY", dir_path))

    def test_handle_path_input_glob(self):
        """Test handling a glob pattern input."""
        # Setup
        pattern = "*.py"
        mock_context = Mock(spec=Context)

        # Execute
        with patch('backtick.main.is_glob_pattern', return_value=True), \
             patch('backtick.main.handle_glob_pattern') as mock_handle_glob:

            handle_path_input(pattern, mock_context)

            # Verify
            mock_handle_glob.assert_called_once_with(pattern, mock_context)

    def test_handle_path_input_nonexistent(self):
        """Test handling a path that doesn't exist."""
        # Setup
        nonexistent_path = "nonexistent_file.txt"
        mock_context = Mock(spec=Context)

        # Execute
        with patch('backtick.main.is_glob_pattern', return_value=False), \
             patch('backtick.main.os.path.expanduser', return_value=nonexistent_path), \
             patch('backtick.main.os.path.isdir', return_value=False), \
             patch('backtick.main.os.path.isfile', return_value=False), \
             patch('builtins.print') as mock_print:

            handle_path_input(nonexistent_path, mock_context)

            # Verify
            mock_context.dispatch.assert_not_called()
            mock_print.assert_called_once_with(f"Error: Path '{nonexistent_path}' does not exist.")


class TestCommandHandling:
    """Tests for command handling functions."""

    def test_create_command_handlers(self):
        """Test creating command handlers."""
        # Setup
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)

        # Execute
        handlers = create_command_handlers(mock_model, mock_view, mock_context)

        # Verify
        assert 'q' in handlers
        assert 'h' in handlers
        assert 'l' in handlers
        assert 'c' in handlers
        assert '`' in handlers

        # Configure mock methods to return expected values
        mock_view.show_help.return_value = True
        mock_view.list_files.return_value = True
        mock_context.dispatch.return_value = None

        # Verify handler behavior
        assert handlers['q']() is False  # Should return False to exit

        # Test the help handler calls view.show_help
        result = handlers['h']()
        mock_view.show_help.assert_called_once()
        assert result is True  # Should return True to continue

        # Test that the list handler calls view.list_files
        result = handlers['l']()
        mock_view.list_files.assert_called_once_with(mock_model.files)
        assert result is True  # Should return True to continue

        # Test that the clear handler dispatches CLEAR_FILES
        result = handlers['c']()
        mock_context.dispatch.assert_called_once_with(Event("CLEAR_FILES"))
        assert result is True  # Should return True to continue

        # Reset for the next test
        mock_context.reset_mock()

        # Test that the copy handler dispatches COPY_TO_CLIPBOARD and returns False
        assert handlers['`']() is False
        mock_context.dispatch.assert_called_once_with(Event("COPY_TO_CLIPBOARD"))

    def test_handle_remove_command_valid_index(self):
        """Test handling a valid remove command."""
        # Setup
        args = "1"  # First item index
        mock_model = Mock(spec=StagedFiles)
        mock_model.files = ["file1.txt", "file2.txt"]
        mock_context = Mock(spec=Context)

        # Execute
        result = handle_remove_command(args, mock_model, mock_context)

        # Verify
        assert result is True  # Should return True to continue
        mock_context.dispatch.assert_called_once_with(Event("REMOVE", "file1.txt"))

    def test_handle_remove_command_invalid_index(self):
        """Test handling a remove command with an invalid index."""
        # Setup
        args = "10"  # Out of range
        mock_model = Mock(spec=StagedFiles)
        mock_model.files = ["file1.txt", "file2.txt"]
        mock_context = Mock(spec=Context)

        # Execute
        with patch('builtins.print') as mock_print:
            result = handle_remove_command(args, mock_model, mock_context)

            # Verify
            assert result is True  # Should return True to continue
            mock_context.dispatch.assert_not_called()
            mock_print.assert_called_once_with("Error: Index 10 is out of range.")

    def test_handle_remove_command_non_numeric(self):
        """Test handling a remove command with a non-numeric index."""
        # Setup
        args = "abc"  # Not a number
        mock_model = Mock(spec=StagedFiles)
        mock_context = Mock(spec=Context)

        # Execute
        with patch('builtins.print') as mock_print:
            result = handle_remove_command(args, mock_model, mock_context)

            # Verify
            assert result is True  # Should return True to continue
            mock_context.dispatch.assert_not_called()
            mock_print.assert_called_once_with("Error: Invalid index 'abc'. Please provide a number.")

    def test_handle_user_input_empty(self):
        """Test handling empty user input."""
        # Setup
        user_input = ""
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)
        mock_handlers = {}

        # Execute
        result = handle_user_input(user_input, mock_model, mock_view, mock_context, mock_handlers)

        # Verify
        assert result is True  # Should return True to continue

    def test_handle_user_input_simple_command(self):
        """Test handling a simple command like 'q' or 'c'."""
        # Setup
        user_input = "q"
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)

        # Create a handlers dict with a mock for the 'q' command
        mock_q_handler = Mock(return_value=False)  # Return False to simulate exit
        mock_handlers = {'q': mock_q_handler}

        # Execute
        result = handle_user_input(user_input, mock_model, mock_view, mock_context, mock_handlers)

        # Verify
        assert result is False  # Should return False to exit
        mock_q_handler.assert_called_once()

    def test_handle_user_input_remove_command(self):
        """Test handling a remove command like 'r 1'."""
        # Setup
        user_input = "r 1"
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)
        mock_handlers = {}

        # Execute
        with patch('backtick.main.handle_remove_command', return_value=True) as mock_handle_remove:
            result = handle_user_input(user_input, mock_model, mock_view, mock_context, mock_handlers)

            # Verify
            assert result is True  # Should return True to continue
            mock_handle_remove.assert_called_once_with("1", mock_model, mock_context)

    def test_handle_user_input_path(self):
        """Test handling a path input."""
        # Setup
        user_input = "file.txt"
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)
        mock_handlers = {}

        # Execute
        with patch('backtick.main.handle_path_input') as mock_handle_path:
            result = handle_user_input(user_input, mock_model, mock_view, mock_context, mock_handlers)

            # Verify
            assert result is True  # Should return True to continue
            mock_handle_path.assert_called_once_with(user_input, mock_context)


class TestMainLoop:
    """Tests for the main_loop function."""

    def test_main_loop_success(self):
        """Test the main_loop function with successful execution."""
        # Setup
        mock_session = Mock(spec=PromptSession)
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)

        # Configure mocks
        mock_session.prompt.side_effect = ["file.txt", "q"]  # First enter a file, then quit

        # Execute
        with patch('backtick.main.initialize_environment', return_value=mock_session), \
             patch('backtick.main.initialize_mvc', return_value=(mock_model, mock_view, mock_context)), \
             patch('backtick.main.create_command_handlers') as mock_create_handlers, \
             patch('backtick.main.handle_user_input') as mock_handle_input:

            # Configure handle_user_input to return True for first call, False for second
            mock_handle_input.side_effect = [True, False]

            result = main_loop()

            # Verify
            mock_session.prompt.assert_called()
            mock_view.show_help.assert_called_once()
            assert mock_handle_input.call_count == 2
            assert result == 0  # Should return 0 for success

    def test_main_loop_keyboard_interrupt(self):
        """Test the main_loop function with a KeyboardInterrupt."""
        # Setup
        mock_session = Mock(spec=PromptSession)
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)

        # Configure mocks
        mock_session.prompt.side_effect = [KeyboardInterrupt, "q"]  # First raise KeyboardInterrupt, then quit

        # Execute
        with patch('backtick.main.initialize_environment', return_value=mock_session), \
             patch('backtick.main.initialize_mvc', return_value=(mock_model, mock_view, mock_context)), \
             patch('backtick.main.create_command_handlers') as mock_create_handlers, \
             patch('backtick.main.handle_user_input', return_value=False), \
             patch('builtins.print') as mock_print:

            result = main_loop()

            # Verify
            assert mock_session.prompt.call_count == 2
            mock_print.assert_any_call("\nUse 'q' to quit.")
            assert result == 0  # Should return 0 for success

    def test_main_loop_eof_error(self):
        """Test the main_loop function with an EOFError."""
        # Setup
        mock_session = Mock(spec=PromptSession)
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)

        # Configure mocks
        mock_session.prompt.side_effect = EOFError  # Simulate Ctrl+D

        # Execute
        with patch('backtick.main.initialize_environment', return_value=mock_session), \
             patch('backtick.main.initialize_mvc', return_value=(mock_model, mock_view, mock_context)), \
             patch('backtick.main.create_command_handlers') as mock_create_handlers, \
             patch('builtins.print') as mock_print:

            result = main_loop()

            # Verify
            mock_session.prompt.assert_called_once()
            mock_print.assert_any_call("\nGoodbye!")
            assert result == 0  # Should return 0 for success

    def test_main_loop_general_exception(self):
        """Test the main_loop function with a general exception."""
        # Setup
        mock_session = Mock(spec=PromptSession)
        mock_model = Mock(spec=StagedFiles)
        mock_view = Mock(spec=TerminalView)
        mock_context = Mock(spec=Context)

        # Configure mocks to raise an exception on first call, then quit
        mock_session.prompt.side_effect = ["file.txt", "q"]

        # Execute
        with patch('backtick.main.initialize_environment', return_value=mock_session), \
             patch('backtick.main.initialize_mvc', return_value=(mock_model, mock_view, mock_context)), \
             patch('backtick.main.create_command_handlers') as mock_create_handlers, \
             patch('backtick.main.handle_user_input', side_effect=[Exception("Test error"), False]), \
             patch('builtins.print') as mock_print, \
             patch('traceback.print_exc') as mock_traceback:

            result = main_loop()

            # Verify
            assert mock_session.prompt.call_count == 2
            mock_print.assert_any_call("Error: Test error")
            mock_traceback.assert_called_once()
            assert result == 0  # Should return 0 for success


class TestMain:
    """Tests for the main function."""

    def test_main_success(self):
        """Test the main function with successful execution."""
        # Execute
        with patch('backtick.main.main_loop', return_value=0) as mock_main_loop:
            result = main()

            # Verify
            mock_main_loop.assert_called_once()
            assert result == 0

    def test_main_exception(self):
        """Test the main function with an exception."""
        # Execute
        with patch('backtick.main.main_loop', side_effect=Exception("Fatal error")), \
             patch('builtins.print') as mock_print, \
             patch('traceback.print_exc') as mock_traceback:

            result = main()

            # Verify
            mock_print.assert_called_once_with("Fatal error: Fatal error")
            mock_traceback.assert_called_once()
            assert result == 1  # Should return 1 for error
