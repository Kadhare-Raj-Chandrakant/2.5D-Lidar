"""Configuration loader."""
import yaml
from pathlib import Path
from typing import Any, Dict
import os


class Config:
    """Singleton configuration manager."""
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str = None):
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = os.environ.get(
                "AV_CONFIG",
                str(Path(__file__).parent.parent / "config" / "settings.yaml")
            )
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key (e.g., 'simulation.fps')."""
        if not self._config:
            self.load()
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def __getattr__(self, name: str) -> Any:
        return self.get(name)


config = Config()