"""Basic smoke tests for core functionality"""

import pytest
from pathlib import Path

from openrag.config import OpenRAGConfig


class TestBasic:
    """Verify basic configuration and setup"""
    
    def test_config_defaults(self):
        """Config has sensible defaults"""
        config = OpenRAGConfig()
        
        # Core settings
        assert config.chroma_port == 8001
        assert config.query_port == 8765
        assert config.collection_name == "code_rag"
        
        # Exclusions
        assert ".git" in config.exclude_dirs
        assert "node_modules" in config.exclude_dirs
        assert "__pycache__" in config.exclude_dirs
        assert "*.pyc" in config.exclude_files
        assert ".DS_Store" in config.exclude_files
        
        # Chunking
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.batch_size == 100
        
        # Default true
        assert config.recursive is True
        assert config.ignore_hidden is True
    
    def test_config_path_creation(self, tmp_path):
        """Config creates directories automatically"""
        config = OpenRAGConfig()
        config.data_dir = tmp_path / ".openrag" / "data"
        config.logs_dir = tmp_path / ".openrag" / "logs"
        
        # Directories shouldn't exist yet
        assert not config.data_dir.exists()
        assert not config.logs_dir.exists()
        
        # __post_init__ should create them
        config.__post_init__()
        
        assert config.data_dir.exists()
        assert config.logs_dir.exists()
        assert (config.logs_dir / "chroma").exists()
        assert (config.logs_dir / "indexer").exists()
        assert (config.logs_dir / "query").exists()
    
    def test_config_save_load(self, tmp_path):
        """Config save and load works"""
        config = OpenRAGConfig()
        config.collection_name = "test_collection"
        config.chunk_size = 1500
        config.exclude_dirs = {".git", "node_modules", "custom"}
        
        config_path = tmp_path / "config.json"
        config.save(config_path)
        
        loaded = OpenRAGConfig.load(config_path)
        
        assert loaded.collection_name == "test_collection"
        assert loaded.chunk_size == 1500
        assert "custom" in loaded.exclude_dirs
        assert ".git" in loaded.exclude_dirs
    
    def test_version(self):
        """Verify version string exists"""
        from openrag import __version__
        assert isinstance(__version__, str)
        assert len(__version__) > 0
