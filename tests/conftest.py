"""Pytest fixtures and configuration"""

import os
import sys
import tempfile
import shutil
import time
from pathlib import Path
from typing import Generator, Dict, Any

import pytest
import requests
from chromadb.api.client import Client as ChromaClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openrag.config import OpenRAGConfig
from openrag.chroma.manager import ChromaCollectionManager
from openrag.indexer.processor import CodeProcessor


@pytest.fixture
def temp_project() -> Generator[Path, None, None]:
    """Create a temporary project directory with sample files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create sample project structure
        (project_path / "main.go").write_text("""
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}

func add(a, b int) int {
    return a + b
}
""")
        
        (project_path / "utils.go").write_text("""
package main

func subtract(a, b int) int {
    return a - b
}

func multiply(a, b int) int {
    return a * b
}
""")
        
        (project_path / "README.md").write_text("# Test Project\n\nThis is a test project.")
        
        # Create frontend directory with React files
        frontend_dir = project_path / "frontend"
        frontend_dir.mkdir()
        (frontend_dir / "App.jsx").write_text("""
import React from 'react';

function App() {
    return <div>Hello World</div>;
}

export default App;
""")
        
        (frontend_dir / "index.js").write_text("""
import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';

ReactDOM.render(<App />, document.getElementById('root'));
""")
        
        # Create SQL file
        (project_path / "schema.sql").write_text("""
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title TEXT NOT NULL,
    content TEXT
);
""")
        
        yield project_path


@pytest.fixture
def temp_project_with_gitignore(temp_project: Path) -> Path:
    """Add .gitignore files to the temporary project"""
    
    # Root .gitignore
    (temp_project / ".gitignore").write_text("""
# Secrets
*.key
.env
secrets.txt

# Build outputs
dist/
build/
*.exe

# Dependencies
node_modules/
vendor/
""")
    
    # Frontend .gitignore
    (temp_project / "frontend" / ".gitignore").write_text("""
# React
.next/
out/
build/

# Dependencies
node_modules/

# Environment
.env.local
.env.production
""")
    
    # Create some files that should be ignored
    (temp_project / "secrets.txt").write_text("API_KEY=12345")
    (temp_project / "node_modules").mkdir()
    (temp_project / "node_modules" / "dummy.txt").write_text("ignored")
    (temp_project / "dist").mkdir()
    (temp_project / "dist" / "output.exe").write_text("binary")
    (temp_project / "frontend" / ".next").mkdir()
    (temp_project / "frontend" / ".next" / "cache.txt").write_text("cache")
    
    return temp_project


@pytest.fixture
def temp_large_file() -> Generator[Path, None, None]:
    """Create a temporary large file for chunking tests"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        # Generate 100KB of text
        content = "Lorem ipsum dolor sit amet. " * 5000
        f.write(content)
        path = Path(f.name)
    
    yield path
    
    if path.exists():
        path.unlink()


@pytest.fixture
def test_config(temp_project: Path) -> OpenRAGConfig:
    """Create a test configuration"""
    config = OpenRAGConfig()
    config.project_root = temp_project
    config.chroma_host = "localhost"
    config.chroma_port = 8001
    config.query_port = 8766  # Different port for tests
    config.collection_name = "test_collection"
    config.chunk_size = 500
    config.chunk_overlap = 100
    config.batch_size = 50
    config.log_level = "ERROR"
    config.chroma_log_stdout = False
    config.indexer_log_stdout = False
    config.query_log_stdout = False
    return config


@pytest.fixture
def chroma_manager(test_config, logger):
    """Create a ChromaDB collection manager for testing"""
    manager = ChromaCollectionManager(test_config, logger)
    
    # Clean up any existing test collection
    try:
        manager.client.delete_collection(test_config.collection_name)
    except:
        pass
    
    manager.initialize_collection()
    yield manager
    
    # Cleanup after tests
    try:
        manager.client.delete_collection(test_config.collection_name)
    except:
        pass


@pytest.fixture
def logger():
    """Create a dummy logger for testing"""
    import logging
    return logging.getLogger("test")


@pytest.fixture
def processor(test_config, logger):
    """Create a CodeProcessor instance for testing"""
    return CodeProcessor(test_config, logger)


@pytest.fixture
def running_chromadb():
    """Ensure ChromaDB is running (skip tests if not)"""
    try:
        client = ChromaClient(host="localhost", port=8001)
        client.heartbeat()
        return True
    except:
        pytest.skip("ChromaDB is not running on localhost:8001")
        return False


@pytest.fixture
def sample_files() -> Dict[str, str]:
    """Sample code snippets for testing"""
    return {
        "go": """
package main

import "fmt"

type User struct {
    ID   int
    Name string
}

func (u *User) Greet() string {
    return fmt.Sprintf("Hello, %s", u.Name)
}
""",
        "jsx": """
import React, { useState } from 'react';

const Counter = () => {
    const [count, setCount] = useState(0);
    
    return (
        <div>
            <p>Count: {count}</p>
            <button onClick={() => setCount(count + 1)}>
                Increment
            </button>
        </div>
    );
};

export default Counter;
""",
        "sql": """
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX idx_users_email ON users(email);
"""
    }
