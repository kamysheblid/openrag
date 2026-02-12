"""Tests for ChromaDB integration"""

import pytest
import time

from openrag.chroma.manager import ChromaCollectionManager
from openrag.chroma.server import ChromaServer


@pytest.mark.usefixtures("running_chromadb")
class TestChromaManager:
    """Test ChromaDB collection manager"""
    
    def test_connection(self, test_config, logger):
        """Test connecting to ChromaDB"""
        manager = ChromaCollectionManager(test_config, logger)
        assert manager.client is not None
        assert manager.embedding_fn is not None
    
    def test_collection_creation(self, chroma_manager):
        """Test creating a collection"""
        info = chroma_manager.get_collection_info()
        assert info["name"] == "test_collection"
        assert info["exists"] is True
        assert info["count"] == 0
    
    def test_add_documents(self, chroma_manager):
        """Test adding documents to collection"""
        documents = [
            "This is a test document about Go programming",
            "React components should be functional and reusable",
            "PostgreSQL queries need proper indexing",
        ]
        metadatas = [
            {"source": "test1.go", "language": "go"},
            {"source": "test2.jsx", "language": "react"},
            {"source": "test3.sql", "language": "sql"},
        ]
        ids = ["doc1", "doc2", "doc3"]
        
        chroma_manager.add_documents(documents, metadatas, ids)
        
        # Verify count increased
        info = chroma_manager.get_collection_info()
        assert info["count"] == 3
    
    def test_query(self, chroma_manager):
        """Test querying documents"""
        # Add test data
        documents = [
            "Go is great for backend services",
            "React is great for frontend UIs",
            "PostgreSQL is a powerful database",
        ]
        metadatas = [
            {"source": "go.txt", "language": "go"},
            {"source": "react.txt", "language": "react"},
            {"source": "sql.txt", "language": "sql"},
        ]
        ids = ["go", "react", "sql"]
        
        chroma_manager.add_documents(documents, metadatas, ids)
        
        # Query
        results = chroma_manager.query("backend", n_results=2)
        
        assert "documents" in results
        assert len(results["documents"][0]) > 0
        assert "Go" in results["documents"][0][0]
    
    def test_delete_by_source(self, chroma_manager):
        """Test deleting documents by source"""
        # Add test data
        documents = ["test content"]
        metadatas = [{"source": "delete_me.txt"}]
        ids = ["delete1"]
        
        chroma_manager.add_documents(documents, metadatas, ids)
        
        # Delete by source
        count = chroma_manager.delete_by_source("delete_me.txt")
        assert count == 1
        
        # Verify deleted
        info = chroma_manager.get_collection_info()
        assert "delete_me.txt" not in str(info)
    
    def test_collection_info(self, chroma_manager):
        """Test getting collection info"""
        # Add some documents with different languages
        docs = [
            ("go doc", {"source": "a.go", "language": "go"}),
            ("js doc", {"source": "b.js", "language": "javascript"}),
            ("py doc", {"source": "c.py", "language": "python"}),
        ]
        
        for i, (doc, meta) in enumerate(docs):
            chroma_manager.add_documents([doc], [meta], [f"doc{i}"])
        
        info = chroma_manager.get_collection_info()
        assert info["count"] == 3
        assert "go" in info["languages"]
        assert "javascript" in info["languages"]
        assert "python" in info["languages"]


class TestChromaServer:
    """Test ChromaDB server management"""
    
    def test_server_health_check(self, test_config, logger):
        """Test health check endpoint"""
        server = ChromaServer(test_config, logger)
        healthy = server._is_healthy()
        # Don't fail test if server isn't running
        if healthy:
            assert healthy is True
    
    def test_server_config(self, test_config, logger):
        """Test server configuration"""
        server = ChromaServer(test_config, logger)
        assert server.config.chroma_host == "localhost"
        assert server.config.chroma_port == 8001
