"""
Tests for the utility functions in backtick/utils.py.
"""

from unittest.mock import patch, mock_open

import pytest

from backtick.utils import detect_file_type, FileType, ClipboardFormatter


class TestFileTypeDetection:
    """Tests for the file type detection functionality."""

    def test_detect_file_type_by_mime_text(self):
        """Test detecting a text file by mime type."""
        # Setup
        file_path = "test.txt"

        # Mock mimetypes to return a text mime type
        with patch("backtick.utils.mimetypes.guess_type", return_value=("text/plain", None)):
            # Execute
            result = detect_file_type(file_path)

            # Verify
            assert result == FileType.TEXT

    def test_detect_file_type_by_mime_binary(self):
        """Test detecting a binary file by mime type."""
        # Setup
        file_path = "test.png"

        # Test various binary mime types
        binary_mime_types = [
            ("image/png", None),
            ("application/octet-stream", None),
            ("video/mp4", None),
            ("audio/mpeg", None)
        ]

        for mime_type in binary_mime_types:
            # Mock mimetypes to return a binary mime type
            with patch("backtick.utils.mimetypes.guess_type", return_value=mime_type):
                # Execute
                result = detect_file_type(file_path)

                # Verify
                assert result == FileType.BINARY

    def test_detect_file_type_by_content_text(self):
        """Test detecting a text file by content analysis when mime type doesn't give a clear answer."""
        # Setup
        file_path = "test_file"

        # Mock mimetypes to return None (unknown)
        with patch("backtick.utils.mimetypes.guess_type", return_value=(None, None)):
            # Create text file content with no nulls or control chars
            text_content = "This is a text file\nwith multiple lines\nand no binary content."

            # Mock file open
            with patch("builtins.open", mock_open(read_data=text_content.encode())):
                # Execute
                result = detect_file_type(file_path)

                # Verify
                assert result == FileType.TEXT

    def test_detect_file_type_by_content_binary(self):
        """Test detecting a binary file by content analysis."""
        # Setup
        file_path = "test_binary"

        # Mock mimetypes to return None (unknown)
        with patch("backtick.utils.mimetypes.guess_type", return_value=(None, None)):
            # Create binary content with null bytes and control characters
            binary_content = bytes([0, 65, 0, 66, 1, 2, 3, 67])

            # Mock file open
            with patch("builtins.open", mock_open(read_data=binary_content)):
                # Execute
                result = detect_file_type(file_path)

                # Verify
                assert result == FileType.BINARY

    def test_detect_file_type_empty_file(self):
        """Test detecting an empty file."""
        # Setup
        file_path = "empty_file"

        # Mock mimetypes to return None (unknown)
        with patch("backtick.utils.mimetypes.guess_type", return_value=(None, None)):
            # Create empty file content
            empty_content = b''

            # Mock file open
            with patch("builtins.open", mock_open(read_data=empty_content)):
                # Execute
                result = detect_file_type(file_path)

                # Verify empty files are considered text
                assert result == FileType.TEXT

    def test_detect_file_type_error(self):
        """Test error handling when detecting file type."""
        # Setup
        file_path = "error_file"

        # Mock mimetypes to return None (unknown)
        with patch("backtick.utils.mimetypes.guess_type", return_value=(None, None)):
            # Mock file open to raise an exception
            with patch("builtins.open", side_effect=IOError("Test error")), \
                    patch("backtick.utils.logging.error") as mock_log_error:
                # Execute
                result = detect_file_type(file_path)

                # Verify
                assert result == FileType.UNKNOWN
                mock_log_error.assert_called_once()
                # Check that the error message contains the file path and exception
                assert file_path in mock_log_error.call_args[0][0]
                assert "Test error" in mock_log_error.call_args[0][0]


class TestClipboardFormatter:
    """Tests for the ClipboardFormatter class."""

    @pytest.fixture
    def formatter(self):
        """Fixture that returns a ClipboardFormatter instance."""
        return ClipboardFormatter(cache_size=3)  # Small cache for testing

    def test_init(self):
        """Test initialization with different cache sizes."""
        # Default cache size
        formatter = ClipboardFormatter()
        assert formatter.file_cache.maxsize == 50
        assert formatter.chunk_size == 4096

        # Custom cache size
        custom_formatter = ClipboardFormatter(cache_size=10, chunk_size=8192)
        assert custom_formatter.file_cache.maxsize == 10
        assert custom_formatter.chunk_size == 8192

    def test_read_file_in_chunks(self, formatter):
        """Test reading a file in chunks."""
        # Setup
        file_path = "test_file.txt"
        file_content = "This is a test file content."

        # Mock file open
        with patch("builtins.open", mock_open(read_data=file_content)):
            # Execute
            result = formatter._read_file_in_chunks(file_path)

            # Verify
            assert result == file_content

    def test_read_file_in_chunks_error(self, formatter):
        """Test error handling when reading a file."""
        # Setup
        file_path = "nonexistent_file.txt"

        # Mock file open to raise an exception
        with patch("builtins.open", side_effect=IOError("Test error")):
            # Execute
            result = formatter._read_file_in_chunks(file_path)

            # Verify
            assert "Error reading file: Test error" in result

    def test_format_files_empty(self, formatter):
        """Test formatting with an empty file list."""
        # Execute
        result = formatter.format_files([])

        # Verify
        assert result == ""

    def test_format_files_text(self, formatter):
        """Test formatting text files."""
        # Setup
        files = ["file1.py", "file2.txt"]

        # Mock file detection and reading
        with patch.object(formatter, "_read_file_in_chunks") as mock_read, \
                patch("backtick.utils.detect_file_type", return_value=FileType.TEXT), \
                patch("os.path.relpath", side_effect=lambda p: p):  # Return the same path

            # Configure the mock to return different content for each file
            mock_read.side_effect = ["print('Hello')", "This is text"]

            # Execute
            result = formatter.format_files(files)

            # Verify
            expected = 'file1.py\n\n```\nprint(\'Hello\')\n```\n\nfile2.txt\n\n```\nThis is text\n```'
            assert result == expected

            # Verify cache contains the files
            assert "file1.py" in formatter.file_cache
            assert "file2.txt" in formatter.file_cache

    def test_format_files_binary(self, formatter):
        """Test formatting with binary files."""
        # Setup
        files = ["image.png", "document.txt"]

        # Mock file detection to return binary for first file, text for second
        def mock_detect_side_effect(path):
            return FileType.BINARY if path == "image.png" else FileType.TEXT

        with patch("backtick.utils.detect_file_type", side_effect=mock_detect_side_effect), \
                patch.object(formatter, "_read_file_in_chunks", return_value="Text content"), \
                patch("os.path.relpath", side_effect=lambda p: p):  # Return the same path

            # Execute
            result = formatter.format_files(files)

            # Verify
            assert "image.png" in result
            assert "[BINARY FILE - CONTENT NOT SHOWN]" in result
            assert "document.txt" in result
            assert "Text content" in result

            # Verify only the text file is cached
            assert "image.png" not in formatter.file_cache
            assert "document.txt" in formatter.file_cache

    def test_format_files_unknown(self, formatter):
        """Test formatting with unknown file types."""
        # Setup
        files = ["unknown_file"]

        # Mock file detection to return unknown
        with patch("backtick.utils.detect_file_type", return_value=FileType.UNKNOWN), \
                patch("os.path.relpath", side_effect=lambda p: p):  # Return the same path

            # Execute
            result = formatter.format_files(files)

            # Verify
            assert "unknown_file" in result
            assert "[UNKNOWN FILE TYPE - CONTENT NOT SHOWN]" in result

            # Verify file is not cached
            assert "unknown_file" not in formatter.file_cache

    def test_format_files_error(self, formatter):
        """Test error handling during formatting."""
        # Setup
        files = ["error_file.txt"]

        # Make detect_file_type raise an exception
        with patch("backtick.utils.detect_file_type", side_effect=Exception("Test error")), \
                patch("os.path.relpath", side_effect=lambda p: p):  # Return the same path

            # Execute
            result = formatter.format_files(files)

            # Verify
            assert "Error reading error_file.txt:" in result
            assert "Test error" in result

    def test_format_files_caching(self, formatter):
        """Test that the file cache is used for subsequent reads."""
        # Setup
        files = ["file1.txt", "file2.txt"]

        # First call to populate cache
        with patch("backtick.utils.detect_file_type", return_value=FileType.TEXT), \
                patch.object(formatter, "_read_file_in_chunks") as mock_read, \
                patch("os.path.relpath", side_effect=lambda p: p):  # Return the same path

            mock_read.side_effect = ["Content 1", "Content 2"]
            formatter.format_files(files)

        # Second call should use cache
        with patch("backtick.utils.detect_file_type", return_value=FileType.TEXT), \
                patch.object(formatter, "_read_file_in_chunks") as mock_read, \
                patch("os.path.relpath", side_effect=lambda p: p):  # Return the same path

            # Execute
            formatter.format_files(files)

            # Verify the read method was NOT called again
            mock_read.assert_not_called()

    def test_format_files_lru_cache_behavior(self):
        """Test that the LRU cache evicts older entries when full."""
        # Setup a formatter with a small cache
        formatter = ClipboardFormatter(cache_size=2)

        # Add files to fill and exceed the cache
        files = ["file1.txt", "file2.txt", "file3.txt"]

        with patch("backtick.utils.detect_file_type", return_value=FileType.TEXT), \
                patch.object(formatter, "_read_file_in_chunks") as mock_read, \
                patch("os.path.relpath", side_effect=lambda p: p):  # Return the same path

            mock_read.side_effect = ["Content 1", "Content 2", "Content 3"]

            # Fill cache with first two files
            formatter.format_files(files[:2])

            # Verify cache state
            assert "file1.txt" in formatter.file_cache
            assert "file2.txt" in formatter.file_cache
            assert len(formatter.file_cache) == 2

            # Add third file, which should evict the least recently used
            formatter.format_files(files[2:])

            # Verify the oldest entry was evicted
            assert "file1.txt" not in formatter.file_cache
            assert "file2.txt" in formatter.file_cache
            assert "file3.txt" in formatter.file_cache
            assert len(formatter.file_cache) == 2

            # Reset the mock for the next test
            mock_read.reset_mock()
            mock_read.side_effect = ["Content 1"]

            # Now access file1 again, which should be re-read
            formatter.format_files(["file1.txt"])

            # Verify the read method was called for file1
            mock_read.assert_called_once_with("file1.txt")

    def test_clear_cache(self, formatter):
        """Test clearing the file cache."""
        # Setup - populate cache
        with patch("backtick.utils.detect_file_type", return_value=FileType.TEXT), \
                patch.object(formatter, "_read_file_in_chunks", return_value="Content"), \
                patch("os.path.relpath", side_effect=lambda p: p):  # Return the same path

            formatter.format_files(["file1.txt", "file2.txt"])

        # Verify cache state before clearing
        assert len(formatter.file_cache) == 2

        # Execute
        formatter.clear_cache()

        # Verify cache is empty
        assert len(formatter.file_cache) == 0