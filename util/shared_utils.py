from configparser import ConfigParser
from pathlib import Path
from typing import List, Optional


def load_config(parent_path: str, config_path: Optional[str]) -> ConfigParser:
    config = ConfigParser()
    if config_path is None:
        script_dir = Path(parent_path)
        config_path = str(script_dir / "default.config")
    config.read(config_path)
    return config


def prettify_rows(rows: List[List[str]], padding: int = 4) -> List[str]:
    column_widths = []
    for col_i in range(len(rows[0])):
        max_len = 0
        for row in rows:
            cell_length = len(row[col_i])
            if cell_length > max_len:
                max_len = cell_length
        column_widths.append(max_len + padding)

    pretty_rows = []
    for row in rows:
        adjusted_cells = [cell.ljust(column_widths[i]) for (i, cell) in enumerate(row)]
        adjusted_row = "".join(adjusted_cells)
        pretty_rows.append(adjusted_row)
    return pretty_rows


def check_valid_config_path(conf: ConfigParser, section: str, key: str) -> bool:
    repo_config = Path(conf.get(section, key))
    valid_path = repo_config.exists()
    return valid_path


def truncate_string(text: str, max_len: int) -> str:
    if len(text) > max_len:
        return text[0:max_len] + "..."
    else:
        return text
