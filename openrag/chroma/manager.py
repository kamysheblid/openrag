"""ChromaDB collection manager"""

import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
import time


class ChromaCollectionManager:
    """Manages ChromaDB collections"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.client = None
        self.collection = None
        self.embedding_fn = None
        self.connect()
    
    def connect(self):
        """Connect to ChromaDB"""
        try:
            self.logger.debug(f"Connecting to ChromaDB at {self.config.chroma_host}:{self.config.chroma_port}")
            self.client = chromadb.HttpClient(
                host=self.config.chroma_host,
                port=self.config.chroma_port
            )
            # Test connection
            heartbeat = self.client.heartbeat()
            self.logger.debug(f"ChromaDB heartbeat: {heartbeat}")
            self.logger.info(f"✅ Connected to ChromaDB at {self.config.chroma_host}:{self.config.chroma_port}")
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to ChromaDB: {e}")
            raise
    
    def initialize_collection(self):
        """Initialize or get existing collection with selected backend"""
        self.logger.info(f"🔍 CONFIG: embedding_backend = '{self.config.embedding_backend}'")
        self.logger.info(f"🔍 CONFIG: ollama_model = '{self.config.ollama_model}'")
        self.logger.info(f"🔍 CONFIG: ollama_url = '{self.config.ollama_url}'")

        try:
            start_time = time.time()
            
            # Select embedding backend
            if self.config.embedding_backend == "ollama":
                from openrag.embeddings.ollama_embedding import OllamaEmbeddingFunction
                
                self.logger.info(f"🦙 Using Ollama embeddings - model: {self.config.ollama_model}")
                self.embedding_fn = OllamaEmbeddingFunction(
                    model_name=self.config.ollama_model,
                    url=self.config.ollama_url,
                    timeout=self.config.ollama_timeout,
                    logger=self.logger
                )
                
            else:  # sentence-transformers
                self.logger.info(f"🧠 Using SentenceTransformers")
                
                # Auto-select model
                if self.config.embedding_model:
                    model_name = self.config.embedding_model
                    self.logger.info(f"  Using model: {model_name}")
                else:
                    model_name = "all-MiniLM-L6-v2"
                    self.logger.info(f"  Using default model: {model_name}")
                
                from chromadb.utils import embedding_functions
                self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_name
                )
            
            elapsed = time.time() - start_time
            self.logger.info(f"✅ Embedding model loaded in {elapsed:.1f}s")
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.config.collection_name
                )
                count = self.collection.count()
                self.logger.info(f"📚 Using existing collection '{self.config.collection_name}' with {count} documents")
            except:
                self.collection = self.client.create_collection(
                    name=self.config.collection_name,
                    embedding_function=self.embedding_fn
                )
                self.logger.info(f"📚 Created new collection '{self.config.collection_name}'")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize collection: {e}", exc_info=True)
            raise
    
    def delete_by_source(self, source: str) -> int:
        """Delete all documents with given source"""
        try:
            self.logger.debug(f"Deleting documents with source: {source}")
            existing = self.collection.get(where={"source": source})
            if existing['ids']:
                self.collection.delete(ids=existing['ids'])
                self.logger.debug(f"Deleted {len(existing['ids'])} documents")
                return len(existing['ids'])
        except Exception as e:
            self.logger.error(f"Error deleting {source}: {e}")
        return 0
    
    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Add documents in batches with memory management"""
        batch_size = min(self.config.batch_size, 50)  # Smaller batches
        total = len(documents)
        
        self.logger.debug(f"Adding {total} documents in batches of {batch_size}")

        # Log memory before
        import psutil
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024
        self.logger.debug(f"Memory before batch: {mem_before:.1f} MB")
        
        for i in range(0, len(documents), batch_size):
            end = min(i + batch_size, len(documents))
            batch_num = i // batch_size + 1
            total_batches = (total - 1) // batch_size + 1
            
            self.logger.debug(f"Adding batch {batch_num}/{total_batches} ({end - i} documents)")
            
            self.collection.add(
                documents=documents[i:end],
                metadatas=metadatas[i:end],
                ids=ids[i:end]
            )
            
            import gc
            gc.collect()

            mem_after = process.memory_info().rss / 1024 / 1024
            self.logger.debug(f"Memory after batch {batch_num}: {mem_after:.1f} MB (Δ {mem_after - mem_before:.1f} MB)")
    
        mem_final = process.memory_info().rss / 1024 / 1024
        self.logger.debug(f"Memory final: {mem_final:.1f} MB (total Δ {mem_final - mem_before:.1f} MB)")

    def get_collection_info(self) -> Dict:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            
            # Get a sample to show languages
            try:
                sample = self.collection.get(limit=100)
                languages = set()
                for meta in sample.get("metadatas", []):
                    if meta:
                        languages.add(meta.get("language", "unknown"))
            except:
                languages = set()
            
            return {
                "name": self.config.collection_name,
                "count": count,
                "languages": list(languages)[:10],
                "exists": True
            }
        except Exception as e:
            self.logger.error(f"Error getting collection info: {e}")
            return {
                "name": self.config.collection_name,
                "count": 0,
                "languages": [],
                "exists": False,
                "error": str(e)
            }
    
    def query(self, query_text: str, n_results: int = 5) -> Dict:
        """Query the collection"""
        self.logger.debug(f"Querying collection with: '{query_text[:50]}...'")
        start_time = time.time()
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        elapsed = time.time() - start_time
        self.logger.debug(f"Query returned {len(results['documents'][0])} results in {elapsed:.3f}s")
        
        return results
