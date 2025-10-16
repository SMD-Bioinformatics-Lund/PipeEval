import argparse
import logging
from pathlib import Path
from typing import List, Optional

from commands.eval.classes.run_settings import RunSettings
from commands.eval.classes.score_paths import ScorePaths
from shared.vcf.main_functions import variant_comparisons

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main(
    vcf1: Path,
    vcf2: Path,
    is_sv: bool,
    use_score_threshold: bool = False,
    max_display: int = 10,
    max_checked_annots: Optional[int] = None,
    score_threshold: Optional[int] = None,
    run_id1: Optional[str] = None,
    run_id2: Optional[str] = None,
    results: Optional[Path] = None,
    extra_annot_keys: Optional[List[str]] = None,
    output_all_variants: bool = False,
    ):
    
    run_settings = RunSettings(
        use_score_threshold=use_score_threshold,
        score_threshold=score_threshold,
        max_display=max_display,
        max_checked_annots=max_checked_annots,
        show_line_numbers=True,
        extra_annot_keys=extra_annot_keys,
    )

    if results is not None:
        if not results.exists():
            results.mkdir(parents=True)

    if run_id1 is None:
        run_id1 = str(vcf1).split("/")[-1].split(".")[0]
        logger.info(f"# --run_id1 not set, assigned: {run_id1}")

    if run_id2 is None:
        run_id2 = str(vcf2).split("/")[-1].split(".")[0]
        if run_id1 == run_id2:
            run_id2 = run_id2 + "_2"
        logger.info(f"# --run_id2 not set, assigned: {run_id2}")

    label = "sv" if is_sv else "snv"
    score_paths = ScorePaths(label, results, score_threshold, output_all_variants)

    do_score_check = True
    do_annot_check = True
    variant_comparisons(
        logger,
        run_id1,
        run_id2,
        vcf1,
        vcf2,
        is_sv,
        run_settings,
        score_paths,
        do_score_check,
        do_annot_check,
    )


def main_wrapper(args: argparse.Namespace):

    if args.silent:
        logger.setLevel(logging.WARNING)

    main(
        args.vcf1,
        args.vcf2,
        args.is_sv,
        args.use_score_threshold,
        args.max_display,
        args.max_checked_annots,
        args.score_threshold,
        args.id1,
        args.id2,
        args.results if args.results is not None else None,
        args.annotations.split(",") if args.annotations is not None else [],
        args.all_variants,
    )


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--vcf1",
        "-1",
        required=True,
        type=Path,
        help="VCF to compare in .vcf or .vcf.gz format",
    )
    parser.add_argument(
        "--vcf2",
        "-2",
        required=True,
        type=Path,
        help="VCF to compare in .vcf or .vcf.gz format",
    )
    parser.add_argument("--id1", help="Optional run ID for first vcf")
    parser.add_argument("--id2", help="Optional run ID for second vcf")
    parser.add_argument("--is_sv", action="store_true", help="Process VCF in SV mode")
    parser.add_argument("--results", type=Path, help="Optional results folder")
    parser.add_argument("--use_score_threshold", action="store_false", help="Score threshold for the scored variants"
    )
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
        "--annotations",
        help="Comma separated additional annotations to retain in output",
    )
    parser.add_argument(
        "--silent", action="store_true", help="Run silently, produce only output files"
    )
    parser.add_argument(
        "--all_variants",
        action="store_true",
        help="Write a comparison file including non-differing variants",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
