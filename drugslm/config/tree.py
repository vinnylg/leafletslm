import json
import logging
from pathlib import Path
import tomllib

import yaml

from drugslm import PACKAGE_ROOT

logger = logging.getLogger(__name__)


class Config:
    """
    Represents a single configuration file.

    This class wraps a Path object pointing to a configuration file (YAML, JSON, TOML).
    It provides a `.load()` method to parse the file content into a Python dictionary or list.
    It also implements `__fspath__`, allowing the object to be treated as a standard
    path string (compatible with `open()`, `os.path`, etc.).

    Attributes:
        path (Path): The absolute path to the configuration file.
    """

    def __init__(self, path: Path):
        """
        Initializes the configuration wrapper.

        Args:
            path (Path): The file path to the configuration file.
        """
        self.path = path

    def load(self) -> dict | list:
        """
        Parses the configuration file based on its extension.

        Returns:
            dict | list: The parsed configuration data.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
            ValueError: If the file extension is not supported.
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Config file not found at: {self.path}")

        # Optional: Log debug info (can be verbose)
        # logger.debug(f"Loading configuration from: {self.path}")

        if self.path.suffix in [".yaml", ".yml"]:
            with open(self.path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

        elif self.path.suffix == ".json":
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)

        elif self.path.suffix == ".toml":
            with open(self.path, "rb") as f:
                return tomllib.load(f)

        raise ValueError(f"Unsupported configuration format: {self.path.suffix}")

    def __str__(self) -> str:
        """Returns the absolute path as a string."""
        return str(self.path.absolute())

    def __repr__(self) -> str:
        """Returns a string representation for debugging purposes."""
        return f"<Config: {self.path.name}>"

    def __fspath__(self) -> str:
        """
        Allows the object to be used directly in file system operations.
        Example: open(settings.browsers.firefox) works because of this.
        """
        return str(self.path)


class ConfigTree:
    """
    Recursively scans the configuration directory and creates a dynamic attribute tree.

    This class mirrors the file system structure of the 'config' folder.
    Subdirectories become nested `ConfigTree` objects, and files become `Config` objects.

    Usage:
        If the file structure is: drugslm/config/browsers/firefox.yaml
        Access it via: settings.browsers.firefox
    """

    def __init__(self, root_path: Path = PACKAGE_ROOT / "config"):
        """
        Initializes the configuration tree.

        Args:
            root_path (Path): The root directory to scan for configurations. Defaults: PACKAGE_ROOT / "config"
        """
        self._root = root_path
        self._load_structure()

    def _load_structure(self):
        """
        Iterates over the directory and dynamically sets attributes for files and folders.
        Skips hidden files (starting with '.') and Python dunder files (starting with '__').
        """
        if not self._root.exists():
            return

        for path in self._root.iterdir():
            key = path.stem  # Filename without extension (e.g., 'firefox')

            # Skip hidden files and python internal files
            if key.startswith(".") or key.startswith("__"):
                continue

            if path.is_dir():
                # Recursively create a tree for subdirectories
                setattr(self, key, ConfigTree(path))
            elif path.suffix in [".yaml", ".yml", ".json", ".toml"]:
                # Wrap supported config files with Config
                setattr(self, key, Config(path))

    def __repr__(self) -> str:
        return f"<ConfigTree at {self._root}>"


# Singleton Instantiation
default_configs = ConfigTree()

__all__ = [
    "default_configs",
]
