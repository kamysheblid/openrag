"""File system watcher for auto-indexing"""

import time
import os
from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from openrag.indexer.processor import CodeProcessor
from openrag.chroma.manager import ChromaCollectionManager


class CodeIndexerHandler(FileSystemEventHandler):
    """Handles file system events and updates ChromaDB"""
    
    def __init__(self, config, logger, collection_manager: ChromaCollectionManager):
        super().__init__()
        self.config = config
        self.logger = logger
        self.processor = CodeProcessor(config, logger)
        self.collection_manager = collection_manager
        self.stats = {"indexed": 0, "errors": 0, "deleted": 0, "skipped": 0}
        
        # Log initial stats
        self.logger.debug("CodeIndexerHandler initialized")
        self.logger.debug(f"File extensions: {sorted(config.file_extensions)}")
        self.logger.debug(f"Exclude dirs: {sorted(config.exclude_dirs)}")
        self.logger.debug(f"Log level: {config.log_level}")
    
    def _handle_gitignore_change(self, file_path: Path):
        """Reload gitignore rules when .gitignore changes"""
        if file_path.name == '.gitignore':
            self.logger.info(f"📋 .gitignore changed, reloading rules...")
            self.processor.reload_gitignore_rules()
            self.logger.debug("Gitignore rules reloaded")
    
    def index_file(self, file_path: Path):
        """Index a single file"""
        try:
            self.logger.debug(f"Processing file: {file_path}")
            
            if not self.processor.is_code_file(file_path):
                self.logger.debug(f"Not a code file (extension not in list): {file_path.suffix}")
                self.stats["skipped"] += 1
                return
            
            if self.processor.should_ignore(file_path):
                rel_path = str(file_path.relative_to(self.config.project_root))
                self.logger.debug(f"Ignored by gitignore/exclude rules: {rel_path}")
                self.stats["skipped"] += 1
                return
            
            # Process file into chunks
            chunks = self.processor.process_file(file_path)
            if not chunks:
                self.logger.debug(f"No chunks generated from: {file_path}")
                return
            
            # Delete existing entries for this file
            rel_path = str(file_path.relative_to(self.config.project_root))
            deleted = self.collection_manager.delete_by_source(rel_path)
            if deleted > 0:
                self.logger.debug(f"Deleted {deleted} existing chunks for: {rel_path}")
            
            # Add new chunks
            documents = [c["document"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            ids = [c["id"] for c in chunks]
            
            self.collection_manager.add_documents(documents, metadatas, ids)

            self.stats["indexed"] += 1
            self.logger.info(f"✅ Indexed {len(chunks)} chunks from: {rel_path}")

            # Log sample of first chunk in debug mode
            if self.config.log_level == "DEBUG":
                self.logger.debug(f"First 100 chars: {documents[0][:100].replace(chr(10), ' ')}...")
            
            # FREE MEMORY - clear chunks
            del chunks
            del metadatas
            del ids
            del documents
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"❌ Error indexing {file_path}: {e}", exc_info=True)
    
    def remove_file(self, file_path: Path):
        """Remove file from index"""
        try:
            rel_path = str(file_path.relative_to(self.config.project_root))
            count = self.collection_manager.delete_by_source(rel_path)
            if count > 0:
                self.stats["deleted"] += 1
                self.logger.info(f"🗑️  Removed {count} chunks from: {rel_path}")
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"❌ Error removing {file_path}: {e}", exc_info=True)
    
    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            file_path = Path(event.src_path)
            self.logger.debug(f"File modified: {file_path}")
            self._handle_gitignore_change(file_path)
            self.index_file(file_path)
    
    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            file_path = Path(event.src_path)
            self.logger.debug(f"File created: {file_path}")
            self._handle_gitignore_change(file_path)
            self.index_file(file_path)
    
    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            file_path = Path(event.src_path)
            self.logger.debug(f"File deleted: {file_path}")
            self._handle_gitignore_change(file_path)
            self.remove_file(file_path)
    
    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            self.logger.debug(f"File moved: {event.src_path} -> {event.dest_path}")
            self._handle_gitignore_change(Path(event.src_path))
            self._handle_gitignore_change(Path(event.dest_path))
            self.remove_file(Path(event.src_path))
            self.index_file(Path(event.dest_path))


class FileWatcher:
    """Watches file system for changes and triggers indexing"""
    
    def __init__(self, config, logger, collection_manager):
        self.config = config
        self.logger = logger
        self.collection_manager = collection_manager
        self.observer = None
        self.handler = None
        
        self.logger.debug("FileWatcher initialized")
    
    def _create_handler(self, collection_manager):
        """Create the event handler"""
        return CodeIndexerHandler(
            self.config,
            self.logger,
            collection_manager
        )
    
    def start(self):
        """Start watching file system"""
        self.logger.info(f"👀 Watching for changes in: {self.config.project_root}")
        
        self.handler = self._create_handler(self.collection_manager)
        
        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(self.config.project_root),
            recursive=self.config.recursive
        )
        self.observer.start()
        
        self.logger.debug(f"File watcher started (recursive={self.config.recursive})")
        return self.handler
    
    def stop(self):
        """Stop watching"""
        if self.observer:
            self.logger.info("Stopping file watcher...")
            self.observer.stop()
            self.observer.join()
            self.logger.info("File watcher stopped")

    def initial_index(self):
        """Perform initial full index with EXTREME memory efficiency"""
        self.logger.info("📊 Performing initial full index (EXTREME memory saving mode)...")
        self.logger.info(f"🔍 Searching for files in: {self.config.project_root}")
        self.logger.info(f"🔍 File extensions: {self.config.file_extensions}")

        import os
        self.logger.info(f"🔍 Current directory: {os.getcwd()}")
        self.logger.info(f"🔍 Project exists? {os.path.exists(self.config.project_root)}")
        self.logger.info(f"🔍 Project is dir? {os.path.isdir(self.config.project_root)}")
        
        # Count files first to see if any are found
        file_count = 0
        for root, dirs, files in os.walk(self.config.project_root):
            dirs[:] = [d for d in dirs if d not in self.config.exclude_dirs]
            file_count += len(files)
        self.logger.info(f"🔍 Total files in project (pre-filter): {file_count}")
        
        # Don't collect all files first - stream them
        files_found = 0
        chunks_total = 0
        start_time = time.time()
        
        # Process files immediately, one at a time
        for root, dirs, files in os.walk(self.config.project_root):
            dirs[:] = [d for d in dirs if d not in self.config.exclude_dirs]
            
            for file in files:
                file_path = Path(root) / file
                
                if not self.handler.processor.is_code_file(file_path):
                    continue
                if self.handler.processor.should_ignore(file_path):
                    continue
                
                # Process ONE file, add to ChromaDB, THEN FREE MEMORY
                self.logger.info(f"🔧 Processing file: {file_path.relative_to(self.config.project_root)}")
                chunks = self.handler.processor.process_file(file_path)
                if chunks:
                    rel_path = str(file_path.relative_to(self.config.project_root))

                    # Log every file when in DEBUG mode
                    if self.config.log_level == "DEBUG":
                        self.logger.debug(f"📄 Indexing: {rel_path}")
                    
                    # Batch size of 1 - slow but memory safe
                    self.handler.collection_manager.add_documents(
                        [c["document"] for c in chunks],
                        [c["metadata"] for c in chunks],
                        [c["id"] for c in chunks]
                    )
                    
                    files_found += 1
                    chunks_total += len(chunks)
                    
                    # Force garbage collection EVERY file
                    import gc
                    gc.collect()
                    
                    # Show progress every file for DEBUG, or every 10 files otherwise
                    if self.config.log_level == "DEBUG" or files_found % 10 == 0:
                        elapsed = time.time() - start_time
                        rate = files_found / elapsed if elapsed > 0 else 0
                        self.logger.info(f"  Progress: {files_found} files, {chunks_total} chunks ({rate:.1f} files/sec)")
        
        elapsed = time.time() - start_time
        self.logger.info(f"✅ Initial indexing complete! Indexed {files_found} files, {chunks_total} chunks in {elapsed:.1f} seconds")
        if self.config.log_level == "DEBUG":
            self.logger.debug(f"📊 Stats - Indexed: {self.handler.stats['indexed']}, Skipped: {self.handler.stats['skipped']}, Errors: {self.handler.stats['errors']}")
        return files_found
