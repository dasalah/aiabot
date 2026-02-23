"""Configuration loader: reads YAML config files and environment variables."""
import os
import yaml
from dotenv import load_dotenv

load_dotenv()

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_DIR = os.environ.get("CONFIG_DIR", os.path.join(_BASE, "config"))


def _load_yaml(filename: str) -> dict:
    path = os.path.join(_CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# Lazy-load configs
_messages: dict | None = None
_settings: dict | None = None
_channels: dict | None = None


def get_messages() -> dict:
    global _messages
    if _messages is None:
        _messages = _load_yaml("messages.yaml")
    return _messages


def get_settings() -> dict:
    global _settings
    if _settings is None:
        _settings = _load_yaml("settings.yaml")
    return _settings


def get_channels() -> dict:
    global _channels
    if _channels is None:
        _channels = _load_yaml("channels.yaml")
    return _channels


def reload_configs():
    """Force reload all config files (useful after web panel edits)."""
    global _messages, _settings, _channels
    _messages = None
    _settings = None
    _channels = None


# Environment variables
API_ID: int = int(os.environ.get("API_ID", "0"))
API_HASH: str = os.environ.get("API_HASH", "")
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
SUPERADMIN_IDS: list[int] = [
    int(x.strip())
    for x in os.environ.get("SUPERADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]
WEB_SECRET_KEY: str = os.environ.get("WEB_SECRET_KEY", "dev-secret-key")
WEB_ADMIN_PASSWORD: str = os.environ.get("WEB_ADMIN_PASSWORD", "admin")
DATA_DIR: str = os.environ.get("DATA_DIR", os.path.join(_BASE, "data"))
