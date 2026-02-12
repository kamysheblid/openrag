"""Process management utilities"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any


class ProcessManager:
    """Manages child processes with clean shutdown"""
    
    def __init__(self, logger):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.logger = logger
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.warning(f"Received signal {signum}, shutting down...")
        self.stop_all()
        sys.exit(0)
    
    def start(
        self,
        name: str,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path] = None,
        log_file: Optional[Path] = None,
    ) -> Optional[subprocess.Popen]:
        """Start a subprocess with logging"""
        
        self.logger.info(f"Starting {name}: {' '.join(cmd)}")
        
        # Setup environment
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)
        
        # Setup stdout/stderr
        stdout = None
        stderr = None
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            stdout = open(log_file, "a")
            stderr = subprocess.STDOUT
        
        try:
            proc = subprocess.Popen(
                cmd,
                env=proc_env,
                cwd=cwd,
                stdout=stdout,
                stderr=stderr,
                text=True,
                bufsize=1,
            )
            
            self.processes[name] = proc
            self.logger.info(f"Started {name} (PID: {proc.pid})")
            return proc
            
        except Exception as e:
            self.logger.error(f"Failed to start {name}: {e}")
            return None
    
    def stop(self, name: str, timeout: int = 10) -> bool:
        """Stop a specific process"""
        if name not in self.processes:
            return False
        
        proc = self.processes[name]
        self.logger.info(f"Stopping {name} (PID: {proc.pid})")
        
        try:
            # Try graceful shutdown
            proc.terminate()
            proc.wait(timeout=timeout)
            self.logger.info(f"Stopped {name}")
        except subprocess.TimeoutExpired:
            # Force kill
            self.logger.warning(f"{name} didn't terminate, killing...")
            proc.kill()
            proc.wait()
        except Exception as e:
            self.logger.error(f"Error stopping {name}: {e}")
        
        del self.processes[name]
        return True
    
    def stop_all(self, timeout: int = 10):
        """Stop all processes"""
        for name in list(self.processes.keys()):
            self.stop(name, timeout)
    
    def is_running(self, name: str) -> bool:
        """Check if a process is running"""
        if name not in self.processes:
            return False
        
        proc = self.processes[name]
        return proc.poll() is None
    
    @staticmethod
    def kill_existing(port: int) -> bool:
        """Kill any process using a specific port"""
        killed = False
        
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    # Skip if we can't access connections
                    if not hasattr(proc, 'connections'):
                        continue
                    
                    # Get connections with error handling
                    try:
                        connections = proc.connections(kind="inet")
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        continue
                    except Exception:
                        continue
                    
                    # Check each connection
                    for conn in connections:
                        if hasattr(conn, 'laddr') and hasattr(conn.laddr, 'port'):
                            if conn.laddr.port == port:
                                proc.kill()
                                killed = True
                                break
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except Exception:
                    continue
                    
        except ImportError:
            # Fallback to lsof
            try:
                if sys.platform in ["linux", "darwin"]:
                    result = subprocess.run(
                        f"lsof -ti :{port}",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.stdout:
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid:
                                os.kill(int(pid), signal.SIGKILL)
                                killed = True
            except:
                pass
        
        return killed
