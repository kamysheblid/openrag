"""Tests for code processing and chunking"""

import pytest
from pathlib import Path

from openrag.indexer.processor import CodeProcessor


class TestCodeProcessor:
    """Test the CodeProcessor class"""
    
    def test_initialization(self, processor):
        """Processor initializes correctly"""
        assert processor.config is not None
        assert processor.logger is not None
        assert processor.gitignore_rules is not None
    
    def test_is_code_file(self, processor, temp_project):
        """Verify code file detection"""
        # Should detect code files
        assert processor.is_code_file(temp_project / "main.go") is True
        assert processor.is_code_file(temp_project / "frontend/App.jsx") is True
        assert processor.is_code_file(temp_project / "schema.sql") is True
        assert processor.is_code_file(temp_project / "README.md") is True
        
        # Should not detect non-code files
        not_code = temp_project / "not_code.txt"
        not_code.touch()
        assert processor.is_code_file(not_code) is False
        
        # Should not detect directories
        assert processor.is_code_file(temp_project / "frontend") is False
    
    def test_detect_language(self, processor):
        """Verify language detection from extensions"""
        test_cases = [
            ("file.go", "go"),
            ("file.js", "javascript"),
            ("file.jsx", "react"),
            ("file.ts", "typescript"),
            ("file.tsx", "react-typescript"),
            ("file.py", "python"),
            ("file.sql", "sql"),
            ("file.html", "html"),
            ("file.css", "css"),
            ("file.json", "json"),
            ("file.yml", "yaml"),
            ("file.md", "markdown"),
            ("file.unknown", "text"),
        ]
        
        for filename, expected in test_cases:
            assert processor.detect_language(Path(filename)) == expected
    
    def test_chunking_basic(self, processor):
        """Basic chunking functionality"""
        processor.config.chunk_size = 100
        processor.config.chunk_overlap = 20
        
        # Create content exactly 250 chars
        content = "a" * 250
        chunks = processor.chunk_content(content)
        
        # Should create 3 chunks (100 + 100 + 50)
        assert len(chunks) == 3
        assert len(chunks[0]) <= 100
        assert len(chunks[1]) <= 100
        assert len(chunks[2]) <= 50
    
    def test_chunking_with_overlap(self, processor):
        """Verify chunk overlap works"""
        processor.config.chunk_size = 50
        processor.config.chunk_overlap = 10
        
        content = "abcdefghijklmnopqrstuvwxyz" * 10
        chunks = processor.chunk_content(content)
        
        if len(chunks) > 1:
            # Check that chunks overlap
            chunk1_end = chunks[0][-10:]
            chunk2_start = chunks[1][:10]
            assert chunk1_end == chunk2_start
    
    def test_chunking_respects_newlines(self, processor):
        """Chunking should try to break at newlines"""
        processor.config.chunk_size = 30
        
        content = "line one\nline two\nline three\nline four\nline five"
        chunks = processor.chunk_content(content)
        
        # Each chunk should end with newline when possible
        for chunk in chunks[:-1]:  # Last chunk might not have newline
            if len(chunk) > 0:
                assert chunk.endswith('\n') or len(chunk) < processor.config.chunk_size
    
    def test_ignore_small_chunks(self, processor):
        """Chunks smaller than 50 chars should be ignored"""
        processor.config.chunk_size = 1000
        
        content = "tiny"
        chunks = processor.chunk_content(content)
        assert len(chunks) == 0
    
    def test_process_file(self, processor, temp_project):
        """Test processing a single file"""
        file_path = temp_project / "main.go"
        results = processor.process_file(file_path)
        
        assert results is not None
        assert len(results) > 0
        
        # Check first chunk
        chunk = results[0]
        assert "document" in chunk
        assert "metadata" in chunk
        assert "id" in chunk
        
        # Check metadata
        meta = chunk["metadata"]
        assert meta["source"] == "main.go"
        assert meta["language"] == "go"
        assert meta["extension"] == ".go"
        assert "chunk_index" in meta
        assert "total_chunks" in meta
    
    def test_process_binary_file(self, processor, temp_project):
        """Binary files should be skipped"""
        binary_file = temp_project / "binary.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\x04')
        
        results = processor.process_file(binary_file)
        assert results is None
    
    def test_gitignore_loading(self, processor, temp_project_with_gitignore):
        """Gitignore rules should be loaded"""
        processor.config.project_root = temp_project_with_gitignore
        processor._load_gitignore_rules()
        
        assert len(processor.gitignore_rules) > 0
    
    def test_gitignore_respect(self, processor, temp_project_with_gitignore):
        """Files in .gitignore should be ignored"""
        processor.config.project_root = temp_project_with_gitignore
        processor._load_gitignore_rules()
        
        # Should not ignore code files
        assert processor.should_ignore(temp_project_with_gitignore / "main.go") is False
        assert processor.should_ignore(temp_project_with_gitignore / "frontend/App.jsx") is False
        
        # Should ignore files in .gitignore
        assert processor.should_ignore(temp_project_with_gitignore / "secrets.txt") is True
        assert processor.should_ignore(temp_project_with_gitignore / "node_modules/dummy.txt") is True
        assert processor.should_ignore(temp_project_with_gitignore / "dist/output.exe") is True
        assert processor.should_ignore(temp_project_with_gitignore / "frontend/.next/cache.txt") is True
    
    def test_exclude_dirs_config(self, processor, temp_project):
        """Config exclude_dirs should be respected"""
        processor.config.exclude_dirs.add("frontend")
        
        code_file = temp_project / "frontend/App.jsx"
        assert processor.should_ignore(code_file) is True
    
    def test_exclude_files_pattern(self, processor, temp_project):
        """Config exclude_files patterns should be respected"""
        processor.config.exclude_files.add("*.jsx")
        
        code_file = temp_project / "frontend/App.jsx"
        assert processor.should_ignore(code_file) is True
    
    def test_large_file_processing(self, processor, temp_large_file):
        """Large files should be processed without memory issues"""
        results = processor.process_file(temp_large_file)
        
        assert results is not None
        assert len(results) > 5  # Should create multiple chunks
