import sys
import os
from pathlib import Path
from typing import Union


def get_project_root() -> Path:
    """
    Get project root directory that works for:
    - Development: when running from any subdirectory
    - PyInstaller: when running as exe
    - Any other deployment scenario
    """
    # If running as exe (PyInstaller)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    # If running in development
    current_file = Path(__file__).resolve()

    # Navigate from src/type_speech/utils.py to project root
    # utils.py -> type_speech/ -> src/ -> project_root
    project_root = current_file.parents[2]

    return project_root


def get_config_path() -> Path:
    """Get path to config directory"""
    return get_project_root() / "config"


def get_credentials_path() -> Path:
    """Get path to credentials directory"""
    return get_project_root() / "credentials"


def resolve_path(relative_path: Union[str, Path]) -> Path:
    """
    Resolve relative path from project root.
    Works for any file in the project structure.
    """
    if os.path.isabs(relative_path):
        return Path(relative_path)

    return get_project_root() / relative_path
