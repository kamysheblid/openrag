"""Centralized logging configuration"""

import sys
from pathlib import Path
from loguru import logger

def setup_logging(config):
    """Setup logging - ONE logger with multiple handlers"""
    
    # ===== START FRESH =====
    logger.remove()
    
    logs_dir = Path(config.logs_dir)
    
    # ===== 1. CONSOLE OUTPUT (what you see when running) =====
    console_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[component]}</cyan> | <level>{message}</level>"
    logger.add(
        sys.stdout,
        level=config.log_level,
        format=console_format,
        colorize=True,
    )
    
    # ===== 2. CHROMA LOG FILE =====
    chroma_dir = logs_dir / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        chroma_dir / "chroma_{time:YYYY-MM-DD}.log",
        level=config.log_level,
        format="{time} | {level} | {extra[component]} | {message}",
        rotation=config.log_rotation,
        retention=config.log_retention,
        filter=lambda record: record["extra"].get("component") == "chroma",
        enqueue=True,
    )
    
    # ===== 3. INDEXER LOG FILE =====
    indexer_dir = logs_dir / "indexer"
    indexer_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        indexer_dir / "indexer_{time:YYYY-MM-DD}.log",
        level=config.log_level,
        format="{time} | {level} | {extra[component]} | {message}",
        rotation=config.log_rotation,
        retention=config.log_retention,
        filter=lambda record: record["extra"].get("component") == "indexer",
        enqueue=True,
    )
    
    # ===== 4. QUERY LOG FILE =====
    query_dir = logs_dir / "query"
    query_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        query_dir / "query_{time:YYYY-MM-DD}.log",
        level=config.log_level,
        format="{time} | {level} | {extra[component]} | {message}",
        rotation=config.log_rotation,
        retention=config.log_retention,
        filter=lambda record: record["extra"].get("component") == "query",
        enqueue=True,
    )
    
    # ===== 5. ERROR LOG FILE (ALL ERRORS) =====
    error_dir = logs_dir / "errors"
    error_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        error_dir / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time} | {level} | {extra[component]} | {message}",
        rotation=config.log_rotation,
        retention=config.log_retention,
        enqueue=True,
    )
    
    # Return BOUND loggers (these are just labels, NOT new instances)
    return {
        "chroma": logger.bind(component="chroma"),
        "indexer": logger.bind(component="indexer"),
        "query": logger.bind(component="query"),
    }
