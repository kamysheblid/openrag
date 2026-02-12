"""ChromaDB server management"""

import subprocess
import time
import socket
import sys
import os
import shutil
from pathlib import Path
from typing import Optional

import requests


class ChromaServer:
    """Manages ChromaDB server process"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.process = None
    
    def start(self) -> bool:
        """Start ChromaDB server"""
        from loguru import logger as loguru_logger
        self.logger = loguru_logger.bind(component="chroma")
        self.logger.level("DEBUG")

        self.logger.debug("=" * 60)
        self.logger.debug("CHROMADB STARTUP - BEGIN")
        self.logger.debug("=" * 60)
        
        self.logger.info(f"Starting ChromaDB on {self.config.chroma_host}:{self.config.chroma_port}")
        
        self.logger.debug("=== ENVIRONMENT DEBUG ===")
        self.logger.debug(f"Python executable: {sys.executable}")
        self.logger.debug(f"Python path: {sys.path}")
        self.logger.debug(f"Current working directory: {os.getcwd()}")
        self.logger.debug(f"PATH: {os.environ.get('PATH', 'NOT SET')}")

        # Check if chroma is installed
        self.logger.debug("Checking if 'chroma' command is available...")
        try:
            import shutil
            chroma_path = shutil.which("chroma")
            self.logger.debug(f"chroma command path: {chroma_path}")
            if not chroma_path:
                self.logger.error("❌ 'chroma' command not found in PATH")
                self.logger.error("   Please install chromadb: pip install chromadb")
                return False
        except Exception as e:
            self.logger.error(f"Error checking chroma command: {e}")
            return False
        
        # Kill existing process on port
        self.logger.debug(f"Checking for existing process on port {self.config.chroma_port}...")
        try:
            from openrag.utils.process import ProcessManager
            killed = ProcessManager.kill_existing(self.config.chroma_port)
            if killed:
                self.logger.debug(f"Killed existing process on port {self.config.chroma_port}")
            else:
                self.logger.debug(f"No existing process found on port {self.config.chroma_port}")
        except Exception as e:
            self.logger.debug(f"Error killing existing process (non-fatal): {e}")
        
        # Ensure data directory exists
        chroma_data_dir = self.config.data_dir / self.config.chroma_persist_dir
        self.logger.debug(f"ChromaDB data directory: {chroma_data_dir}")
        chroma_data_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Data directory exists: {chroma_data_dir.exists()}")
        
        # Create log file for ChromaDB stdout/stderr
        chroma_log_file = self.config.logs_dir / "chroma" / "chroma_process.log"
        chroma_log_file.parent.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"ChromaDB process log: {chroma_log_file}")
        
        # Prepare command
        cmd = [
            "chroma", "run",
            "--host", self.config.chroma_host,
            "--port", str(self.config.chroma_port),
            "--path", str(chroma_data_dir),
        ]
        self.logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            # Open log file for writing
            self.logger.debug("Opening log file and starting subprocess...")
            with open(chroma_log_file, "a") as log_file:
                log_file.write(f"\n{'='*60}\n")
                log_file.write(f"ChromaDB started at {time.ctime()}\n")
                log_file.write(f"Command: {' '.join(cmd)}\n")
                log_file.write(f"{'='*60}\n\n")
                log_file.flush()
                
                self.process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            self.logger.debug(f"  ⏳ Process started with PID: {self.process.pid}")
            self.logger.debug(f"  📝 Log file: {chroma_log_file}")
            self.logger.debug(f"  🔍 Will begin health checks in 3 seconds...")
            self.logger.debug(f"  ⏰ Starting health checks now")

            # Give it a moment to start
            time.sleep(2)

            # Check if the API is responding - this is the REAL test
            api_ready = self._is_api_ready()
            if not api_ready:
                # If API isn't ready, check if we can find any ChromaDB processes
                import psutil
                chroma_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if 'chroma' in ' '.join(proc.cmdline()).lower():
                            chroma_processes.append(proc)
                    except:
                        pass
                
                if chroma_processes:
                    self.logger.info(f"Found {len(chroma_processes)} ChromaDB processes running, but API not ready yet")
                    # Continue waiting - don't fail immediately
                else:
                    self.logger.error("❌ No ChromaDB processes found and API not responding")
                    
                    # Try to read the log file for errors
                    try:
                        with open(chroma_log_file, "r") as f:
                            lines = f.readlines()[-50:]
                            self.logger.error("=== CHROMADB ERROR LOG ===")
                            for line in lines:
                                self.logger.error(f"  {line.rstrip()}")
                            self.logger.error("==========================")
                    except Exception as e:
                        self.logger.error(f"Could not read log file: {e}")
                    return False

            return True
           
            self.logger.info(f"ChromaDB process started with PID: {self.process.pid}")
            self.logger.debug(f"Process poll (should be None): {self.process.poll()}")
            
            # Wait for server to be ready
            self.logger.info("Waiting for ChromaDB to be ready...")
            
            for i in range(60):
                time.sleep(1)
                
                # Check if process died
                if self.process.poll() is not None:
                    self.logger.error(f"ChromaDB process died with exit code: {self.process.poll()}")
                    
                    # Read last 20 lines of log
                    try:
                        with open(chroma_log_file, "r") as f:
                            lines = f.readlines()[-20:]
                            self.logger.error("=== Last 20 lines of ChromaDB log ===")
                            for line in lines:
                                self.logger.error(f"  {line.rstrip()}")
                            self.logger.error("========================================")
                    except Exception as e:
                        self.logger.error(f"Could not read log file: {e}")
                    
                    return False
                
                # Check if port is listening
                #port_open = self._is_port_open()
                #api_ready = self._is_api_ready() if port_open else False
                api_ready = self._is_api_ready()
                
                self.logger.debug(f"Attempt {i+1}/60 - Port open: {port_open}, API ready: {api_ready}")
                
                if port_open and api_ready:
                    self.logger.info(f"✅ ChromaDB ready on http://{self.config.chroma_host}:{self.config.chroma_port}")
                    self.logger.debug(f"ChromaDB startup complete after {i+1} seconds")
                    self.logger.debug("=" * 60)
                    return True
                
                if i % 10 == 0 and i > 0:
                    self.logger.debug(f"Still waiting for ChromaDB... ({i+1}/60)")
            
            self.logger.error("❌ ChromaDB failed to start within 60 seconds")
            self.logger.debug("=" * 60)
            return False
            
        except FileNotFoundError as e:
            self.logger.error(f"❌ Failed to start ChromaDB - command not found: {e}")
            self.logger.error("   Please install chromadb: pip install chromadb")
            return False
        except Exception as e:
            self.logger.error(f"❌ Failed to start ChromaDB: {e}", exc_info=True)
            return False
    
    def set_log_level(self, level):
        """Set the logger level"""
        self.logger.setLevel(level)
        self.logger.debug(f"ChromaServer log level set to: {level}")

    def _is_port_open(self) -> bool:
        """Check if port is listening"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((self.config.chroma_host, self.config.chroma_port))
            sock.close()
            return result == 0
        except Exception as e:
            self.logger.debug(f"Port check error: {e}")
            return False

    def _is_api_ready(self) -> bool:
        """Check if ChromaDB v2 API is responding with detailed debug logging"""
        self.logger.debug(f"🔍 API health check starting...")
        
        # Try v2 root endpoint
        v2_url = f"http://{self.config.chroma_host}:{self.config.chroma_port}/api/v2"
        self.logger.debug(f"  Checking v2 URL: {v2_url}")
        
        try:
            response = requests.get(v2_url, timeout=1)
            self.logger.debug(f"  v2 response status: {response.status_code}")
            self.logger.debug(f"  v2 response headers: {dict(response.headers)}")
            self.logger.debug(f"  v2 response body: {response.text[:200]}")
            
            if response.status_code == 200:
                self.logger.debug(f"  ✅ v2 API is ready!")
                return True
            else:
                self.logger.debug(f"  ❌ v2 API returned {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            self.logger.debug(f"  ❌ v2 connection error: {e}")
        except Exception as e:
            self.logger.debug(f"  ❌ v2 unexpected error: {e}")
        
        # Try v1 heartbeat as fallback
        v1_url = f"http://{self.config.chroma_host}:{self.config.chroma_port}/api/v1/heartbeat"
        self.logger.debug(f"  Checking v1 URL: {v1_url}")
        
        try:
            response = requests.get(v1_url, timeout=1)
            self.logger.debug(f"  v1 response status: {response.status_code}")
            
            if response.status_code == 200:
                self.logger.debug(f"  ✅ v1 API is ready!")
                return True
        except Exception as e:
            self.logger.debug(f"  ❌ v1 error: {e}")
        
        self.logger.debug(f"  ❌ All API checks failed")
        return False

    def stop(self):
        """Stop ChromaDB server"""
        if self.process:
            self.logger.info("Stopping ChromaDB...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                self.logger.info("ChromaDB stopped")
            except subprocess.TimeoutExpired:
                self.logger.warning("ChromaDB didn't terminate, killing...")
                self.process.kill()
                self.logger.info("ChromaDB killed")
