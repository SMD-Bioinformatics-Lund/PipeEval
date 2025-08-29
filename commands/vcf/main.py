import argparse
import logging
from pathlib import Path
import sys
from typing import List, Optional, Set

from commands.eval.classes.helpers import RunSettings
from commands.eval.main import do_vcf_comparisons
from commands.eval.main_functions import VCFComparison
from commands.eval.utils import parse_vcf_pair
from shared.constants import VCFType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ALL_VCF_COMPARISONS = {member.value for member in VCFComparison}


def main(
    vcf1: Path,
    vcf2: Path,
    max_display: int,
    max_checked_annots: int,
    score_threshold: int,
    run_id1: Optional[str],
    run_id2: Optional[str],
    results_folder: Optional[Path],
    extra_annot_keys: List[str],
    output_all_variants: bool,
    comparisons: Set[str],
    custom_info_keys: Set[str],
    vcf_type: VCFType,
):
    if results_folder is not None:
        if not results_folder.exists():
            results_folder.mkdir(parents=True)

    if run_id1 is None:
        run_id1 = str(vcf1).split("/")[-1].split(".")[0]
        logger.info(f"# --run_id1 not set, assigned: {run_id1}")

    if run_id2 is None:
        run_id2 = str(vcf2).split("/")[-1].split(".")[0]
        if run_id1 == run_id2:
            run_id2 = run_id2 + "_2"
        logger.info(f"# --run_id2 not set, assigned: {run_id2}")

    run_ids = (run_id1, run_id2)

    verbose = False
    show_line_numbers = True

    rs = RunSettings(
        "",
        score_threshold,
        max_display,
        verbose,
        max_checked_annots,
        show_line_numbers,
        extra_annot_keys,
        output_all_variants,
    )

    if not comparisons:
        comparisons = ALL_VCF_COMPARISONS
    vcf_comparisons: Set[VCFComparison] = set()
    for comp in comparisons:
        if comp not in VCFComparison:
            all_valid = [member.value for member in VCFComparison]
            logger.warning(
                f"{comp} is not a valid comparison. Skipping. Valid are: {", ".join(all_valid)}"
            )
        else:
            vcf_comparisons.add(VCFComparison(comp))

    vcfs = parse_vcf_pair(logger, run_ids, (vcf1, vcf2), vcf_type)
    do_vcf_comparisons(
        logger, vcf_comparisons, run_ids, results_folder, rs, vcf_type, vcfs, custom_info_keys
    )


def main_wrapper(args: argparse.Namespace):

    if args.silent:
        logger.setLevel(logging.WARNING)

    comparisons = ALL_VCF_COMPARISONS if not args.comparisons else set(args.comparisons.split(","))
    custom_info_keys = set() if not args.custom_info_keys else set(args.custom_info_keys.split(","))

    if len(custom_info_keys) == 0 and "custom_info" in comparisons and args.comparisons:
        logger.warning(
            "custom_info comparison specified but no --custom_info_keys arguments. Skipping."
        )
        comparisons.remove("custom_info")
        if len(comparisons) == 0:
            logger.error("No remaining comparisons after removing custom_info. Stopping.")
            sys.exit(1)

    main(
        args.vcf1,
        args.vcf2,
        args.max_display,
        args.max_checked_annots,
        args.score_threshold,
        args.id1,
        args.id2,
        args.results if args.results is not None else None,
        args.annotations.split(",") if args.annotations is not None else [],
        args.all_variants,
        comparisons,
        custom_info_keys,
        args.vcf_type,
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
    parser.add_argument(
        "--comparisons",
        help=f"Comparisons to do. Available are: {",".join(ALL_VCF_COMPARISONS)}. Default is to run all.",
    )
    parser.add_argument(
        "--custom_info_keys",
        help='INFO keys to inspect separately. Used together with "info" setting.',
    )
    parser.add_argument(
        "--vcf_type", type=VCFType, help="Specify if running an SNV or SV", required=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
