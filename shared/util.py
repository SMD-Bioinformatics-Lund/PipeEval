import logging
from configparser import ConfigParser
from pathlib import Path
from typing import Any, List, Optional


# def load_config(
#     logger: logging.Logger, parent_path: str, config_path: Optional[str]
# ) -> ConfigParser:
#     config = ConfigParser()
#     if config_path is None:
#         script_dir = Path(parent_path)
#         config_path = str(script_dir / "default.config")
#         logger.info(
#             f"No config path supplied, attempting to read from: {str(config_path)}"
#         )

#     if not Path(config_path).exists():
#         raise ValueError(
#             f"A valid config must be provided. No config file found in path: {config_path}."
#         )

#     config.read(config_path)
#     return config


def prettify_rows(rows: List[List[Any]], padding: int = 4) -> List[str]:
    column_widths: List[int] = []
    for col_i in range(len(rows[0])):
        max_len = 0
        for row in rows:
            cell_length = len(str(row[col_i]))
            if cell_length > max_len:
                max_len = cell_length
        column_widths.append(max_len + padding)

    pretty_rows: List[str] = []
    for row in rows:
        adjusted_cells = [
            str(cell).ljust(column_widths[i]) for (i, cell) in enumerate(row)
        ]
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
