"""Code file processing and chunking"""

import os
import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add this import at the top
try:
    import gitignore_parser
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gitignore-parser"])
    import gitignore_parser


class CodeProcessor:
    """Process code files into chunks with metadata"""
    
    def __init__(self, config, logger):
        self.logger = logger
        self.logger.debug("=" * 60)
        self.logger.debug("CODEPROCESSOR INIT - START")
        self.logger.debug("=" * 60)
        
        self.config = config
        self.logger.debug(f"Config loaded: chunk_size={config.chunk_size}, overlap={config.chunk_overlap}")
        self.logger.debug(f"Project root: {config.project_root}")
        self.logger.debug(f"File extensions: {sorted(config.file_extensions)}")
        self.logger.debug(f"Exclude dirs: {sorted(config.exclude_dirs)}")
        self.logger.debug(f"Exclude files: {sorted(config.exclude_files)}")
        self.logger.debug(f"Ignore hidden: {config.ignore_hidden}")
        
        self.gitignore_rules = []
        self.logger.debug("Gitignore rules initialized empty")
        
        self._load_gitignore_rules()
        self.logger.debug("=" * 60)
        self.logger.debug("CODEPROCESSOR INIT - COMPLETE")
        self.logger.debug("=" * 60)
    
    def _load_gitignore_rules(self):
        """Load all .gitignore files from the project"""
        self.logger.debug("=" * 60)
        self.logger.debug("LOAD GITIGNORE RULES - START")
        self.logger.debug("=" * 60)
        
        self.gitignore_rules = []
        
        self.logger.debug(f"Scanning for .gitignore files in {self.config.project_root}")
        gitignore_count = 0
        
        for root, dirs, files in os.walk(self.config.project_root):
            self.logger.debug(f"Scanning directory: {root}")
            self.logger.debug(f"  Dirs found: {len(dirs)}")
            self.logger.debug(f"  Files found: {len(files)}")
            
            if '.gitignore' in files:
                gitignore_path = Path(root) / '.gitignore'
                self.logger.debug(f"Found .gitignore at: {gitignore_path}")
                try:
                    self.logger.debug(f"Parsing .gitignore file...")
                    matches = gitignore_parser.parse_gitignore(
                        str(gitignore_path),
                        base_dir=str(root)
                    )
                    self.gitignore_rules.append((Path(root), matches))
                    gitignore_count += 1
                    self.logger.debug(f"✅ Loaded .gitignore from: {gitignore_path}")
                    self.logger.debug(f"  Total rules loaded: {gitignore_count}")
                except Exception as e:
                    self.logger.debug(f"⚠️  Error loading {gitignore_path}: {e}")
        
        self.logger.debug(f"✅ Loaded {gitignore_count} .gitignore files total")
        self.logger.debug("=" * 60)
        self.logger.debug("LOAD GITIGNORE RULES - COMPLETE")
        self.logger.debug("=" * 60)
    
    def reload_gitignore_rules(self):
        """Reload .gitignore files (call when .gitignore changes)"""
        self.logger.debug("=" * 60)
        self.logger.debug("RELOAD GITIGNORE RULES - START")
        self.logger.debug("=" * 60)
        
        self._load_gitignore_rules()
        
        self.logger.debug("🔄 Reloaded .gitignore rules")
        self.logger.debug("=" * 60)
        self.logger.debug("RELOAD GITIGNORE RULES - COMPLETE")
        self.logger.debug("=" * 60)
    
    def should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored"""
        self.logger.debug(f"🔍 SHOULD_IGNORE CHECK - File: {file_path}")
        
        rel_path = str(file_path.relative_to(self.config.project_root))
        self.logger.debug(f"  Relative path: {rel_path}")
        
        # 1. Check excluded directories from config
        self.logger.debug(f"  Checking exclude_dirs: {sorted(self.config.exclude_dirs)}")
        for exclude_dir in self.config.exclude_dirs:
            if f"/{exclude_dir}/" in f"/{rel_path}/" or rel_path.startswith(f"{exclude_dir}/"):
                self.logger.debug(f"  🚫 Excluded by directory pattern: {exclude_dir}")
                return True
        
        # 2. Check excluded file patterns from config
        self.logger.debug(f"  Checking exclude_files patterns: {sorted(self.config.exclude_files)}")
        for pattern in self.config.exclude_files:
            if fnmatch.fnmatch(file_path.name, pattern):
                self.logger.debug(f"  🚫 Excluded by filename pattern: {pattern} matches {file_path.name}")
                return True
            if fnmatch.fnmatch(rel_path, pattern):
                self.logger.debug(f"  🚫 Excluded by path pattern: {pattern} matches {rel_path}")
                return True
        
        # 3. Skip hidden files if configured
        if self.config.ignore_hidden and file_path.name.startswith('.'):
            self.logger.debug(f"  🚫 Excluded by hidden file rule: {file_path.name}")
            return True
        
        # 4. Check .gitignore rules
        self.logger.debug(f"  Checking {len(self.gitignore_rules)} .gitignore rule sets")
        for gitignore_dir, matcher in self.gitignore_rules:
            if str(file_path).startswith(str(gitignore_dir)):
                self.logger.debug(f"  File is under gitignore dir: {gitignore_dir}")
                try:
                    if matcher(str(file_path)):
                        self.logger.debug(f"  🚫 Excluded by .gitignore rule")
                        return True
                except Exception as e:
                    self.logger.debug(f"  ⚠️ Error applying gitignore matcher: {e}")
        
        self.logger.debug(f"  ✅ File passes all ignore checks")
        return False
    
    def is_code_file(self, file_path: Path) -> bool:
        """Check if file is a code file we want to index"""
        self.logger.debug(f"🔍 IS_CODE_FILE CHECK - File: {file_path}")
        
        if not file_path.is_file():
            self.logger.debug(f"  ❌ Not a file (is directory or missing)")
            return False
        
        ext = file_path.suffix.lower()
        self.logger.debug(f"  Extension: '{ext}'")
        
        result = ext in self.config.file_extensions
        self.logger.debug(f"  {'✅' if result else '❌'} Extension {ext} in allowed set: {result}")
        
        return result
    
    def detect_language(self, file_path: Path) -> str:
        """Detect programming language from extension"""
        ext = file_path.suffix.lower()
        self.logger.debug(f"🔍 DETECT LANGUAGE - Extension: '{ext}'")
        
        language_map = {
            '.go': 'go', '.js': 'javascript', '.jsx': 'react',
            '.ts': 'typescript', '.tsx': 'react-typescript', '.sql': 'sql',
            '.py': 'python', '.rb': 'ruby', '.php': 'php', '.java': 'java',
            '.rs': 'rust', '.cpp': 'cpp', '.c': 'c', '.h': 'c',
            '.hpp': 'cpp', '.cs': 'csharp', '.swift': 'swift',
            '.kt': 'kotlin', '.r': 'r', '.jl': 'julia',
            '.yml': 'yaml', '.yaml': 'yaml', '.json': 'json',
            '.toml': 'toml', '.md': 'markdown', '.html': 'html',
            '.css': 'css', '.scss': 'scss', '.sh': 'bash', '.bash': 'bash',
            '.env': 'dotenv', '.conf': 'config', '.txt': 'text'
        }
        
        language = language_map.get(ext, 'text')
        self.logger.debug(f"  Detected language: {language}")
        return language
    

    def chunk_content(self, content: str) -> List[str]:
        """Split file content into overlapping chunks"""
        self.logger.debug("=" * 60)
        self.logger.debug("CHUNK CONTENT - START")
        self.logger.debug("=" * 60)
        
        content_length = len(content)
        self.logger.debug(f"Content length: {content_length} bytes")
        self.logger.debug(f"Chunk size: {self.config.chunk_size}")
        self.logger.debug(f"Chunk overlap: {self.config.chunk_overlap}")
        
        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        start = 0
        iteration = 0
        last_start = -1  # Track previous start to detect infinite loop
        
        while start < len(content):
            # SAFETY CHECK - Prevent infinite loop
            if start == last_start:
                self.logger.error(f"❌ Infinite loop detected! start={start} is not advancing. Breaking.")
                break
            
            last_start = start
            iteration += 1
            end = min(start + chunk_size, len(content))
            
            self.logger.debug(f"  Iteration {iteration}: start={start}, end={end}")
            
            # Try to end at a newline
            if end < len(content):
                newline_pos = content.rfind('\n', start, end)
                if newline_pos > start:
                    self.logger.debug(f"    Adjusted end to newline at {newline_pos}")
                    end = newline_pos + 1
            
            chunk = content[start:end].strip()
            chunk_len = len(chunk)
            
            if chunk_len > 50:
                chunks.append(chunk)
                self.logger.debug(f"    ✅ Added chunk {len(chunks)} ({chunk_len} chars)")
            
            # CRITICAL FIX - Ensure start always advances
            new_start = end - overlap
            if new_start <= start:
                # If we're not advancing, force advance by 1
                self.logger.debug(f"    ⚠️ Start not advancing ({new_start} <= {start}), forcing +1")
                start = end + 1
            else:
                start = new_start
            
            self.logger.debug(f"    Next start position: {start}")
            
            # SAFETY CHECK - Prevent too many iterations
            if iteration > content_length:
                self.logger.error(f"❌ Too many iterations ({iteration}), breaking")
                break
        
        self.logger.debug(f"✅ Created {len(chunks)} total chunks in {iteration} iterations")
        self.logger.debug("=" * 60)
        self.logger.debug("CHUNK CONTENT - COMPLETE")
        self.logger.debug("=" * 60)
        
        return chunks if chunks else [content[:chunk_size]]

    def process_file(self, file_path: Path) -> Optional[List[Dict[str, Any]]]:
        """Process a single file into chunks with metadata"""
        self.logger.debug("=" * 60)
        self.logger.debug("PROCESS FILE - START")
        self.logger.debug("=" * 60)
        self.logger.debug(f"File path: {file_path}")
        
        try:
            # Read file
            self.logger.debug(f"📖 Reading file...")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content_length = len(content)
            self.logger.debug(f"✅ Read {content_length} bytes")
            
            if not content.strip():
                self.logger.debug(f"⚠️ File is empty or whitespace only, skipping")
                return None
            
            rel_path = str(file_path.relative_to(self.config.project_root))
            self.logger.debug(f"Relative path: {rel_path}")
            
            language = self.detect_language(file_path)
            ext = file_path.suffix.lower()
            self.logger.debug(f"Language: {language}, Extension: {ext}")
            
            # Chunk content
            self.logger.debug(f"✂️ Chunking content...")
            chunks = self.chunk_content(content)
            self.logger.debug(f"✅ Created {len(chunks)} chunks")
            
            results = []
            self.logger.debug(f"🏗️ Building metadata for {len(chunks)} chunks...")
            
            for i, chunk in enumerate(chunks):
                if i % 10 == 0 or i == len(chunks) - 1:
                    self.logger.debug(f"  Processing chunk {i+1}/{len(chunks)}")
                
                result = {
                    "document": chunk,
                    "metadata": {
                        "source": rel_path,
                        "filename": file_path.name,
                        "extension": ext,
                        "language": language,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "directory": str(file_path.parent.relative_to(self.config.project_root)),
                    },
                    "id": f"{rel_path}_{i}"
                }
                results.append(result)
            
            self.logger.debug(f"✅ Built {len(results)} chunk records")
            self.logger.debug(f"📊 First chunk ID: {results[0]['id'] if results else 'None'}")
            self.logger.debug(f"📊 First chunk size: {len(results[0]['document']) if results else 0} chars")
            
            self.logger.debug("=" * 60)
            self.logger.debug("PROCESS FILE - COMPLETE - SUCCESS")
            self.logger.debug("=" * 60)
            
            return results
            
        except UnicodeDecodeError:
            self.logger.debug(f"⚠️ Skipping binary file (Unicode decode error): {file_path}")
            self.logger.debug("=" * 60)
            self.logger.debug("PROCESS FILE - COMPLETE - BINARY SKIPPED")
            self.logger.debug("=" * 60)
            return None
        except Exception as e:
            self.logger.error(f"❌ Error processing {file_path}: {e}", exc_info=True)
            self.logger.debug("=" * 60)
            self.logger.debug("PROCESS FILE - COMPLETE - ERROR")
            self.logger.debug("=" * 60)
            return None
