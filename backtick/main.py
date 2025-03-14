#!/usr/bin/env python3
"""
Backtick Interactive Shell - A terminal app for staging files and copying to clipboard

Usage:
- Type a file or directory path to stage it
- Type a glob pattern to stage multiple files (e.g., *.py)
- Type ` and press Enter to copy all staged files to the clipboard
- Type 'list' to show staged files
- Type 'clear' to clear staged files
- Type 'ignore' to show ignore patterns
- Type 'exit' or 'quit' to exit
"""

import glob
import os

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
    commands = ['`', 'c', 'l', 'q', 'r', 'h']
    command_completer = WordCompleter(commands)
    path_completer = IgnoreAwarePathCompleter(expanduser=True)
    return merge_completers([command_completer, path_completer])


def setup_key_bindings():
    kb = KeyBindings()

    @kb.add('c-x')
    def show_cwd(event):
        event.app.current_buffer.insert_text(f"# CWD: {os.getcwd()}")

    @kb.add(Keys.Tab)
    def _(event):
        if event.app.current_buffer.complete_state:
            event.app.current_buffer.complete_next()
        else:
            buff = event.app.current_buffer
            if buff.text:
                buff.start_completion()

    return kb


def setup_prompt_session(merged_completer, kb):
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
    """
    merged_completer = setup_completers()
    kb = setup_key_bindings()
    session = setup_prompt_session(merged_completer, kb)
    return session


def initialize_mvc():
    """
    Sets up the event dispatcher, model, view, and context for the application.
    """
    event_dispatcher = EventDispatcher()
    model = StagedFiles()
    context = Context(event_dispatcher)
    view = TerminalView(context, model)

    # Map commands to the context
    context.map_command("ADD_FILE", AddFileCommand(model))
    context.map_command("ADD_DIRECTORY", AddDirectoryCommand(model))
    context.map_command("REMOVE", RemoveCommand(model))
    context.map_command("CLEAR_FILES", ClearFilesCommand(model))
    context.map_command("COPY_TO_CLIPBOARD", CopyToClipboardCommand(model))

    return model, view, context



def handle_user_input(user_input, model, view, context):
    """
    Processes the user input and dispatches the appropriate commands or actions.
    """
    if user_input == 'q':
        print("Goodbye!")
        return False
    elif user_input == 'h':
        view.show_help()
    elif user_input == 'l':
        view.list_files(model.files)
    elif user_input == 'c':
        context.dispatch(Event("CLEAR_FILES"))
    elif user_input.startswith('r '):
        handle_remove_command(user_input, model, context)
    elif user_input == '`':
        context.dispatch(Event("COPY_TO_CLIPBOARD"))
        return False
    elif user_input:
        handle_path_input(user_input, context)
    return True


def handle_remove_command(user_input, model, context):
    """
    Handles the 'remove' command by parsing the index and dispatching the REMOVE event.
    """
    try:
        index = int(user_input.split()[1]) - 1
        if 0 <= index < len(model.files):
            file_to_remove = model.files[index]
            context.dispatch(Event("REMOVE", file_to_remove))
        else:
            print(f"Error: Index '{index + 1}' is out of range.")
    except (ValueError, IndexError):
        print("Error: Invalid index for remove command.")


def handle_path_input(user_input, context):
    """
    Handles user input that specifies a file, directory, or glob pattern.
    """
    if is_glob_pattern(user_input):
        handle_glob_pattern(user_input, context)
        return

    if os.path.isdir(user_input):
        context.dispatch(Event("ADD_DIRECTORY", user_input))
        return

    if os.path.isfile(user_input):
        context.dispatch(Event("ADD_FILE", user_input))
        return

    print(f"Error: Path '{user_input}' does not exist.")


def is_glob_pattern(user_input):
    """
    Checks if the user input contains a glob pattern.
    """
    return '*' in user_input or '?' in user_input


def handle_glob_pattern(user_input, context):
    """
    Handles glob patterns by matching paths and dispatching events for files or directories.
    """
    matched_paths = glob.glob(os.path.expanduser(user_input))
    if not matched_paths:
        print(f"No paths match the pattern '{user_input}'")
        return

    for matched_path in matched_paths:
        if os.path.isfile(matched_path):
            context.dispatch(Event("ADD_FILE", matched_path))
        elif os.path.isdir(matched_path):
            context.dispatch(Event("ADD_DIRECTORY", matched_path))

    print(f"Added {len(matched_paths)} paths matching '{user_input}'")


def main_loop():
    """
    Main loop of the application. Handles user input and dispatches commands.
    """
    session = initialize_environment()
    model, view, context = initialize_mvc()

    view.show_help()

    while True:
        try:
            user_input = session.prompt(
                HTML("<ansigreen>backtick></ansigreen> "), complete_in_thread=True
            ).strip()
            if not handle_user_input(user_input, model, view, context):
                break
        except KeyboardInterrupt:
            print("\nUse 'q' to quit.")
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")


def main():
    main_loop()


if __name__ == "__main__":
    main()

