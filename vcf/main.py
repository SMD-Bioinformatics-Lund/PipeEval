import argparse
from pathlib import Path
import logging
from typing import Optional

from shared.compare import do_comparison
from shared.vcf.annotation import compare_variant_annotation
from shared.vcf.main_functions import compare_variant_presence, compare_variant_score
from shared.vcf.vcf import parse_scored_vcf


# logger = setup_stdout_logger()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main(vcf1: Path, vcf2: Path, is_sv: bool, results: Optional[Path]):
    vcf_r1 = parse_scored_vcf(vcf1, is_sv)
    vcf_r2 = parse_scored_vcf(vcf2, is_sv)
    comparison_results = do_comparison(
        set(vcf_r1.variants.keys()),
        set(vcf_r2.variants.keys()),
    )

    max_display = 10
    show_line_numbers = True
    out_path_presence = results / "presence.txt" if results else None

    run_id1 = "label 1"
    run_id2 = "label 2"

    compare_variant_presence(
        logger,
        run_id1,
        run_id2,
        vcf_r1.variants,
        vcf_r2.variants,
        comparison_results,
        max_display,
        out_path_presence,
        show_line_numbers,
    )

    shared_variants = comparison_results.shared

    # FIXME: How to handle these settings? An object?
    max_checked_annots = 10

    logger.info("")
    logger.info("--- Comparing annotations ---")
    compare_variant_annotation(
        logger,
        run_id1,
        run_id2,
        shared_variants,
        vcf_r1.variants,
        vcf_r2.variants,
        max_checked_annots,
    )

    # FIXME: Check automatically for score check? Allow override with flags
    do_score_check = True
    score_threshold = 17
    out_path_score_above_thres = results / "above_thres.txt" if results else None
    out_path_score_all = results / "score_all.txt" if results else None

    if do_score_check:
        logger.info("")
        logger.info("--- Comparing score ---")
        compare_variant_score(
            logger,
            run_id1,
            run_id2,
            shared_variants,
            vcf_r1.variants,
            vcf_r2.variants,
            score_threshold,
            max_display,
            out_path_score_above_thres,
            out_path_score_all,
            is_sv,
            show_line_numbers,
        )


def main_wrapper(args: argparse.Namespace):
    main(
        Path(args.vcf1),
        Path(args.vcf2),
        args.is_sv,
        Path(args.results) if args.results is not None else None,
    )


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--vcf1", required=True)
    parser.add_argument("--vcf2", required=True)
    parser.add_argument("--is_sv", action="store_true")
    parser.add_argument("--results", help="Optional results folder")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
