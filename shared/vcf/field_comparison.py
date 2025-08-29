import statistics
from collections import defaultdict
from decimal import Decimal
from itertools import islice
from logging import Logger
from typing import Dict, List, Tuple

from shared.util import prettify_rows, render_bar


def show_categorical_comparisons(
    logger: Logger,
    run_ids: Tuple[str, str],
    category_entries: List[Tuple[str, str]],
    max_thres=5,
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
    for key, value in islice(
        sorted(nbr_differences.items(), key=lambda pair: pair[1], reverse=True),
        max_thres,
    ):
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
    numeric_pairs: List[Tuple[Decimal, Decimal]],
    width: int = 60,
) -> None:

    v1_vals = [a for a, _ in numeric_pairs]
    v2_vals = [b for _, b in numeric_pairs]

    ident_count = sum(1 for a, b in numeric_pairs if a == b)
    diff_count = len(numeric_pairs) - ident_count

    v1_median = statistics.median(v1_vals)
    v2_median = statistics.median(v2_vals)
    v1_stdev = round(statistics.stdev(v1_vals), 2) if len(v1_vals) >= 2 else "NA"
    v2_stdev = round(statistics.stdev(v2_vals), 2) if len(v2_vals) >= 2 else "NA"
    v1_min = min(v1_vals)
    v2_min = min(v2_vals)
    v1_max = max(v1_vals)
    v2_max = max(v2_vals)

    v1_stats_row = [
        f"{run_ids[0]}",
        f"N={len(v1_vals)}",
        f"median={v1_median}",
        f"stdev={v1_stdev}",
        f"min={v1_min}",
        f"max={v1_max}",
    ]
    v2_stats_row = [
        f"{run_ids[1]}",
        f"N={len(v2_vals)}",
        f"median={v2_median}",
        f"stdev={v2_stdev}",
        f"min={v2_min}",
        f"max={v2_max}",
    ]

    pretty_stats_rows = prettify_rows([v1_stats_row, v2_stats_row])
    for row in pretty_stats_rows:
        logger.info(row)

    logger.info(f"Identical pairs: {ident_count}, differing pairs: {diff_count}")

    all_vals = v1_vals + v2_vals
    global_min = min(all_vals)
    global_max = max(all_vals)

    bar1 = render_bar(v1_vals, global_min, global_max, width)
    bar2 = render_bar(v2_vals, global_min, global_max, width)

    bar_rows = [
        [f"{run_ids[0]}", global_min, f"|{bar1}|", global_max],
        [f"{run_ids[1]}", global_min, f"|{bar2}|", global_max],
    ]

    pretty_rows = prettify_rows(bar_rows)

    for row in pretty_rows:
        logger.info(row)
