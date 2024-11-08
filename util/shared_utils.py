from configparser import ConfigParser
from pathlib import Path
from typing import Optional

def load_config(parent_path: str, config_path: Optional[str]) -> ConfigParser:
    config = ConfigParser()
    if config_path is None:
        script_dir = Path(parent_path)
        config_path = str(script_dir / "default.config")
    config.read(config_path)
    return config
