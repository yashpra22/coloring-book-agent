"""Shared utilities for the Coloring Book Agent."""
import os
import sys
import json
import hashlib
import re
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
    """Load environment variables from .env file and the process environment."""
    env = {}

    project_root = Path(__file__).resolve().parents[1]
    env_file = Path(env_path)
    if not env_file.is_absolute():
        cwd_env = Path.cwd() / env_file
        project_env = project_root / env_file
        env_file = cwd_env if cwd_env.exists() else project_env

    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip().strip('"').strip("'")
    # Also check actual environment
    for key in ["OPENROUTER_API_KEY", "NVIDIA_API_KEY", "HF_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"]:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def sanitize_for_log(value, secrets=None, max_length: int = 600) -> str:
    """Return a compact log-safe string with API-token-looking values redacted."""
    if value is None:
        return ""
    text = str(value)
    for secret in secrets or []:
        if secret and len(secret) >= 8:
            text = text.replace(secret, "[REDACTED]")

    patterns = [
        r"sk-or-v1-[A-Za-z0-9_-]+",
        r"nvapi-[A-Za-z0-9_-]+",
        r"hf_[A-Za-z0-9_-]+",
        r"Bearer\s+[A-Za-z0-9._~+/=-]+",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)

    text = " ".join(text.split())
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def ensure_dirs(config: dict) -> None:
    """Create all output directories."""
    paths = config.get("paths", {})
    for path_key in paths.values():
        Path(path_key).mkdir(parents=True, exist_ok=True)


def get_date_str() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def prompt_hash(prompt: str) -> str:
    """Generate a short hash for a prompt (for caching)."""
    return hashlib.md5(prompt.encode()).hexdigest()[:12]


def save_json(data, filepath: str) -> None:
    """Save data as JSON."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
