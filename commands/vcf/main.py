import argparse
from pathlib import Path
import logging
from typing import List, Optional

from shared.vcf.main_functions import (
    variant_comparisons,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main(
    vcf1: Path,
    vcf2: Path,
    is_sv: bool,
    max_display: int,
    max_checked_annots: int,
    score_threshold: int,
    run_id1: Optional[str],
    run_id2: Optional[str],
    results: Optional[Path],
    annotations: List[str],
):
    show_line_numbers = True
    out_path_presence = results / "presence.txt" if results else None

    if run_id1 is None:
        run_id1 = str(vcf1).split("/")[-1].split(".")[0]
        logger.info(f"# --run_id1 not set, assigned: {run_id1}")

    if run_id2 is None:
        run_id2 = str(vcf2).split("/")[-1].split(".")[0]
        if run_id1 == run_id2:
            run_id2 = run_id2 + "_2"
        logger.info(f"# --run_id2 not set, assigned: {run_id2}")

    out_path_score_above_thres = results / "above_thres.txt" if results else None
    out_path_score_all = results / "score_all.txt" if results else None

    do_score_check = True
    do_annot_check = True
    variant_comparisons(
        logger,
        run_id1,
        run_id2,
        vcf1,
        vcf2,
        is_sv,
        score_threshold,
        max_display,
        max_checked_annots,
        out_path_presence,
        out_path_score_above_thres,
        out_path_score_all,
        do_score_check,
        do_annot_check,
        show_line_numbers,
        annotations if annotations is not None else [],
    )


def main_wrapper(args: argparse.Namespace):

    main(
        args.vcf1,
        args.vcf2,
        args.is_sv,
        args.score_threshold,
        args.max_checked_annots,
        args.max_display,
        args.id1,
        args.id2,
        args.results if args.results is not None else None,
        args.annotations.split(",") if args.annotations is not None else [],
    )


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--vcf1", "-1", required=True, type=Path, help="VCF to compare in .vcf or .vcf.gz format"
    )
    parser.add_argument(
        "--vcf2", "-2", required=True, type=Path, help="VCF to compare in .vcf or .vcf.gz format"
    )
    parser.add_argument("--id1", help="Optional run ID for first vcf")
    parser.add_argument("--id2", help="Optional run ID for second vcf")
    parser.add_argument("--is_sv", action="store_true", help="Process VCF in SV mode")
    parser.add_argument("--results", type=Path, help="Optional results folder")
    parser.add_argument(
        "--score_threshold",
        type=int,
        default=17,
        help="Variants with higher rank score get extra attention",
    )
    parser.add_argument(
        "--max_checked_annots",
        type=int,
        default=10000,
        help="Limit the number of annotations to check (for performance)",
    )
    parser.add_argument(
        "--max_display",
        type=int,
        default=10,
        help="Limit the number of entries printed to STDOUT (all entries are written to results folder)",
    )

    parser.add_argument(
        "--annotations", help="Comma separated additional annotations to retain in output"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
