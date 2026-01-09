"""Configuration file handling for ICPC Audio Generator."""

from pathlib import Path
from typing import Optional

import yaml

from icpc_audio.models import Config

CONFIG_FILE_NAME = "icpc-audio.yaml"


def get_config_path(folder: Path) -> Path:
    """Get path to config file in specified folder."""
    return folder / CONFIG_FILE_NAME


def load_config(folder: Path) -> Optional[Config]:
    """Load configuration from file, or return None if not found."""
    config_path = get_config_path(folder)
    if not config_path.exists():
        return None

    with open(config_path) as f:
        data = yaml.safe_load(f)
        if data is None:
            return None
        return Config(**data)


def save_config(config: Config, folder: Path) -> Path:
    """Save configuration to file. Returns the path where it was saved."""
    config_path = get_config_path(folder)
    with open(config_path, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)
    return config_path
