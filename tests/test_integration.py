"""Integration tests - end to end"""

import pytest
import time
import requests
from pathlib import Path

from openrag.config import OpenRAGConfig
from openrag.chroma.manager import ChromaCollectionManager
from openrag.indexer.watcher import FileWatcher
from openrag.query.server import QueryServer


@pytest.mark.usefixtures("running_chromadb")
class TestIntegration:
    """End-to-end integration tests"""
    
    def test_full_pipeline(self, test_config, logger, temp_project):
        """Test complete pipeline: index → query"""
        
        # 1. Setup collection
        collection_manager = ChromaCollectionManager(test_config, logger)
        collection_manager.initialize_collection()
        
        # 2. Index files
        watcher = FileWatcher(test_config, logger, collection_manager)
        handler = watcher.start()
        
        # Index all files
        for root, dirs, files in os.walk(temp_project):
            for file in files:
                file_path = Path(root) / file
                if handler.processor.is_code_file(file_path):
                    handler.index_file(file_path)
        
        # 3. Query
        results = collection_manager.query("Go function", n_results=5)
        
        assert results is not None
        assert len(results["documents"][0]) > 0
        
        watcher.stop()
    
    def test_query_server_integration(self, test_config, logger, temp_project):
        """Test query server with real data"""
        
        # 1. Index some data
        collection_manager = ChromaCollectionManager(test_config, logger)
        collection_manager.initialize_collection()
        
        collection_manager.add_documents(
            ["Go backend code", "React frontend code"],
            [
                {"source": "main.go", "language": "go"},
                {"source": "App.jsx", "language": "react"}
            ],
            ["go1", "react1"]
        )
        
        # 2. Start query server (without actually running uvicorn)
        server = QueryServer(test_config, logger)
        app = server.create_app()
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # 3. Test query
        response = client.post("/query", json={
            "query": "backend",
            "n_results": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        
        # Should find Go code
        found_go = False
        for result in data["results"]:
            if result["metadata"].get("language") == "go":
                found_go = True
                break
        
        assert found_go
    
    def test_file_watcher_real_time(self, test_config, logger, chroma_manager, temp_project):
        """Test real-time file watching"""
        test_config.project_root = temp_project
        
        # Start watcher
        watcher = FileWatcher(test_config, logger, chroma_manager)
        handler = watcher.start()
        
        # Create a new file
        new_file = temp_project / "new_file.go"
        new_file.write_text("package main\nfunc new() {}\n")
        
        # Give watcher time to detect
        time.sleep(1)
        
        # Verify it was indexed
        rel_path = "new_file.go"
        existing = chroma_manager.collection.get(where={"source": rel_path})
        assert len(existing["ids"]) > 0
        
        # Modify the file
        new_file.write_text("package main\nfunc updated() {}\n")
        time.sleep(1)
        
        # Should be re-indexed
        existing_after = chroma_manager.collection.get(where={"source": rel_path})
        assert len(existing_after["ids"]) > 0
        
        watcher.stop()
    
    def test_gitignore_live_reload(self, test_config, logger, chroma_manager, temp_project_with_gitignore):
        """Test gitignore changes are picked up in real-time"""
        test_config.project_root = temp_project_with_gitignore
        
        # Start watcher
        watcher = FileWatcher(test_config, logger, chroma_manager)
        handler = watcher.start()
        handler.processor._load_gitignore_rules()
        
        # File should be ignored initially
        secret_file = temp_project_with_gitignore / "secrets.txt"
        assert handler.processor.should_ignore(secret_file) is True
        
        # Modify .gitignore to remove the exclusion
        gitignore = temp_project_with_gitignore / ".gitignore"
        gitignore.write_text("# Empty gitignore")
        
        # Trigger reload
        handler._handle_gitignore_change(gitignore)
        
        # File should no longer be ignored
        assert handler.processor.should_ignore(secret_file) is False
        
        watcher.stop()
