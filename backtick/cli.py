"""
Command-line interface for the backtick tool.

This module provides a non-interactive CLI interface for backtick.
"""

import argparse
import os
import sys
from typing import List, Optional

from backtick.commands import (
    AddFileCommand,
    AddDirectoryCommand,
    CopyToClipboardCommand
)
from backtick.models import StagedFiles
from swallow_framework import EventDispatcher, Event, Context


def parse_args():
    """
    Parse command-line arguments.

    Returns:
        The parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Collect file contents and combine them into clipboard content."
    )

    # Add arguments
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to include"
    )
    parser.add_argument(
        "-n", "--no-recursive",
        action="store_true",
        help="Disable recursive processing of directories (default is recursive)"
    )
    parser.add_argument(
        "-i", "--ignore-file",
        default=".backtickignore",
        help="Path to the ignore file (default: .backtickignore)"
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the combined content instead of copying to clipboard"
    )
    parser.add_argument(
        "-o", "--output",
        help="Write output to a file instead of the clipboard"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    return parser.parse_args()


def cli():
    """
    Execute the CLI version of backtick.

    Returns:
        Exit code for the application
    """
    args = parse_args()

    # Create a model and context
    event_dispatcher = EventDispatcher()
    model = StagedFiles(ignore_file_path=args.ignore_file)
    context = Context(event_dispatcher)

    # Map commands
    add_file_cmd = AddFileCommand(model)
    add_dir_cmd = AddDirectoryCommand(model, use_parallel=True, recursive=not args.no_recursive)
    copy_cmd = CopyToClipboardCommand(model)

    context.map_command("ADD_FILE", add_file_cmd)
    context.map_command("ADD_DIRECTORY", add_dir_cmd)
    context.map_command("COPY_TO_CLIPBOARD", copy_cmd)

    # Process the provided paths
    if not args.paths:
        print("Error: No files or directories specified.")
        return 1

    # Add files and directories
    for path in args.paths:
        if os.path.isfile(path):
            if args.verbose:
                print(f"Adding file: {path}")
            context.dispatch(Event("ADD_FILE", path))
        elif os.path.isdir(path):
            if args.verbose:
                print(f"Adding directory: {path}")
            context.dispatch(Event("ADD_DIRECTORY", path))
        else:
            print(f"Warning: Path not found: {path}")

    # Get the total number of files
    file_count = model.get_file_count()

    if file_count == 0:
        print("No files were staged. Nothing to copy.")
        return 1

    # Copy to clipboard or file
    if args.output:
        # Format the files
        content = copy_cmd.formatter.format_files(model.files)

        # Write to file
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Wrote content of {file_count} file(s) to {args.output}")
        except Exception as e:
            print(f"Error writing to {args.output}: {str(e)}")
            return 1
    elif args.print:
        # Format and print the files
        content = copy_cmd.formatter.format_files(model.files)
        print(content)
    else:
        # Copy to clipboard
        context.dispatch(Event("COPY_TO_CLIPBOARD"))

    return 0


def main():
    """
    Main entry point for the CLI.

    Returns:
        Exit code for the application
    """
    try:
        return cli()
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 130
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())