#!/usr/bin/env python3
"""
Backtick Interactive Shell - A terminal app for staging files and copying to clipboard

Usage:
- Type a file or directory path to stage it
- Type a glob pattern to stage multiple files (e.g., *.py)
- Type ` and press Enter to copy all staged files to the clipboard
- Type 'l' to show staged files
- Type 'c' to clear staged files
- Type 'q' to exit
"""

import glob
import os
import sys
from typing import Dict, Callable, Optional, Any, Tuple, List

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, merge_completers
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.styles import Style

from backtick.commands import (
    AddFileCommand,
    ClearFilesCommand,
    CopyToClipboardCommand,
    AddDirectoryCommand,
    RemoveCommand
)
from swallow_framework import EventDispatcher, Event, Context
from backtick.models import StagedFiles
from backtick.ignore import IgnoreAwarePathCompleter
from backtick.views import TerminalView


def setup_completers():
    """
    Set up command and path completers.

    Returns:
        A merged completer for commands and paths
    """
    commands = ['`', 'c', 'l', 'q', 'r', 'h']
    command_completer = WordCompleter(commands)
    path_completer = IgnoreAwarePathCompleter(expanduser=True)
    return merge_completers([command_completer, path_completer])


def setup_key_bindings():
    """
    Set up key bindings for the prompt session.

    Returns:
        A KeyBindings object with the configured key bindings
    """
    kb = KeyBindings()

    @kb.add('c-x')
    def show_cwd(event):
        """Show the current working directory when Ctrl+X is pressed."""
        event.app.current_buffer.insert_text(f"# CWD: {os.getcwd()}")

    @kb.add(Keys.Tab)
    def handle_tab(event):
        """Handle tab completion."""
        if event.app.current_buffer.complete_state:
            event.app.current_buffer.complete_next()
        else:
            buff = event.app.current_buffer
            if buff.text:
                buff.start_completion()

    return kb


def setup_prompt_session(merged_completer, kb):
    """
    Set up the prompt session with history and styling.

    Args:
        merged_completer: The completer to use for the prompt
        kb: The key bindings to use for the prompt

    Returns:
        A configured PromptSession object
    """
    history_file = os.path.expanduser("~/.backtick_history")
    return PromptSession(
        completer=merged_completer,
        complete_style=CompleteStyle.MULTI_COLUMN,
        complete_while_typing=True,
        complete_in_thread=True,
        history=FileHistory(history_file),
        key_bindings=kb,
        style=Style.from_dict({
            'prompt': 'bold green',
            'completion': 'bg:#008800 #ffffff',
            'completion.cursor.current': 'bg:#00aaaa #000000',
        })
    )


def initialize_environment():
    """
    Sets up the environment by initializing completers, key bindings, and the prompt session.

    Returns:
        A configured PromptSession object
    """
    merged_completer = setup_completers()
    kb = setup_key_bindings()
    session = setup_prompt_session(merged_completer, kb)
    return session


def initialize_mvc():
    """
    Sets up the event dispatcher, model, view, and context for the application.

    Returns:
        A tuple containing the model, view, and context
    """
    event_dispatcher = EventDispatcher()
    model = StagedFiles()
    context = Context(event_dispatcher)
    view = TerminalView(context, model)

    # Map commands to the context
    context.map_command("ADD_FILE", AddFileCommand(model))
    context.map_command("ADD_DIRECTORY", AddDirectoryCommand(model, use_parallel=True, recursive=True))
    context.map_command("REMOVE", RemoveCommand(model))
    context.map_command("CLEAR_FILES", ClearFilesCommand(model))
    context.map_command("COPY_TO_CLIPBOARD", CopyToClipboardCommand(model))

    return model, view, context


def is_glob_pattern(user_input: str) -> bool:
    """
    Check if the user input is a glob pattern.

    Args:
        user_input: The user input to check

    Returns:
        True if the input contains glob pattern characters, False otherwise
    """
    # More robust glob pattern detection
    glob_chars = set('*?[]{}')
    return any(c in glob_chars for c in user_input)


def handle_glob_pattern(user_input: str, context: Context) -> None:
    """
    Handle glob patterns by expanding them and dispatching appropriate events.

    Args:
        user_input: The glob pattern to expand
        context: The application context for dispatching events
    """
    matched_paths = glob.glob(os.path.expanduser(user_input), recursive=True)
    if not matched_paths:
        print(f"No paths match the pattern '{user_input}'")
        return

    # Count files and directories
    file_count = 0
    dir_count = 0

    for matched_path in matched_paths:
        if os.path.isfile(matched_path):
            context.dispatch(Event("ADD_FILE", matched_path))
            file_count += 1
        elif os.path.isdir(matched_path):
            context.dispatch(Event("ADD_DIRECTORY", matched_path))
            dir_count += 1

    print(f"Added {file_count} files and {dir_count} directories matching '{user_input}'")


def handle_path_input(user_input: str, context: Context) -> None:
    """
    Handle user input for file or directory paths.

    Args:
        user_input: The path to process
        context: The application context for dispatching events
    """
    # Check if the input is a glob pattern
    if is_glob_pattern(user_input):
        handle_glob_pattern(user_input, context)
        return

    # Expand user directory if needed
    expanded_path = os.path.expanduser(user_input)

    # Check if it's a directory
    if os.path.isdir(expanded_path):
        context.dispatch(Event("ADD_DIRECTORY", expanded_path))
        return

    # Check if it's a file
    if os.path.isfile(expanded_path):
        context.dispatch(Event("ADD_FILE", expanded_path))
        return

    print(f"Error: Path '{user_input}' does not exist.")


def create_command_handlers(model: StagedFiles, view: TerminalView, context: Context):
    """
    Create a dictionary of command handlers.

    Args:
        model: The StagedFiles model
        view: The TerminalView
        context: The application context

    Returns:
        A dictionary mapping command strings to handler functions
    """
    handlers = {
        'q': lambda: False,  # Quit
        'h': lambda: view.show_help() or True,
        'l': lambda: view.list_files(model.files) or True,
        'c': lambda: context.dispatch(Event("CLEAR_FILES")) or True,
        '`': lambda: context.dispatch(Event("COPY_TO_CLIPBOARD")) or False,
    }

    return handlers


def handle_remove_command(args: str, model: StagedFiles, context: Context) -> bool:
    """
    Handle the remove command with arguments.

    Args:
        args: The arguments for the remove command (file index)
        model: The StagedFiles model
        context: The application context

    Returns:
        True to continue the application loop, False to exit
    """
    try:
        # Try to parse the index from the args
        index = int(args.strip())

        # Check if the index is valid
        if 0 < index <= len(model.files):
            file_to_remove = model.files[index - 1]
            context.dispatch(Event("REMOVE", file_to_remove))
        else:
            print(f"Error: Index {index} is out of range.")
    except ValueError:
        print(f"Error: Invalid index '{args}'. Please provide a number.")

    return True


def handle_user_input(user_input: str, model: StagedFiles, view: TerminalView, context: Context, handlers: Dict[str, Callable]) -> bool:
    """
    Process user input and dispatch appropriate commands.

    Args:
        user_input: The input from the user
        model: The StagedFiles model
        view: The TerminalView
        context: The application context
        handlers: Dictionary of command handlers

    Returns:
        True to continue the application loop, False to exit
    """
    # Check for empty input
    if not user_input:
        return True

    # Check for single-character commands
    if user_input in handlers:
        return handlers[user_input]()

    # Check for commands with arguments
    if user_input.startswith('r '):
        return handle_remove_command(user_input[2:], model, context)

    # Handle paths and glob patterns
    handle_path_input(user_input, context)
    return True


def main_loop():
    """
    Main application loop. Handles user input and dispatches commands.

    Returns:
        Exit code for the application
    """
    session = initialize_environment()
    model, view, context = initialize_mvc()
    handlers = create_command_handlers(model, view, context)

    view.show_help()

    while True:
        try:
            user_input = session.prompt(
                HTML("<ansigreen>backtick></ansigreen> "), complete_in_thread=True
            ).strip()

            if not handle_user_input(user_input, model, view, context, handlers):
                break

        except KeyboardInterrupt:
            print("\nUse 'q' to quit.")
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()

    return 0


def main():
    """
    Entry point for the backtick application.

    Returns:
        Exit code for the application
    """
    try:
        exit_code = main_loop()
        return exit_code
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())