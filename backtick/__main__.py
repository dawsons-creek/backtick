#!/usr/bin/env python3
"""
Main entry point for the backtick package.

This module handles command-line arguments and dispatches to the appropriate mode
(interactive shell, CLI, or MCP server).
"""

import sys


def main() -> int:
    """
    Main entry point for backtick.
    Dispatches to the appropriate mode based on command-line arguments.

    Returns:
        Exit code for the application
    """

    # Check if we have arguments (CLI mode) or not (interactive mode)
    if len(sys.argv) > 1:
        # CLI mode
        from backtick.cli import main as cli_main
        return cli_main()
    else:
        # Interactive mode
        from backtick.main import main as interactive_main
        return interactive_main()


if __name__ == "__main__":
    sys.exit(main())
