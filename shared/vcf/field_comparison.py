from collections import defaultdict
from decimal import Decimal
from itertools import islice
from logging import Logger
import statistics
from typing import Dict, List, Tuple

from shared.util import prettify_rows


def show_categorical_comparisons(
    logger: Logger, run_ids: Tuple[str, str], category_entries: List[Tuple[str, str]], max_thres=10
):
    nbr_identical = 0

    nbr_differences: Dict[str, int] = defaultdict(int)

    for entry1, entry2 in category_entries:
        if entry1 == entry2:
            nbr_identical += 1
            continue

        combined_key = f"{entry1}___{entry2}"
        nbr_differences[combined_key] += 1

    logger.info(f"{run_ids[0]} to {run_ids[1]}")
    rows_1_to_2: List[List[str]] = [["From", "To", "Count"]]
    for key, value in islice(sorted(
        nbr_differences.items(), key=lambda pair: pair[1], reverse=True
    ), max_thres):
        from_cat, to_cat = key.split("___", 1)
        rows_1_to_2.append([from_cat, to_cat, str(value)])
    if len(nbr_differences) > max_thres:
        logger.info(f"Showing first {max_thres}")
    if len(rows_1_to_2) > 1:
        for row in prettify_rows(rows_1_to_2):
            logger.info(row)
    else:
        logger.info("No differences found")


def show_numerical_comparisons(
    logger: Logger,
    run_ids: Tuple[str, str],
    info_key: str,
    numeric_pairs: List[Tuple[Decimal, Decimal]],
    width: int = 60,
) -> None:

    v1_vals = [a for a, _ in numeric_pairs]
    v2_vals = [b for _, b in numeric_pairs]

    ident_count = sum(1 for a, b in numeric_pairs if a == b)
    diff_count = len(numeric_pairs) - ident_count

    # FIXME: Move to util location
    def median(vals: List[Decimal]) -> str:
        if len(vals) == 0:
            return "NA"
        return str(statistics.median(vals))

    def stdev(vals: List[Decimal]) -> str:
        if len(vals) < 2:
            return "NA"
        try:
            return str(statistics.stdev(vals))
        except statistics.StatisticsError:
            return "NA"

    logger.info("")
    logger.info(f"{info_key} (numeric)")
    logger.info(
        f"{run_ids[0]} -> N={len(v1_vals)} median={median(v1_vals)} stdev={stdev(v1_vals)}"
    )
    logger.info(
        f"{run_ids[1]} -> N={len(v2_vals)} median={median(v2_vals)} stdev={stdev(v2_vals)}"
    )
    logger.info(f"Identical pairs: {ident_count} Differing pairs: {diff_count}")

    # FIXME: OK, these parts will need some hands-on touch

    # FIXME: Move to util
    def safe_quantiles(vals: List[Decimal]):
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

    def _render_bar(vals: List[Decimal], vmin_all: Decimal, vmax_all: Decimal, w: int) -> str:
        if len(vals) == 0:
            return "".ljust(w)
        vmin, q1, md, q3, vmax = safe_quantiles(vals)

        if not vmin or not vmax:
            raise ValueError("Unknown situation, vmin and vmax should be non None")

        # If any are None (empty list handled above), just show median
        chars = [" "] * w
        # Whiskers: min..max as '-'
        l = scale_to_range(vmin, vmin_all, vmax_all, w)
        r = scale_to_range(vmax, vmin_all, vmax_all, w)
        if l > r:
            l, r = r, l
        for i in range(l, r + 1):
            chars[i] = "-"
        # IQR: q1..q3 as '='
        if q1 is not None and q3 is not None:
            i1 = scale_to_range(q1, vmin_all, vmax_all, w)
            i3 = scale_to_range(q3, vmin_all, vmax_all, w)
            if i1 > i3:
                i1, i3 = i3, i1
            for i in range(i1, i3 + 1):
                chars[i] = "="
        # Median as '|'
        if md is not None:
            im = scale_to_range(md, vmin_all, vmax_all, w)
            chars[im] = "|"
        return "".join(chars)

    # FIXME: Util?
    if len(v1_vals) and len(v2_vals):
        global_min = min(min(v1_vals), min(v2_vals))
        global_max = max(max(v1_vals), max(v2_vals))
    elif len(v1_vals):
        global_min = min(v1_vals)
        global_max = max(v1_vals)
    elif len(v2_vals):
        global_min = min(v2_vals)
        global_max = max(v2_vals)
    else:
        global_min = Decimal(0)
        global_max = Decimal(0)

    bar1 = _render_bar(v1_vals, global_min, global_max, width)
    bar2 = _render_bar(v2_vals, global_min, global_max, width)

    logger.info(f"{run_ids[0]} |{bar1}|")
    logger.info(f"{run_ids[1]} |{bar2}|")