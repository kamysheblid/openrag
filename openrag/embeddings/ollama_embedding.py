"""Ollama embedding adapter for ChromaDB"""

import requests
import json
from typing import List, Optional
import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

class OllamaEmbeddingFunction(EmbeddingFunction):
    """ChromaDB compatible embedding function using Ollama"""
    
    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        url: str = "http://localhost:11434",
        timeout: int = 60,
        logger = None
    ):
        self.model_name = model_name
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.logger = logger
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Verify Ollama is reachable and model exists"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError(f"Ollama not responding: {response.status_code}")
            
            # Check if model exists
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            if self.model_name not in model_names:
                # Try without tag
                base_name = self.model_name.split(':')[0]
                exists = any(m.startswith(base_name) for m in model_names)
                if not exists:
                    raise ValueError(
                        f"Model '{self.model_name}' not found. "
                        f"Run: ollama pull {self.model_name}"
                    )
            
            if self.logger:
                self.logger.info(f"✅ Ollama connected - model: {self.model_name}")
                
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.url}. "
                f"Is Ollama running? (ollama serve)"
            )
    
    def __call__(self, texts: Documents) -> Embeddings:
        """Generate embeddings for a list of texts"""
        embeddings = []
        
        for text in texts:
            try:
                # Truncate extremely long texts (Ollama has limits)
                if len(text) > 8000:
                    text = text[:8000]
                
                response = requests.post(
                    f"{self.url}/api/embeddings",
                    json={
                        "model": self.model_name,
                        "prompt": text
                    },
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama error: {response.text}")
                
                embedding = response.json()['embedding']
                embeddings.append(embedding)

                # Causing OOM issues, clear response to free mem
                del response
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to embed text: {e}")
                # Return zero vector as fallback
                embeddings.append([0.0] * 768)  # Default dimension
        
        return embeddings
