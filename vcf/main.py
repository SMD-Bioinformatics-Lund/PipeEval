import argparse
from pathlib import Path
import logging

from shared.compare import do_comparison
from shared.vcf.main_functions import compare_variant_presence
from shared.vcf.vcf import parse_vcf


# logger = setup_stdout_logger()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main(vcf1: Path, vcf2: Path, is_sv: bool, out_base: Path):
    variants_r1 = parse_vcf(vcf1, is_sv)
    variants_r2 = parse_vcf(vcf1, is_sv)
    comparison_results = do_comparison(
        set(variants_r1.keys()),
        set(variants_r2.keys()),
    )

    max_display = 10
    show_line_numbers = True
    out_path_presence = out_base / "presence"

    compare_variant_presence(
        logger, 
        "label 1", 
        "label 2", 
        variants_r1, 
        variants_r2, 
        comparison_results, 
        max_display, 
        out_path_presence, 
        show_line_numbers
    )


def main_wrapper(args: argparse.Namespace):
    main(args.vcf1, args.vcf2)


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--vcf1", required=True)
    parser.add_argument("--vcf2", required=True)
    parser.add_argument("--is_sv", action="store_true")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
