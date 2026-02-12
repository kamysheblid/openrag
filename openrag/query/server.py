"""FastAPI query server"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import time
from typing import List, Dict, Any, Optional

from openrag.chroma.manager import ChromaCollectionManager


class QueryServer:
    """Manages the FastAPI query server"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.app = None
        self.collection_manager = None
    
    def create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(title="OpenRAG Query Server")
        
        # Enable CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Connect to ChromaDB
        self.logger.info("Connecting to ChromaDB for query server...")
        self.collection_manager = ChromaCollectionManager(self.config, self.logger)
        
        # Try to get collection
        try:
            self.collection_manager.initialize_collection()
            info = self.collection_manager.get_collection_info()
            self.logger.info(f"✅ Connected to collection '{info['name']}' with {info['count']} documents")
        except Exception as e:
            self.logger.error(f"Failed to initialize collection: {e}")
        
        class QueryRequest(BaseModel):
            query: str
            collection: Optional[str] = None
            n_results: int = 5
        
        class QueryResponse(BaseModel):
            results: List[Dict[str, Any]]
            count: int
        
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            """Log all requests"""
            start_time = time.time()
            
            # Log request
            if request.method == "POST" and request.url.path == "/query":
                body = await request.body()
                self.logger.debug(f"Request: {body[:200]}...")
            
            response = await call_next(request)
            
            # Log response time
            process_time = time.time() - start_time
            self.logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
            
            return response
        
        @app.get("/")
        async def root():
            """Root endpoint"""
            info = self.collection_manager.get_collection_info()
            response = {
                "service": "OpenRAG Query Server",
                "version": "0.1.0",
                "status": "running",
                "collection": info
            }
            self.logger.debug(f"Root endpoint called, collection has {info['count']} documents")
            return response
        
        @app.get("/health")
        async def health():
            """Health check endpoint"""
            try:
                info = self.collection_manager.get_collection_info()
                status = {
                    "status": "healthy",
                    "chromadb": "connected",
                    "collection": info
                }
                self.logger.debug("Health check: OK")
                return status
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "chromadb": "disconnected",
                    "error": str(e)
                }
        
        @app.get("/collections")
        async def list_collections():
            """List all collections"""
            try:
                collections = self.collection_manager.client.list_collections()
                names = [c.name for c in collections]
                self.logger.debug(f"Listed collections: {names}")
                return {"collections": names}
            except Exception as e:
                self.logger.error(f"Failed to list collections: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/query", response_model=QueryResponse)
        async def query(request: QueryRequest):
            """Query the codebase"""
            start_time = time.time()
            self.logger.info(f"Query: '{request.query[:100]}...' (n_results={request.n_results})")
            
            try:
                # Override collection name if provided
                collection_name = request.collection or self.config.collection_name
                self.logger.debug(f"Using collection: {collection_name}")
                
                # Get collection (without embedding function - use persisted one)
                collection = self.collection_manager.client.get_collection(
                    name=collection_name
                )
                
                # Query
                results = collection.query(
                    query_texts=[request.query],
                    n_results=request.n_results,
                    include=["documents", "metadatas", "distances"]
                )
                
                formatted_results = []
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    similarity = 1 - distance
                    formatted_results.append({
                        "id": i + 1,
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "metadata": metadata,
                        "similarity": similarity
                    })
                    
                    self.logger.debug(f"Result {i+1}: {metadata.get('source', 'unknown')} (similarity: {similarity:.3f})")
                
                elapsed = time.time() - start_time
                self.logger.info(f"✅ Found {len(formatted_results)} results in {elapsed:.3f}s")
                
                return QueryResponse(
                    results=formatted_results,
                    count=len(formatted_results)
                )
                
            except Exception as e:
                elapsed = time.time() - start_time
                self.logger.error(f"❌ Query failed after {elapsed:.3f}s: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        return app
    
    def start(self):
        """Start the query server"""
        self.logger.info(f"🚀 Starting query server on {self.config.query_host}:{self.config.query_port}")
        
        # Create log file for uvicorn access logs
        uvicorn_log_file = self.config.logs_dir / "query" / "uvicorn_access.log"
        uvicorn_error_file = self.config.logs_dir / "query" / "uvicorn_error.log"
        
        self.app = self.create_app()
        
        # Configure uvicorn logging
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(message)s",
                    "use_colors": None,
                },
                "access": {
                    "()": "uvicorn.logging.AccessFormatter",
                    "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": str(uvicorn_log_file),
                },
                "error_file": {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": str(uvicorn_error_file),
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default", "file"], "level": "INFO"},
                "uvicorn.error": {"handlers": ["default", "error_file"], "level": "INFO", "propagate": False},
                "uvicorn.access": {"handlers": ["access", "file"], "level": "INFO", "propagate": False},
            },
        }
        
        uvicorn.run(
            self.app,
            host=self.config.query_host,
            port=self.config.query_port,
            log_config=log_config,
            log_level=self.config.log_level.lower(),
            access_log=self.config.log_level == "DEBUG",
        )
