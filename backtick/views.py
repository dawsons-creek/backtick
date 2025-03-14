from contextlib import contextmanager
from swallow_framework import View, Context
from backtick.models import StagedFiles


class TerminalView(View):
    """Represents the user interface for the staged files app."""

    def __init__(self, context: Context, model: StagedFiles):
        """Initializes the TerminalView and auto-watches the model."""
        super().__init__(context)  # Make sure to call parent constructor
        self.model = model

        # Watch for changes to the files property using the cleaner API
        self.model.files.on_change(self.update)

        # Initial update
        self.update(model.files)

    def show_help(self) -> None:
        """Displays the menu and handles user input."""
        with self.print_message():
            print("Type a file or directory name and hit enter to add it to the staged files.\n")
            print("'l' list: List all staged files.")
            print("'r' remove <index>: Remove a file/directory from the staged files.")
            print("'c' clear: Clear all staged files.")
            print("'h' show this help message.")
            print("'q' quit the program.")

    def update(self, files: list) -> None:
        """Updates the view when the model changes."""
        self.list_files(files)

    def list_files(self, files: list) -> None:
        """Displays the list of staged files."""
        with self.print_message():
            if not files:
                print("No files are staged.")
            else:
                print("\nStaged Files:")
                for i, file in enumerate(files, 1):
                    print(f"{i}. {file}")

    @contextmanager
    def print_message(self) -> None:
        """Prints a message to the user."""
        yield
        print("\n")

