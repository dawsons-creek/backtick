# Backtick

A command-line tool that collects file contents and combines them into one long string on the clipboard. Perfect for sharing code snippets or documentation with others.

## Features

- Stage individual files or entire directories
- Use glob patterns to add multiple files at once
- Automatic filtering based on `.backtickignore` patterns (gitignore syntax)
- Efficient memory usage with chunk-based file reading and LRU caching
- Binary file detection to avoid binary content in the clipboard
- Tab completion for file paths and commands
- Concurrent processing for faster directory scanning

## Installation

```bash
# Install from PyPI
pip install backtick

# Or install directly from GitHub
pip install git+https://github.com/rocket-tycoon/backtick.git
```

## Usage

Run the `backtick` command to start the interactive shell:

```bash
backtick
```

### Commands

- `<file_path>` - Add a file to the staged list
- `<directory_path>` - Add all files in a directory (recursively)
- `<glob_pattern>` - Add files matching a glob pattern (e.g., *.py)
- `l` - List all staged files
- `r <index>` - Remove a file by index
- `c` - Clear all staged files
- `h` - Show help message
- `q` - Quit the program
- `` ` `` - Copy all staged files to clipboard and quit

### Example Workflow

```bash
# Start backtick
$ backtick

# Add specific files
backtick> app.py
Added app.py to staged files.

# Add a directory
backtick> lib/
Added 5 files from directory 'lib/'.

# Add all Python files
backtick> *.py
Added 3 files matching '*.py'.

# List staged files
backtick> l

Staged Files (9 total):
1. app.py
2. lib/utils.py
3. lib/models.py
4. lib/views.py
5. lib/commands.py
6. test_app.py
7. README.md
8. setup.py
9. requirements.txt

# Remove a file
backtick> r 9
File removed: requirements.txt

# Copy to clipboard and exit
backtick> `
Formatting files for clipboard...
Copying to clipboard...
Copied 8 file(s) to clipboard.
```

## Ignoring Files

Create a `.backtickignore` file in your project directory to specify files or patterns to ignore. This file uses the same syntax as `.gitignore`:

```
# Ignore all logs
*.log

# Ignore the venv directory
venv/

# Ignore all .pyc files
*.pyc

# Ignore specific files
secrets.json
```

## Performance Optimization

Backtick includes several optimizations for handling large codebases:

1. **Memory-efficient reading**: Files are read in chunks to avoid loading everything into memory at once
2. **LRU caching**: Recently used files are cached, but the cache has a size limit
3. **Binary file detection**: Binary files are automatically identified and excluded from text processing
4. **Parallel processing**: Directory scanning uses multiple threads for better performance
5. **Batch updates**: Changes to the file list are batched for better UI responsiveness

## Configuration

Backtick reads its configuration from the following files:

- `.backtickignore` - Contains patterns for files to ignore
- `~/.backtick_history` - Command history for the interactive shell

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/rocket-tycoon/backtick.git
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

# Run linting
black backtick tests
isort backtick tests
mypy backtick
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request