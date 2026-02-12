"""Tests for file system watcher"""

import pytest
import time
from pathlib import Path

from openrag.indexer.watcher import FileWatcher, CodeIndexerHandler


@pytest.mark.usefixtures("running_chromadb")
class TestFileWatcher:
    """Test file system watching functionality"""
    
    def test_handler_initialization(self, test_config, logger, chroma_manager):
        """Test handler initialization"""
        handler = CodeIndexerHandler(test_config, logger, chroma_manager)
        assert handler.processor is not None
        assert handler.collection_manager is not None
        assert handler.stats["indexed"] == 0
    
    def test_index_file(self, test_config, logger, chroma_manager, temp_project):
        """Test indexing a single file"""
        handler = CodeIndexerHandler(test_config, logger, chroma_manager)
        
        file_path = temp_project / "main.go"
        handler.index_file(file_path)
        
        assert handler.stats["indexed"] > 0
        
        # Verify it was added to collection
        info = chroma_manager.get_collection_info()
        assert info["count"] > 0
    
    def test_remove_file(self, test_config, logger, chroma_manager, temp_project):
        """Test removing a file from index"""
        handler = CodeIndexerHandler(test_config, logger, chroma_manager)
        
        # First index the file
        file_path = temp_project / "main.go"
        handler.index_file(file_path)
        
        # Then remove it
        handler.remove_file(file_path)
        
        # Verify it was removed
        rel_path = str(file_path.relative_to(temp_project))
        existing = chroma_manager.collection.get(where={"source": rel_path})
        assert len(existing["ids"]) == 0
    
    def test_gitignore_reload(self, test_config, logger, chroma_manager, temp_project_with_gitignore):
        """Test reloading gitignore rules when file changes"""
        test_config.project_root = temp_project_with_gitignore
        handler = CodeIndexerHandler(test_config, logger, chroma_manager)
        
        # Initial gitignore load
        handler.processor._load_gitignore_rules()
        rules_before = len(handler.processor.gitignore_rules)
        
        # Simulate gitignore change
        handler._handle_gitignore_change(temp_project_with_gitignore / ".gitignore")
        
        # Rules should be reloaded
        assert len(handler.processor.gitignore_rules) >= rules_before
    
    def test_watcher_initialization(self, test_config, logger, chroma_manager, temp_project):
        """Test file watcher initialization"""
        test_config.project_root = temp_project
        watcher = FileWatcher(test_config, logger, chroma_manager)
        
        assert watcher.config == test_config
        assert watcher.collection_manager == chroma_manager
    
    def test_initial_index(self, test_config, logger, chroma_manager, temp_project):
        """Test initial full index"""
        test_config.project_root = temp_project
        watcher = FileWatcher(test_config, logger, chroma_manager)
        handler = watcher.start()
        
        files_indexed = watcher.initial_index()
        
        assert files_indexed > 0
        assert handler.stats["indexed"] > 0
        
        watcher.stop()
