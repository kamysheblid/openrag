# OpenRAG 🚀

**One-command local RAG system for codebases**

OpenRAG is a zero-configuration, self-contained RAG (Retrieval Augmented Generation) system that automatically indexes your codebase and provides a query API. It runs entirely locally, respects `.gitignore`, and requires no cloud services.

```bash
# One command to start everything
openrag up --project /path/to/your/code

# That's it. Your code is now searchable.
```

---

## ✨ Features

- **⚡ One-command setup** - `openrag up` starts ChromaDB, auto-indexer, and query server
- **📁 Automatic gitignore support** - Respects all `.gitignore` files, including nested ones
- **🔄 Real-time indexing** - File changes are indexed instantly via watchdog
- **🗂️ Smart chunking** - Configurable chunk size and overlap for optimal retrieval
- **🔌 Query API** - FastAPI endpoint for Open WebUI and other tools
- **📊 Separate rotating logs** - Each component has its own log file with rotation
- **🎯 Language detection** - Automatic detection of 30+ programming languages
- **🚫 Zero cloud dependencies** - Everything runs locally
- **📦 No Docker required** - Pure Python, runs anywhere
- **💾 Persistent storage** - Index survives restarts
- **🔧 Fully configurable** - CLI args, config files, or environment variables

---

## 📋 Requirements

- Python 3.9+
- 4GB RAM recommended (2GB minimum)
- ~1GB disk space for models

---

## 🚀 Quick Start

### Installation

```bash
# Install from source
git clone https://github.com/kamysheblid/openrag.git
cd openrag
pip install -e .
```

### Start indexing your code

```bash
# Index your current directory
openrag up

# Index a specific project
openrag up --project /path/to/project

# Index with custom settings
openrag up \
  --project ./my-project \
  --collection my_code \
  --extensions .go .js .tsx .sql \
  --exclude-dirs node_modules dist build
```

### Check status

```bash
openrag status
```

### Stop everything

```bash
openrag down
```

---

## 🔧 Configuration

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project, -p` | Path to codebase | Current directory |
| `--collection, -c` | ChromaDB collection name | `code_rag` |
| `--chroma-host` | ChromaDB host | `localhost` |
| `--chroma-port` | ChromaDB port | `8001` |
| `--query-host` | Query server host | `localhost` |
| `--query-port` | Query server port | `8765` |
| `--extensions, -e` | File extensions to index | 30+ languages |
| `--exclude-dirs` | Directories to exclude | `node_modules`, `.git`, etc |
| `--chunk-size` | Chunk size in characters | `1000` |
| `--chunk-overlap` | Chunk overlap | `200` |
| `--log-level` | Log level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `--quiet, -q` | Suppress stdout logging | `False` |
| `--no-chroma` | Don't start ChromaDB | `False` |
| `--no-indexer` | Don't start auto-indexer | `False` |
| `--no-query` | Don't start query server | `False` |
| `--no-initial-index` | Skip initial full index | `False` |
| `--save-config` | Save configuration to file | `None` |
| `--config` | Load configuration from file | `None` |

### Configuration File

Save your settings for reuse:

```bash
# Save configuration
openrag up --project . --save-config my-project.json

# Use saved configuration
openrag up --config my-project.json
```

---

## 🎯 Usage Examples

### Basic Go + React Project

```bash
openrag up \
  --project /path/to/project \
  --extensions .go .js .jsx .ts .tsx .sql \
  --exclude-dirs node_modules dist build
```

### Large Codebase with Custom Chunking

```bash
openrag up \
  --project ~/projects/monorepo \
  --chunk-size 1500 \
  --chunk-overlap 300 \
  --batch-size 50 \
  --log-level INFO
```

### Headless Mode (Server Only)

```bash
openrag up \
  --project /var/www/app \
  --no-initial-index \
  --quiet \
  --log-file /var/log/openrag.log
```

### Initialize Without Watching

```bash
# One-time index, then exit
openrag init --project ./docs --collection docs_rag
```

---

## 🔌 Connecting to Open WebUI

1. **Start OpenRAG:**
   ```bash
   openrag up --project ./your-codebase
   ```

2. **In Open WebUI, add an external tool:**
   - URL: `http://localhost:8765`
   - Name: `Codebase RAG`

3. **Query your codebase:**
   ```
   @Codebase RAG How is authentication implemented?
   ```

---

## 📁 Project Structure

```
~/.openrag/
├── data/
│   └── chroma_data/     # Vector database
└── logs/
    ├── chroma/          # ChromaDB logs (rotating)
    ├── indexer/         # Auto-indexer logs (rotating)
    └── query/           # Query server logs (rotating)
```

---

## 🛠️ Development

```bash
# Install in development mode
git clone https://github.com/kamysheblid/openrag.git
cd openrag
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black openrag/
isort openrag/
```

---

## 📊 Performance Tips

- **First run** - Allow 1-2 minutes for the embedding model to download
- **Large codebases** - Use `--no-initial-index` and let the watcher index gradually
- **Memory usage** - Reduce `--batch-size` to 50 on low-memory systems
- **SSD recommended** - ChromaDB performs best on fast storage

---

## ❓ Troubleshooting

### "ModuleNotFoundError: No module named 'openrag'"
```bash
# Make sure you're in the right directory and run:
pip install -e .
```

### "Connection refused" errors
```bash
# Check if ChromaDB is running
openrag status

# Kill stuck processes and restart
openrag down
openrag up
```

### Nothing is being indexed
```bash
# Check if your file extensions are included
openrag up --project . --extensions .go .js .py

# Check gitignore exclusions
openrag up --project . --log-level DEBUG
```

### Embedding function conflict
This is fixed in OpenRAG - the query server uses the persisted embedding function automatically.

---

## 🗺️ Roadmap

- [x] Automatic gitignore support
- [x] Separate rotating logs per component
- [x] Configuration save/load
- [x] Real-time file watching
- [ ] Multiple collection support
- [ ] Web UI dashboard
- [ ] Incremental backup/restore
- [ ] Embedding model selection
- [ ] Hybrid search (BM25 + vector)

---

## 📄 License

MIT License - feel free to use this in personal and commercial projects.

---

## 🙏 Acknowledgments

- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Sentence Transformers](https://www.sbert.net/) - Embedding models
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [Watchdog](https://github.com/gorakhargosh/watchdog) - File system monitoring
- [Open WebUI](https://github.com/open-webui/open-webui) - Frontend integration

---

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/kamysheblid/openrag/issues)
- **Discussions:** [GitHub Discussions](https://github.com/kamysheblid/openrag/discussions)

---

**Made with ❤️ for local RAG**
```
