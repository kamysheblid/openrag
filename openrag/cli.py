"""Command line interface for OpenRAG"""

import typer
import sys
import time
import os
from pathlib import Path
from typing import Optional, List

from openrag.config import OpenRAGConfig
from openrag.utils.logging import setup_logging
from openrag.chroma.server import ChromaServer
from openrag.utils.process import ProcessManager
from openrag.chroma.manager import ChromaCollectionManager
from openrag.indexer.watcher import FileWatcher
from openrag.query.server import QueryServer

app = typer.Typer(
    name="openrag",
    help="One-command local RAG system",
    add_completion=False,
)


@app.callback()
def callback():
    """OpenRAG - One-command local RAG system"""
    pass


@app.command()
def up(
    # Project paths
    project: Path = typer.Option(
        Path.cwd(),
        "--project", "-p",
        help="Path to codebase to index",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    
    # ChromaDB settings
    chroma_host: str = typer.Option(
        "localhost",
        "--chroma-host",
        help="ChromaDB host",
    ),
    chroma_port: int = typer.Option(
        8001,
        "--chroma-port",
        help="ChromaDB port",
    ),
    
    # Query server settings
    query_host: str = typer.Option(
        "localhost",
        "--query-host",
        help="Query server host",
    ),
    query_port: int = typer.Option(
        8765,
        "--query-port",
        help="Query server port",
    ),
    
    # Collection settings
    collection: str = typer.Option(
        "code_rag",
        "--collection", "-c",
        help="ChromaDB collection name",
    ),
    
    # Component control
    no_chroma: bool = typer.Option(
        False,
        "--no-chroma",
        help="Don't start ChromaDB (assume it's already running)",
    ),
    no_indexer: bool = typer.Option(
        False,
        "--no-indexer",
        help="Don't start auto-indexer",
    ),
    no_query: bool = typer.Option(
        False,
        "--no-query",
        help="Don't start query server",
    ),
    no_initial_index: bool = typer.Option(
        False,
        "--no-initial-index",
        help="Skip initial full index",
    ),
    
    # File filtering
    extensions: Optional[List[str]] = typer.Option(
        None,
        "--extensions", "-e",
        help="File extensions to index (e.g., .go .js .tsx)",
    ),
    exclude_dirs: Optional[List[str]] = typer.Option(
        None,
        "--exclude-dirs",
        help="Directories to exclude (e.g., node_modules dist)",
    ),
    
    # Chunking settings
    chunk_size: int = typer.Option(
        500,
        "--chunk-size",
        help="Size of text chunks in characters",
    ),
    chunk_overlap: int = typer.Option(
        100,
        "--chunk-overlap",
        help="Overlap between chunks in characters",
    ),
    # Embedding backend selection
    embedding_backend: str = typer.Option(
        "sentence-transformers",
        "--embed-backend", "-eb",
        help="Embedding backend: 'sentence-transformers' or 'ollama'",
    ),

    # Ollama specific settings
    ollama_url: str = typer.Option(
        "http://localhost:11434",
        "--ollama-url",
        help="Ollama server URL",
    ),
    ollama_model: str = typer.Option(
        "nomic-embed-text",
        "--ollama-model", "-om",
        help="Ollama embedding model (pull first: ollama pull nomic-embed-text)",
    ),
    ollama_timeout: int = typer.Option(
        60,
        "--ollama-timeout",
        help="Timeout for Ollama requests in seconds",
    ),
    # Logging settings
    log_level: str = typer.Option(
        "INFO",
        "--log-level", "-l",
        help="Log level (DEBUG, INFO, WARNING, ERROR)",
    ),
    log_dir: Optional[Path] = typer.Option(
        None,
        "--log-dir",
        help="Directory for log files",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Suppress stdout logging (file logging still enabled)",
    ),
    
    # Config
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Load configuration from file",
    ),
    save_config: Optional[Path] = typer.Option(
        None,
        "--save-config",
        help="Save configuration to file and exit",
    ),
):
    """Start OpenRAG services"""
    
    print("\n" + "=" * 60)
    print("🚀 OpenRAG - One-command Local RAG System")
    print("=" * 60 + "\n")
    
    # === LOAD/SAVE CONFIG ===
    print("📋 CONFIGURATION PHASE")
    print("-" * 40)
    
    # Load or create config
    if config_file and config_file.exists():
        print(f"  Loading config from: {config_file}")
        config = OpenRAGConfig.load(config_file)
        print(f"  ✅ Config loaded")
    else:
        print(f"  Creating default config")
        config = OpenRAGConfig()
        print(f"  ✅ Default config created")
    
    # Override with command line arguments
    print(f"\n  Overriding with CLI args:")
    config.project_root = project
    print(f"    project: {project}")
    config.chroma_host = chroma_host
    print(f"    chroma_host: {chroma_host}")
    config.chroma_port = chroma_port
    print(f"    chroma_port: {chroma_port}")
    config.query_host = query_host
    print(f"    query_host: {query_host}")
    config.query_port = query_port
    print(f"    query_port: {query_port}")
    config.collection_name = collection
    print(f"    collection: {collection}")
    config.enable_chroma = not no_chroma
    print(f"    enable_chroma: {not no_chroma}")
    config.enable_indexer = not no_indexer
    print(f"    enable_indexer: {not no_indexer}")
    config.enable_query = not no_query
    print(f"    enable_query: {not no_query}")
    config.initial_index = not no_initial_index
    print(f"    initial_index: {not no_initial_index}")
    config.chunk_size = chunk_size
    print(f"    chunk_size: {chunk_size}")
    config.chunk_overlap = chunk_overlap
    print(f"    chunk_overlap: {chunk_overlap}")
    config.log_level = log_level.upper()
    print(f"    log_level: {log_level.upper()}")

    if log_dir:
        config.logs_dir = log_dir
        print(f"    logs_dir: {log_dir}")
    
    if extensions:
        config.file_extensions = set(extensions)
        print(f"    extensions: {extensions}")
    
    if exclude_dirs:
        config.exclude_dirs = set(exclude_dirs)
        print(f"    exclude_dirs: {exclude_dirs}")
    
    # Update stdout logging based on quiet flag
    if quiet:
        config.chroma_log_stdout = False
        config.indexer_log_stdout = False
        config.query_log_stdout = False
        print(f"    quiet mode: ON (stdout logging disabled)")
    
    # Save config if requested
    if save_config:
        print(f"\n  💾 Saving config to: {save_config}")
        config.save(save_config)
        print(f"  ✅ Config saved")
        raise typer.Exit()
    
    print("\n  📁 Creating directories...")
    config.__post_init__()
    print(f"    data_dir: {config.data_dir}")
    print(f"    logs_dir: {config.logs_dir}")
    print(f"    ✅ Directories created")
    
    print("\n" + "=" * 60 + "\n")
    
    # === LOGGING SETUP ===
    print("📋 LOGGING SETUP PHASE")
    print("-" * 40)
    print(f"  Setting up loggers with level: {config.log_level}")
    print(f"  Log directory: {config.logs_dir}")
    
    loggers = setup_logging(config)
    chroma_logger = loggers["chroma"]
    indexer_logger = loggers["indexer"]
    query_logger = loggers["query"]

    import sys
    print(f"\n🔍 LOGGER DEBUG:")
    print(f"  Chroma logger ID: {id(chroma_logger)}")
    print(f"  Indexer logger ID: {id(indexer_logger)}")
    print(f"  Query logger ID: {id(query_logger)}")
    print(f"  All same? {id(chroma_logger) == id(indexer_logger) == id(query_logger)}")
    print(f"  Chroma handlers: {chroma_logger._core.handlers.keys()}")
    print(f"  Indexer handlers: {indexer_logger._core.handlers.keys()}")
    print(f"  Query handlers: {query_logger._core.handlers.keys()}\n")

    indexer_logger.debug("🔴🔴🔴 THIS SHOULD APPEAR IN INDEXER LOGS 🔴🔴🔴")
    chroma_logger.debug("🔵🔵🔵 THIS SHOULD APPEAR IN CHROMA LOGS 🔵🔵🔵")
    query_logger.debug("🟢🟢🟢 THIS SHOULD APPEAR IN QUERY LOGS 🟢🟢🟢")

    indexer_logger.debug(f"🔍🔍🔍 DEBUG MODE ACTIVE - Log level: {config.log_level}")

    print(f"  ✅ Chroma logger: {chroma_logger}")
    print(f"  ✅ Indexer logger: {indexer_logger}")
    print(f"  ✅ Query logger: {query_logger}")
    
    # Log initial config to files
    chroma_logger.debug("=" * 60)
    chroma_logger.debug("OPENRAG STARTUP - CHROMA COMPONENT")
    chroma_logger.debug("=" * 60)
    chroma_logger.debug(f"Config: {config.to_dict()}")
    
    indexer_logger.debug("=" * 60)
    indexer_logger.debug("OPENRAG STARTUP - INDEXER COMPONENT")
    indexer_logger.debug("=" * 60)
    indexer_logger.debug(f"Config: {config.to_dict()}")
    
    query_logger.debug("=" * 60)
    query_logger.debug("OPENRAG STARTUP - QUERY COMPONENT")
    query_logger.debug("=" * 60)
    query_logger.debug(f"Config: {config.to_dict()}")
    
    print("\n" + "=" * 60 + "\n")
    
    # === PROCESS MANAGER ===
    print("📋 PROCESS MANAGER PHASE")
    print("-" * 40)
    print(f"  Initializing ProcessManager...")
    process_manager = ProcessManager(indexer_logger)
    print(f"  ✅ ProcessManager ready")
    print("\n" + "=" * 60 + "\n")
    
    try:
        # === CHROMADB STARTUP ===
        if config.enable_chroma:
            print("📋 CHROMADB STARTUP PHASE")
            print("-" * 40)
            print(f"  Creating ChromaServer instance...")
            chroma_server = ChromaServer(config, chroma_logger)
            print(f"  ✅ ChromaServer created")
            
            print(f"  Starting ChromaDB...")
            chroma_logger.debug(">>> ENTERING ChromaServer.start()")
            success = chroma_server.start()
            chroma_logger.debug(f"<<< EXITING ChromaServer.start() with result: {success}")
            
            if not success:
                print(f"  ❌ ChromaDB failed to start")
                chroma_logger.error("ChromaDB startup failed, exiting")
                raise typer.Exit(1)
            else:
                print(f"  ✅ ChromaDB started successfully")
        else:
            print("📋 CHROMADB STARTUP PHASE")
            print("-" * 40)
            print(f"  ⚠️ ChromaDB disabled (--no-chroma flag)")
            chroma_logger.info("ChromaDB disabled by user")
        
        print("\n" + "=" * 60 + "\n")
        
        # === COLLECTION INITIALIZATION ===
        if config.enable_chroma or not no_chroma:
            print("📋 COLLECTION INITIALIZATION PHASE")
            print("-" * 40)
            print(f"  Creating CollectionManager...")
            collection_manager = ChromaCollectionManager(config, indexer_logger)
            print(f"  ✅ CollectionManager created")
            
            print(f"  Initializing collection '{config.collection_name}'...")
            indexer_logger.debug(">>> ENTERING ChromaCollectionManager.initialize_collection()")
            collection_manager.initialize_collection()
            indexer_logger.debug("<<< EXITING ChromaCollectionManager.initialize_collection()")
            print(f"  ✅ Collection ready")
            
            # Get collection stats
            info = collection_manager.get_collection_info()
            print(f"  📊 Collection stats: {info['count']} documents")
            indexer_logger.info(f"Collection '{info['name']}' has {info['count']} documents")
        else:
            collection_manager = None
            print("📋 COLLECTION INITIALIZATION PHASE")
            print("-" * 40)
            print(f"  ⚠️ Skipping (ChromaDB disabled)")
        
        print("\n" + "=" * 60 + "\n")
        
        # === FILE WATCHER STARTUP ===
        if config.enable_indexer and collection_manager:
            print("📋 FILE WATCHER STARTUP PHASE")
            print("-" * 40)
            print(f"  Creating FileWatcher...")
            file_watcher = FileWatcher(config, indexer_logger, collection_manager)
            print(f"  ✅ FileWatcher created")
            
            print(f"  Starting file watcher...")
            indexer_logger.debug(">>> ENTERING FileWatcher.start()")
            handler = file_watcher.start()
            indexer_logger.debug("<<< EXITING FileWatcher.start()")
            print(f"  ✅ File watcher running")
            
            # Initial index
            if config.initial_index:
                print(f"\n  📊 Running initial full index...")
                indexer_logger.debug(">>> ENTERING FileWatcher.initial_index()")
                files_indexed = file_watcher.initial_index()
                indexer_logger.debug(f"<<< EXITING FileWatcher.initial_index() - indexed {files_indexed} files")
                print(f"  ✅ Initial index complete: {files_indexed} files")
            else:
                print(f"  ⚠️ Skipping initial index (--no-initial-index flag)")
        else:
            print("📋 FILE WATCHER STARTUP PHASE")
            print("-" * 40)
            if not config.enable_indexer:
                print(f"  ⚠️ Indexer disabled (--no-indexer flag)")
            if not collection_manager:
                print(f"  ⚠️ No collection manager available")
            file_watcher = None
        
        print("\n" + "=" * 60 + "\n")
        
        # === QUERY SERVER STARTUP ===
        if config.enable_query:
            print("📋 QUERY SERVER STARTUP PHASE")
            print("-" * 40)
            print(f"  Creating QueryServer...")
            query_server = QueryServer(config, query_logger)
            print(f"  ✅ QueryServer created")
            
            # Kill existing process on port
            print(f"  Checking port {config.query_port}...")
            killed = ProcessManager.kill_existing(config.query_port)
            if killed:
                print(f"  ✅ Killed existing process on port {config.query_port}")
            
            print(f"  Starting query server on {config.query_host}:{config.query_port}...")
            print(f"  ⚠️ This will block until stopped with Ctrl+C")
            print("\n" + "=" * 60 + "\n")
            
            query_logger.debug(">>> ENTERING QueryServer.start()")
            query_server.start()
            query_logger.debug("<<< EXITING QueryServer.start()")
        else:
            print("📋 QUERY SERVER STARTUP PHASE")
            print("-" * 40)
            print(f"  ⚠️ Query server disabled (--no-query flag)")
            print(f"\n✅ OpenRAG is running. Press Ctrl+C to stop.\n")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n👋 Shutting down...")
    
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Log to all loggers
        chroma_logger.error(f"Fatal error: {e}", exc_info=True)
        indexer_logger.error(f"Fatal error: {e}", exc_info=True)
        query_logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        print("\n📋 CLEANUP PHASE")
        print("-" * 40)
        
        if 'process_manager' in locals():
            print(f"  Stopping all processes...")
            process_manager.stop_all()
            print(f"  ✅ Processes stopped")
        
        if 'file_watcher' in locals() and file_watcher:
            print(f"  Stopping file watcher...")
            file_watcher.stop()
            print(f"  ✅ File watcher stopped")
        
        print(f"\n✅ OpenRAG stopped\n")


@app.command()
def down():
    """Stop all OpenRAG services"""
    print("\n" + "=" * 60)
    print("🛑 OpenRAG - Shutting Down")
    print("=" * 60 + "\n")
    
    print("📋 PROCESS CLEANUP")
    print("-" * 40)
    
    # Kill ChromaDB on port 8001
    print(f"  Checking ChromaDB on port 8001...")
    if ProcessManager.kill_existing(8001):
        print(f"  ✅ Stopped ChromaDB")
    else:
        print(f"  ⚠️ No ChromaDB process found")
    
    # Kill query server on port 8765
    print(f"  Checking query server on port 8765...")
    if ProcessManager.kill_existing(8765):
        print(f"  ✅ Stopped query server")
    else:
        print(f"  ⚠️ No query server process found")
    
    print(f"\n✅ OpenRAG stopped\n")


@app.command()
def status():
    """Check status of OpenRAG services"""
    print("\n" + "=" * 60)
    print("📊 OpenRAG - Status Check")
    print("=" * 60 + "\n")
    
    import psutil
    import socket
    
    print("📋 SERVICE STATUS")
    print("-" * 40)
    
    # Check ChromaDB
    chroma_running = False
    chroma_pid = None
    
    # Check by port
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 8001))
        sock.close()
        if result == 0:
            chroma_running = True
            print(f"  ✅ ChromaDB: Running on port 8001")
        else:
            print(f"  ❌ ChromaDB: Not running on port 8001")
    except:
        print(f"  ❌ ChromaDB: Could not check port 8001")
    
    # Check by process
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.cmdline())
            if "chroma" in cmdline.lower() and "run" in cmdline.lower():
                chroma_pid = proc.pid
                print(f"    PID: {chroma_pid}")
                break
        except:
            pass
    
    # Check query server
    query_running = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 8765))
        sock.close()
        if result == 0:
            query_running = True
            print(f"  ✅ Query Server: Running on port 8765")
        else:
            print(f"  ❌ Query Server: Not running on port 8765")
    except:
        print(f"  ❌ Query Server: Could not check port 8765")
    
    print("\n📋 COLLECTION STATUS")
    print("-" * 40)
    
    # Check collections
    try:
        import chromadb
        client = chromadb.HttpClient(host="localhost", port=8001)
        collections = client.list_collections()
        if collections:
            print(f"  ✅ Connected to ChromaDB")
            print(f"\n  📚 Collections:")
            for c in collections:
                try:
                    count = c.count()
                    print(f"    • {c.name}: {count} documents")
                except:
                    print(f"    • {c.name}: (count unavailable)")
        else:
            print(f"  ⚠️ Connected but no collections found")
    except Exception as e:
        print(f"  ❌ Cannot connect to ChromaDB: {e}")
    
    print(f"\n✅ Status check complete\n")


@app.command()
def init(
    project: Path = typer.Option(
        Path.cwd(),
        "--project", "-p",
        help="Path to codebase to index",
    ),
    collection: str = typer.Option(
        "code_rag",
        "--collection", "-c",
        help="Collection name",
    ),
    extensions: Optional[List[str]] = typer.Option(
        None,
        "--extensions", "-e",
        help="File extensions to index",
    ),
):
    """Initialize a new collection (index all files once)"""
    
    print("\n" + "=" * 60)
    print("📚 OpenRAG - Initialize Collection")
    print("=" * 60 + "\n")
    
    from openrag.config import OpenRAGConfig
    from openrag.utils.logging import setup_logging
    from openrag.chroma.manager import ChromaCollectionManager
    from openrag.indexer.watcher import FileWatcher
    
    print("📋 CONFIGURATION")
    print("-" * 40)
    print(f"  Project: {project}")
    print(f"  Collection: {collection}")
    if extensions:
        print(f"  Extensions: {extensions}")
    
    config = OpenRAGConfig()
    config.project_root = project
    config.collection_name = collection
    if extensions:
        config.file_extensions = set(extensions)
    
    print(f"\n  Creating directories...")
    config.__post_init__()
    print(f"  ✅ Directories created")
    
    print(f"\n  Setting up logging...")
    loggers = setup_logging(config)
    logger = loggers["indexer"]
    print(f"  ✅ Logger ready")
    
    print(f"\n📋 COLLECTION INITIALIZATION")
    print("-" * 40)
    
    try:
        # Connect to ChromaDB
        print(f"  Connecting to ChromaDB...")
        collection_manager = ChromaCollectionManager(config, logger)
        print(f"  ✅ Connected")
        
        # Initialize collection
        print(f"  Initializing collection '{collection}'...")
        collection_manager.initialize_collection()
        print(f"  ✅ Collection ready")
        
        # Create watcher for initial index
        print(f"\n  Creating file watcher...")
        file_watcher = FileWatcher(config, logger, collection_manager)
        handler = file_watcher._create_handler(collection_manager)
        file_watcher.handler = handler
        print(f"  ✅ File watcher ready")
        
        # Run initial index
        print(f"\n  📊 Running initial index...")
        files = file_watcher.initial_index()
        print(f"  ✅ Indexed {files} files")
        
        # Get final stats
        info = collection_manager.get_collection_info()
        print(f"\n  📊 Collection '{collection}' now has {info['count']} documents")
        
        print(f"\n✅ Initialization complete!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
