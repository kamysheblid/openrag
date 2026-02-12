"""Configuration management with sensible defaults"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Set, List
import os
import json
from datetime import datetime


@dataclass
class OpenRAGConfig:
    """Master configuration for OpenRAG"""
    
    # Project paths
    project_root: Path = field(default_factory=lambda: Path.cwd())
    data_dir: Path = field(default_factory=lambda: Path.home() / ".openrag" / "data")
    logs_dir: Path = field(default_factory=lambda: Path.home() / ".openrag" / "logs")
    
    # Component enabled/disabled
    enable_chroma: bool = True
    enable_indexer: bool = True
    enable_query: bool = True
    
    # ChromaDB settings
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_persist_dir: str = "chroma_data"
    
    # Query server settings
    query_host: str = "localhost"
    query_port: int = 8765
    
    # Indexer settings
    collection_name: str = "code_rag"
    file_extensions: Set[str] = field(default_factory=lambda: {
        '.go', '.js', '.jsx', '.ts', '.tsx', '.sql', '.yml', '.yaml',
        '.json', '.toml', '.env', '.conf', '.md', '.txt', '.sh', '.bash',
        '.html', '.css', '.scss', '.py', '.rb', '.php', '.java', '.rs',
        '.cpp', '.c', '.h', '.hpp', '.cs', '.swift', '.kt', '.jl'
    })
    exclude_dirs: Set[str] = field(default_factory=lambda: {
        '.git', '__pycache__', 'venv', 'env', '.env', 'dist', 'build',
        '.next', 'out', 'coverage', '.vscode', '.idea', 'node_modules',
        '.chroma_db', '.pytest_cache', '.mypy_cache', '.ruff_cache',
        'target', 'bin', 'obj', 'vendor'
    })
    exclude_files: Set[str] = field(default_factory=lambda: {
        '*.pyc', '*.pyo', '*.pyd', '.DS_Store', 'Thumbs.db', '*.log',
        '*.lock', '*.bak', '*.swp', '*.swo', '*.tmp', '*.cache'
    })
    
    # Chunking settings
    chunk_size: int = 500
    chunk_overlap: int = 100
    batch_size: int = 10
    
    # Watch settings
    recursive: bool = True
    ignore_hidden: bool = True

    # Embedding backend settings
    embedding_backend: str = "ollama"  # or "ollama"
    embedding_model: Optional[str] = None  # For sentence-transformers

    # Ollama settings
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mxbai-embed-large:335m"
    ollama_timeout: int = 60

    # Logging settings
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name} | {message}"
    log_rotation: str = "1 day"
    log_retention: str = "30 days"
    log_compression: str = "gz"
    
    # Separate log outputs per component
    chroma_log_stdout: bool = True
    indexer_log_stdout: bool = True
    query_log_stdout: bool = True
    chroma_log_file: bool = True
    indexer_log_file: bool = True
    query_log_file: bool = True
    
    def __post_init__(self):
        """Create directories after initialization"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "chroma").mkdir(exist_ok=True)
        (self.logs_dir / "indexer").mkdir(exist_ok=True)
        (self.logs_dir / "query").mkdir(exist_ok=True)
    
    @classmethod
    def from_dict(cls, d: dict) -> "OpenRAGConfig":
        """Create config from dictionary"""
        # Convert string paths to Path objects
        if "project_root" in d and isinstance(d["project_root"], str):
            d["project_root"] = Path(d["project_root"])
        if "data_dir" in d and isinstance(d["data_dir"], str):
            d["data_dir"] = Path(d["data_dir"])
        if "logs_dir" in d and isinstance(d["logs_dir"], str):
            d["logs_dir"] = Path(d["logs_dir"])
        
        # Convert lists to sets for collection fields
        for field_name in ["file_extensions", "exclude_dirs", "exclude_files"]:
            if field_name in d and isinstance(d[field_name], list):
                d[field_name] = set(d[field_name])
        
        return cls(**d)
    
    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization"""
        d = self.__dict__.copy()
        # Convert Path objects to strings
        d["project_root"] = str(d["project_root"])
        d["data_dir"] = str(d["data_dir"])
        d["logs_dir"] = str(d["logs_dir"])
        # Convert sets to lists for JSON serialization
        d["file_extensions"] = list(d["file_extensions"])
        d["exclude_dirs"] = list(d["exclude_dirs"])
        d["exclude_files"] = list(d["exclude_files"])
        return d
    
    def save(self, path: Optional[Path] = None):
        """Save configuration to file"""
        if path is None:
            path = self.data_dir / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "OpenRAGConfig":
        """Load configuration from file"""
        with open(path) as f:
            d = json.load(f)
        return cls.from_dict(d)
