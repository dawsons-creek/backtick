# Backtick

A command-line tool that collects file contents and combines them into one long string formatted for the clipboard. Ideal for quickly gathering context for LLMs or sharing code snippets.

## Features

-   **Interactive Shell:** Provides a user-friendly interface (`backtick` command) for staging files.
-   **Command Alias:** Offers a shorter alias (`bt`) for potentially non-interactive use or quicker access (details depend on `backtick.cli` implementation).
-   **Flexible Staging:** Add individual files, entire directories (recursively by default), or use shell-supported glob patterns (e.g., `*.py`) to add multiple files.
-   **Ignore File Support:** Automatically filters files and directories based on `.backtickignore` patterns using `.gitignore` syntax, powered by the `pathspec` library.
-   **Ignore-Aware Tab Completion:** File and directory path completion in the interactive shell intelligently hides ignored items.
-   **Reactive State Management:** Uses `swallow-framework` for efficient internal state updates.
-   **Clipboard Integration:** Copies the formatted content of all staged files to the clipboard using `pyperclip`.
-   **Status Feedback:** Provides clear messages for added, removed, skipped, or cleared files.

## Installation

This package is installed directly from its GitHub repository.

```bash
# Install the latest version from the main branch on GitHub
pip install git+[https://github.com/dawsons-creek/backtick.git](https://github.com/dawsons-creek/backtick.git)

# Or, to install a specific version/tag (e.g., v0.1.0):
# pip install git+[https://github.com/dawsons-creek/backtick.git@v0.1.0](https://github.com/dawsons-creek/backtick.git@v0.1.0)
```

## Usage

### Interactive Shell

Run the `backtick` command to start the interactive session:

```bash
backtick
```

**Commands:**

-   `<file_path>` - Add a specific file to the staged list.
-   `<directory_path>` - Add all non-ignored files within a directory (recursively).
-   `<glob_pattern>` - Add files matching a shell glob pattern (e.g., `src/**/*.py`).
-   `l` - List all currently staged files with their index numbers.
-   `r <index>` - Remove a file from the list using its index number.
-   `c` - Clear all files from the staged list.
-   `h` - Show the help message summarizing commands.
-   `q` - Quit the program without copying.
-   `` ` `` (Backtick character) - Format and copy the content of all staged files to the clipboard, then quit.

### Command Line Alias

The `bt` command provides an alternative entry point (its specific arguments and behavior are defined in `backtick.cli`).

```bash
# Example (hypothetical - depends on cli.py implementation)
bt file1.py src/
```

### Example Workflow (Interactive Shell)

```bash
# Start backtick
$ backtick

# Add specific files
backtick> app.py
Added app.py to staged files.

# Add a directory
backtick> lib/
Added 5 files from directory 'lib/'.

# Add files using a glob (if your shell supports it)
backtick> tests/*.py
Added 3 files matching 'tests/*.py'.

# List staged files
backtick> l

Staged Files (9 total):
1. app.py
2. lib/utils.py
3. lib/models.py
4. lib/views.py
5. lib/commands.py
6. tests/test_app.py
7. tests/test_utils.py
8. tests/conftest.py
9. README.md

# Remove a file by index
backtick> r 9
File removed: README.md

# Copy to clipboard and exit
backtick> `
Formatting files for clipboard...
Copying to clipboard...
Copied 8 file(s) to clipboard.
```

## Ignoring Files

Create a `.backtickignore` file in your project's root directory (or the directory where you run `backtick`) to specify files or patterns to ignore. The syntax is the same as `.gitignore`.

```
# Example .backtickignore

# Ignore virtual environment directories
venv/
.venv/

# Ignore compiled Python files
*.pyc
__pycache__/

# Ignore build artifacts
build/
dist/
*.egg-info/

# Ignore logs and specific config
*.log
secrets.json
```

## Development

### Setup

```bash
# Clone the repository
git clone [https://github.com/dawsons-creek/backtick.git](https://github.com/dawsons-creek/backtick.git)
cd backtick

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with development dependencies
pip install -e ".[dev]"
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=backtick

# Run linting and type checking
black backtick tests
isort backtick tests
mypy backtick
```

## License

This project is licensed under the MIT License - see the `LICENSE` file (or `pyproject.toml`) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request to the `dawsons-creek/backtick` repository.

1.  Fork the repository (`https://github.com/dawsons-creek/backtick`).
2.  Create your feature branch (`git checkout -b feature/your-amazing-feature`).
3.  Commit your changes (`git commit -am 'Add some amazing feature'`).
4.  Push to the branch (`git push origin feature/your-amazing-feature`).
5.  Open a Pull Request.
```
