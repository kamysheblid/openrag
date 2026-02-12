"""Setup script for OpenRAG"""

from setuptools import setup, find_packages

setup(
    name="openrag",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "chromadb>=0.4.0",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "watchdog>=3.0.0",
        "sentence-transformers>=2.2.0",
        "gitignore-parser>=0.1.0",
        "httpx>=0.25.0",
        "python-multipart>=0.0.6",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "loguru>=0.7.0",
        "typer>=0.9.0",
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "openrag=openrag.cli:app",
        ],
    },
    python_requires=">=3.9",
    author="Your Name",
    description="One-command local RAG system",
    license="MIT",
)
