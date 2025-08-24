"""
Tests for filesystem operations with sandbox protection.
"""

import pytest
import tempfile
import os
from pathlib import Path
from ateam.tools.builtin.fs import read_file, write_file, list_dir, stat_file


class TestFilesystemOperations:
    """Test filesystem operations with sandbox protection."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_read_file_success(self, temp_dir):
        """Test successful file read within sandbox."""
        # Create a test file
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Hello, World!")
        
        result = read_file("test.txt", temp_dir)
        assert result.ok
        assert result.value == "Hello, World!"
    
    def test_read_file_not_found(self, temp_dir):
        """Test file read when file doesn't exist."""
        result = read_file("nonexistent.txt", temp_dir)
        assert not result.ok
        assert result.error.code == "fs.not_found"
    
    def test_read_file_outside_sandbox(self, temp_dir):
        """Test file read outside sandbox is denied."""
        result = read_file("../../../etc/passwd", temp_dir)
        assert not result.ok
        assert result.error.code == "fs.access_denied"
    
    def test_write_file_success(self, temp_dir):
        """Test successful file write within sandbox."""
        result = write_file("test.txt", "Hello, World!", temp_dir)
        assert result.ok
        
        # Verify file was written
        test_file = Path(temp_dir) / "test.txt"
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"
    
    def test_write_file_creates_directories(self, temp_dir):
        """Test file write creates parent directories."""
        result = write_file("subdir/test.txt", "Hello, World!", temp_dir)
        assert result.ok
        
        # Verify directory and file were created
        test_file = Path(temp_dir) / "subdir" / "test.txt"
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"
    
    def test_write_file_outside_sandbox(self, temp_dir):
        """Test file write outside sandbox is denied."""
        result = write_file("../../../etc/test.txt", "Hello", temp_dir)
        assert not result.ok
        assert result.error.code == "fs.access_denied"
    
    def test_list_dir_success(self, temp_dir):
        """Test successful directory listing within sandbox."""
        # Create test files and directories
        (Path(temp_dir) / "file1.txt").write_text("content1")
        (Path(temp_dir) / "file2.txt").write_text("content2")
        (Path(temp_dir) / "subdir").mkdir()
        (Path(temp_dir) / "subdir" / "file3.txt").write_text("content3")
        
        result = list_dir(".", temp_dir)
        assert result.ok
        
        entries = result.value
        assert len(entries) == 3  # file1.txt, file2.txt, subdir (not the file inside subdir)
        
        # Check file entries
        file1 = next(e for e in entries if e["name"] == "file1.txt")
        assert file1["is_file"]
        assert file1["size"] == 8
        
        file2 = next(e for e in entries if e["name"] == "file2.txt")
        assert file2["is_file"]
        assert file2["size"] == 8
        
        # Check directory entry
        subdir = next(e for e in entries if e["name"] == "subdir")
        assert subdir["is_dir"]
        assert subdir["size"] is None
        
        # Test listing the subdirectory
        result = list_dir("subdir", temp_dir)
        assert result.ok
        subdir_entries = result.value
        assert len(subdir_entries) == 1
        
        file3 = subdir_entries[0]
        assert file3["name"] == "file3.txt"
        assert file3["is_file"]
        assert file3["size"] == 8
    
    def test_list_dir_not_found(self, temp_dir):
        """Test directory listing when directory doesn't exist."""
        result = list_dir("nonexistent", temp_dir)
        assert not result.ok
        assert result.error.code == "fs.not_found"
    
    def test_list_dir_not_directory(self, temp_dir):
        """Test directory listing when path is not a directory."""
        # Create a file
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("content")
        
        result = list_dir("test.txt", temp_dir)
        assert not result.ok
        assert result.error.code == "fs.not_directory"
    
    def test_list_dir_outside_sandbox(self, temp_dir):
        """Test directory listing outside sandbox is denied."""
        result = list_dir("../../../etc", temp_dir)
        assert not result.ok
        assert result.error.code == "fs.access_denied"
    
    def test_stat_file_success(self, temp_dir):
        """Test successful file stats within sandbox."""
        # Create a test file
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Hello, World!")
        
        result = stat_file("test.txt", temp_dir)
        assert result.ok
        
        stats = result.value
        assert stats["name"] == "test.txt"
        assert stats["is_file"]
        assert stats["size"] == 13
        assert "permissions" in stats
        assert "owner_readable" in stats
        assert "owner_writable" in stats
    
    def test_stat_directory_success(self, temp_dir):
        """Test successful directory stats within sandbox."""
        # Create a test directory
        test_dir = Path(temp_dir) / "testdir"
        test_dir.mkdir()
        
        result = stat_file("testdir", temp_dir)
        assert result.ok
        
        stats = result.value
        assert stats["name"] == "testdir"
        assert stats["is_dir"]
        assert stats["size"] is None
    
    def test_stat_file_not_found(self, temp_dir):
        """Test file stats when file doesn't exist."""
        result = stat_file("nonexistent.txt", temp_dir)
        assert not result.ok
        assert result.error.code == "fs.not_found"
    
    def test_stat_file_outside_sandbox(self, temp_dir):
        """Test file stats outside sandbox is denied."""
        result = stat_file("../../../etc/passwd", temp_dir)
        assert not result.ok
        assert result.error.code == "fs.access_denied"
    
    def test_sandbox_protection_symlinks(self, temp_dir):
        """Test that symlinks don't bypass sandbox protection."""
        # Create a symlink pointing outside the sandbox
        if os.name != 'nt':  # Skip on Windows
            outside_file = Path(temp_dir).parent / "outside.txt"
            outside_file.write_text("outside content")
            
            symlink = Path(temp_dir) / "link.txt"
            symlink.symlink_to(outside_file)
            
            # Reading through symlink should be denied
            result = read_file("link.txt", temp_dir)
            assert not result.ok
            assert result.error.code == "fs.access_denied"
    
    def test_write_file_append_mode(self, temp_dir):
        """Test file write in append mode."""
        # Write initial content
        result = write_file("test.txt", "Hello", temp_dir)
        assert result.ok
        
        # Append additional content
        result = write_file("test.txt", ", World!", temp_dir, mode="a")
        assert result.ok
        
        # Verify combined content
        test_file = Path(temp_dir) / "test.txt"
        assert test_file.read_text() == "Hello, World!"
