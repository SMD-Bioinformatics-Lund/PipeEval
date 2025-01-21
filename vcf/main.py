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


def main(vcf1: Path, vcf2: Path, is_sv: bool, max_display: int, max_checked_annots: int, score_threshold: int, run_id1: Optional[str], run_id2: Optional[str], results: Optional[Path]):
    vcf_r1 = parse_scored_vcf(vcf1, is_sv)
    vcf_r2 = parse_scored_vcf(vcf2, is_sv)
    comparison_results = do_comparison(
        set(vcf_r1.variants.keys()),
        set(vcf_r2.variants.keys()),
    )

    show_line_numbers = True
    out_path_presence = results / "presence.txt" if results else None

    if run_id1 is None:
        run_id1 = str(vcf1)
        logger.info(f"--run_id1 not set, assigned: {run_id1}")

    if run_id2 is None:
        run_id2 = str(vcf2)
        logger.info(f"--run_id2 not set, assigned: {run_id2}")

    logger.info("")
    logger.info("### Comparing variant presence ###")
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

    logger.info("")
    logger.info("### Comparing annotations ###")
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
        logger.info("### Comparing score ###")
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
        args.score_threshold,
        args.max_checked_annots,
        args.max_display,
        args.id1,
        args.id2,
        Path(args.results) if args.results is not None else None,
    )


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--vcf1", "-1", required=True)
    parser.add_argument("--vcf2", "-2", required=True)
    parser.add_argument("--id1", help="Optional run ID for vcf 1")
    parser.add_argument("--id2", help="Optional run ID for vcf 2")
    parser.add_argument("--is_sv", action="store_true")
    parser.add_argument("--results", help="Optional results folder")
    parser.add_argument("--score_threshold", type=int, default=17)
    parser.add_argument("--max_checked_annots", type=int, default=1000)
    parser.add_argument("--max_display", type=int, default=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
