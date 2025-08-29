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
    """Return value if number, else return None"""
    try:
        d = Decimal(val)
    except (InvalidOperation, TypeError):
        return None
    return d if d.is_finite() else None


def get_safe_quantiles(vals: List[Decimal]):
    if len(vals) < 2:
        md = statistics.median(vals) if len(vals) == 1 else None
        return (min(vals) if vals else None, md, md, md, max(vals) if vals else None)
    try:
        q1, q2, q3 = statistics.quantiles(vals, n=4, method="inclusive")
    except Exception:
        # Fallback: approximate using median splits
        sorted_vals = sorted(vals)
        md = statistics.median(sorted_vals)
        mid = len(sorted_vals) // 2
        lower = sorted_vals[:mid]
        upper = sorted_vals[-mid:]
        q1 = statistics.median(lower) if lower else md
        q3 = statistics.median(upper) if upper else md
        return (sorted_vals[0], q1, md, q3, sorted_vals[-1])
    md = statistics.median(vals)
    return (min(vals), q1, md, q3, max(vals))


def scale_to_range(val: Decimal, vmin: Decimal, vmax: Decimal, w: int) -> int:
    if vmin == vmax:
        return w // 2
    # Clamp within [0, w-1]
    pos = int(round((float(val - vmin) / float(vmax - vmin)) * (w - 1)))
    return max(0, min(w - 1, pos))


def render_bar(
    values: List[Decimal], view_min: Decimal, view_max: Decimal, screen_width: int
) -> str:
    if len(values) == 0:
        return "".ljust(screen_width)
    min_value, q1, median, q3, max_value = get_safe_quantiles(values)

    # Start with all positions empty
    view_chars = [" "] * screen_width
    if min_value is None or max_value is None:
        # If no end values, return an empty string
        return "".join(view_chars)

    left_value = scale_to_range(min_value, view_min, view_max, screen_width)
    right_value = scale_to_range(max_value, view_min, view_max, screen_width)

    for i in range(left_value, right_value + 1):
        view_chars[i] = " "

    # IQR: q1..q3 as '='
    if q1 is not None and q3 is not None:
        q1_view_pos = scale_to_range(q1, view_min, view_max, screen_width)
        q3_view_pos = scale_to_range(q3, view_min, view_max, screen_width)
        for i in range(q1_view_pos, q3_view_pos + 1):
            view_chars[i] = "="

    # Median as '|'
    if median is not None:
        median_view_pos = scale_to_range(median, view_min, view_max, screen_width)
        view_chars[median_view_pos] = "|"

    return "".join(view_chars)
