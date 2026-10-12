"""Shared utilities for the Coloring Book Agent."""
import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime

from loguru import logger


def setup_logging(log_dir: str = "logs") -> None:
    """Configure loguru for file + console logging."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO",
    )
    logger.add(
        os.path.join(log_dir, "coloring_book_{time:YYYY-MM-DD}.log"),
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    )


def load_config(config_path: str = "config/settings.yaml") -> dict:
    """Load YAML configuration."""
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_themes(themes_path: str = "config/themes.yaml") -> dict:
    """Load themes YAML."""
    import yaml
    with open(themes_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_env(env_path: str = ".env") -> dict:
    """Load environment variables from .env file."""
    env = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    # Also check actual environment
    for key in ["OPENROUTER_API_KEY", "NVIDIA_API_KEY", "HF_TOKEN"]:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def ensure_dirs(config: dict) -> None:
    """Create all output directories."""
    paths = config.get("paths", {})
    for path_key in paths.values():
        Path(path_key).mkdir(parents=True, exist_ok=True)


def get_date_str() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def get_timestamp() -> str:
    """Get current timestamp for unique filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def prompt_hash(prompt: str) -> str:
    """Generate a short hash for a prompt (for caching)."""
    return hashlib.md5(prompt.encode()).hexdigest()[:12]


def save_json(data, filepath: str) -> None:
    """Save data as JSON."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(filepath: str):
    """Load JSON data."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
