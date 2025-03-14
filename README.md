# Backtick

A command line tool that processes text by executing shell commands enclosed in backticks.

## Installation

### Prerequisites

- Python 3.12 or higher
- Git (for installation from source)

### Using uv (Recommended)

```bash
# Create a virtual environment with Python 3.12
uv venv --python=3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install backtick
uv pip install backtick
```

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/backtick.git
cd backtick

# Create a virtual environment with Python 3.12
uv venv --python=3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e ".[dev]"
```

### Dependencies

Backtick depends on:
- click - Command line interface
- rich - Rich terminal output
- prompt-toolkit - Interactive shell functionality
- pyperclip - Clipboard integration
- swallow-framework - Additional functionality (optional)

## Usage

### Basic Usage

```bash
backtick run "Today's date is `date`"
```

Output:
```
Today's date is Wed Mar 12 14:30:45 UTC 2025
```

### Process a File

```bash
backtick run -f input.txt -o output.txt
```

### Copy to Clipboard

```bash
backtick run -c "The current directory has `ls -la | wc -l` entries"
```

### Verbose Mode

To see error messages from failed commands:

```bash
backtick run -v "The command `invalid-command` failed"
```

### Interactive Shell

Start an interactive shell where you can type and evaluate commands on-the-fly:

```bash
backtick shell
```

In the shell, you can use these special commands:
- `:copy` - Copy the last result to clipboard
- `:verbose` - Toggle verbose mode
- `:clear` - Clear the screen
- `:exit` - Exit the shell (or press Ctrl+D)

### Todo Application

Backtick includes a Todo application built with the Swallow Framework:

```bash
backtick todo
```

This launches an interactive Todo application with the following features:
- Add, remove, and toggle completion of todo items
- Filter between all items and active items only
- View statistics about your todo list

## Examples

### Basic Text Processing

```bash
backtick run "There are `ls -1 | wc -l` files in the current directory."
```

### Multiple Commands

```bash
backtick run "System info: `uname -a`, with `free -h | grep Mem | awk '{print $3}'` memory used."
```

### Process Files

Create a file template.txt:
```
Hostname: `hostname`
Current user: `whoami`
Date: `date`
Uptime: `uptime`
```

Process it:
```bash
backtick run -f template.txt -o system_info.txt
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/backtick.git
cd backtick

# Create and activate virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
uv pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black backtick tests
isort backtick tests
```

### Type Checking

```bash
mypy backtick
```

## License

MIT