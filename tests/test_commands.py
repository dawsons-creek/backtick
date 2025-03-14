import os
import os
from unittest.mock import patch

import pytest
from backtick.commands import AddFileCommand, AddDirectoryCommand
from backtick.models import StagedFiles


@pytest.fixture
def staged_files():
    return StagedFiles()

@pytest.fixture
def add_file_command(staged_files):
    return AddFileCommand(staged_files)

@pytest.fixture
def add_directory_command(staged_files):
    return AddDirectoryCommand(staged_files)

def test_add_file_to_staged_files(add_file_command, staged_files):
    test_file = "test_file.txt"
    staged_files.base_dir = os.getcwd()
    staged_files.ignore_handler = MockIgnoreHandler(False)  # Always allow adding files

    add_file_command.execute(test_file)

    assert os.path.relpath(test_file, staged_files.base_dir) in staged_files.files

def test_add_directory_with_files(add_directory_command, staged_files):
    test_dir = "test_folder"
    staged_files.base_dir = os.getcwd()
    staged_files.ignore_handler = MockIgnoreHandler(False)

    with patch("os.walk") as mock_walk:
        mock_walk.return_value = [
            (os.path.join(staged_files.base_dir, test_dir), ("subdir",), ("file1.txt", "file2.txt")),
            (os.path.join(staged_files.base_dir, test_dir, "subdir"), (), ("file3.txt",)),
        ]

        add_directory_command.execute(test_dir)

    assert os.path.relpath(os.path.join(test_dir, "file1.txt"), staged_files.base_dir) in staged_files.files
    assert os.path.relpath(os.path.join(test_dir, "file2.txt"), staged_files.base_dir) in staged_files.files
    assert os.path.relpath(os.path.join(test_dir, "subdir", "file3.txt"), staged_files.base_dir) in staged_files.files

def test_add_directory_with_no_files(add_directory_command, staged_files):
    test_dir = "empty_folder"
    staged_files.base_dir = os.getcwd()
    staged_files.ignore_handler = MockIgnoreHandler(False)

    with patch("os.walk") as mock_walk:
        mock_walk.return_value = [(os.path.join(staged_files.base_dir, test_dir), (), ())]

        add_directory_command.execute(test_dir)

    assert len(staged_files.files) == 0

def test_add_directory_with_ignored_files(add_directory_command, staged_files):
    test_dir = "ignored_folder"
    staged_files.base_dir = os.getcwd()
    staged_files.ignore_handler = MockIgnoreHandler(True)  # Always ignore files

    with patch("os.walk") as mock_walk:
        mock_walk.return_value = [
            (os.path.join(staged_files.base_dir, test_dir), (), ("file1.txt", "file2.txt")),
        ]

        add_directory_command.execute(test_dir)

    assert len(staged_files.files) == 0

# Mock class for IgnoreHandler
class MockIgnoreHandler:
    def __init__(self, ignore_value):
        self._ignore_value = ignore_value

    def should_ignore(self, file_path):
        return self._ignore_value


def test_add_existing_file_does_not_duplicate(add_file_command, staged_files):
    test_file = "existing_file.txt"
    staged_files.base_dir = os.getcwd()
    staged_files.ignore_handler = MockIgnoreHandler(False)
    staged_files.files.append(os.path.relpath(test_file, staged_files.base_dir))

    add_file_command.execute(test_file)

    assert staged_files.files.count(os.path.relpath(test_file, staged_files.base_dir)) == 1


def test_add_ignored_file_is_skipped(add_file_command, staged_files):
    test_file = "ignored_file.txt"
    staged_files.base_dir = os.getcwd()
    staged_files.ignore_handler = MockIgnoreHandler(True)  # Always ignore files

    add_file_command.execute(test_file)

    assert os.path.relpath(test_file, staged_files.base_dir) not in staged_files.files


# Mock class for IgnoreHandler
class MockIgnoreHandler:
    def __init__(self, ignore_value):
        self._ignore_value = ignore_value  # Rename to avoid conflict

    def should_ignore(self, file_path):
        return self._ignore_value
