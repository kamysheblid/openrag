"""Tests for query API"""

import pytest
import requests
from fastapi.testclient import TestClient

from openrag.query.server import QueryServer


@pytest.mark.usefixtures("running_chromadb")
class TestQueryAPI:
    """Test the query server API endpoints"""
    
    @pytest.fixture
    def client(self, test_config, logger):
        """Create test client"""
        server = QueryServer(test_config, logger)
        app = server.create_app()
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "OpenRAG" in data["service"]
    
    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_collections_endpoint(self, client):
        """Test collections endpoint"""
        response = client.get("/collections")
        assert response.status_code == 200
    
    def test_query_endpoint(self, client, chroma_manager):
        """Test query endpoint"""
        # Add some test data
        chroma_manager.add_documents(
            ["Go is a programming language"],
            [{"source": "test.go", "language": "go"}],
            ["test1"]
        )
        
        response = client.post("/query", json={
            "query": "Go programming",
            "collection": "test_collection",
            "n_results": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data
    
    def test_query_invalid_collection(self, client):
        """Test query with invalid collection"""
        response = client.post("/query", json={
            "query": "test",
            "collection": "does_not_exist",
            "n_results": 5
        })
        
        assert response.status_code == 500
