from configparser import ConfigParser
from decimal import Decimal, InvalidOperation
from pathlib import Path
import statistics
from typing import Any, List, Optional


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
        adjusted_cells = [str(cell).ljust(column_widths[i]) for (i, cell) in enumerate(row)]
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


def parse_decimal(val: str) -> Optional[Decimal]:
    try:
        d = Decimal(val)
    except (InvalidOperation, TypeError):
        return None
    return d if d.is_finite() else None


def scale_value_to_screen(val: Decimal, min_value: Decimal, max_value: Decimal, screen_width: int) -> int:

    if min_value == max_value:
        return screen_width // 2

    total_range = float(max_value - min_value)
    value_from_min = float(val - min_value)
    scaled_value = (value_from_min / total_range) * (screen_width - 1)
    pos = int(round(scaled_value))
    return pos


def render_bar(
    values: List[Decimal], view_min: Decimal, view_max: Decimal, screen_width: int
) -> str:
    if len(values) == 0:
        return "".ljust(screen_width)
    q1, _q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    min_value = min(values)
    max_value = max(values)
    median_value = statistics.median(values)

    # Start with all positions empty
    view_chars = [" "] * screen_width
    if min_value is None or max_value is None:
        # If no end values, return an empty string
        return "".join(view_chars)

    left_value = scale_value_to_screen(min_value, view_min, view_max, screen_width)
    right_value = scale_value_to_screen(max_value, view_min, view_max, screen_width)

    for i in range(left_value, right_value + 1):
        view_chars[i] = " "

    # IQR: q1..q3 as '='
    if q1 is not None and q3 is not None:
        q1_view_pos = scale_value_to_screen(q1, view_min, view_max, screen_width)
        q3_view_pos = scale_value_to_screen(q3, view_min, view_max, screen_width)
        for i in range(q1_view_pos, q3_view_pos + 1):
            view_chars[i] = "="

    # Median as '|'
    if median_value is not None:
        median_view_pos = scale_value_to_screen(median_value, view_min, view_max, screen_width)
        view_chars[median_view_pos] = "|"

    return "".join(view_chars)
