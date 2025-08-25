#!/usr/bin/env python3

import argparse
import difflib
import logging
import os
from collections import Counter
from configparser import ConfigParser, SectionProxy
from io import TextIOWrapper
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from commands.eval.classes.helpers import VCFPair
from commands.eval.classes.pathobj import PathObj
from commands.eval.classes.run_object import (
    RunObject,
    get_files_in_dir,
    get_run_object,
)
from commands.eval.classes.run_settings import RunSettings

# from commands.eval.classes.score_paths import ScorePaths
from commands.eval.eval_functions import vcf_comparisons
from shared.compare import Comparison, do_comparison
from shared.constants import RUN_ID_PLACEHOLDER
from shared.file import check_valid_file, get_filehandle
from shared.vcf.annotation import compare_variant_annotation
from shared.vcf.main_functions import (
    compare_variant_presence,
    compare_variant_score,
    write_full_score_table,
)
from shared.vcf.vcf import ScoredVCF, count_variants, parse_scored_vcf

from .utils import (
    do_file_diff,
    do_simple_diff,
    get_ignored,
    get_pair_match,
    get_vcf_pair,
    verify_pair_exists,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VCF_SUFFIX = [".vcf", ".vcf.gz"]
VALID_COMPARISONS = set(
    [
        "default",
        "file",
        "presence_snv",
        "presence_sv",
        "score_snv",
        "score_sv",
        "yaml",
        "qc",
        "annotation_snv",
        "annotation_sv",
    ]
)

description = """
Compare results between runs for two versions of a pipeline.

Performs all or a subset of the comparisons:

- What files are present
- Do the VCF files have the same number of variants
- For the scored SNV and SV VCFs, what are call differences and differences in rank scores
- Are there differences in the Scout yaml
- Are there differences in the QC report
"""


FILE_NAMES = {"versions": "versions.diff", "scout_yaml": "scout_yaml.diff", "qc": "qc.diff"}


def log_and_write(text: str, fh: Optional[TextIOWrapper]):
    logger.info(text)
    if fh is not None:
        print(text, file=fh)


def check_comparison(all_comparisons: Optional[Set[str]], target_comparison: str) -> bool:
    return all_comparisons is None or target_comparison in all_comparisons


def main(  # noqa: C901 (skipping complexity check)
    ro: RunObject,
    rs: RunSettings,
    args_config_path: Optional[str],
    comparisons: Optional[Set[str]],
    outdir: Optional[Path],
):

    r1_paths = get_files_in_dir(ro.r1_results, ro.r1_id, RUN_ID_PLACEHOLDER, ro.r1_results)
    r2_paths = get_files_in_dir(ro.r2_results, ro.r2_id, RUN_ID_PLACEHOLDER, ro.r2_results)

    parent_path = Path(__file__).resolve().parent
    config_path = args_config_path or parent_path / "default.config"
    config = ConfigParser()
    config.read(config_path)

    if not config.has_section(rs.pipeline):
        available_sections = config.sections()
        raise ValueError(
            f"Pipeline {rs.pipeline} is not defined in config. Available in config file are: {', '.join(available_sections)}"
        )

    pipe_conf = config[rs.pipeline]

    if comparisons is not None and len(comparisons & VALID_COMPARISONS) == 0:
        raise ValueError(f"Valid comparisons are: {VALID_COMPARISONS}, found: {comparisons}")

    verify_pair_exists("result dirs", ro.r1_results, ro.r2_results)

    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)

    if comparisons is None or "file" in comparisons:
        do_file_diff(logger, outdir, pipe_conf, ro, r1_paths, r2_paths)

    run_ids = (ro.r1_id, ro.r2_id)

    # SNV comparisons
    snv_vcf_path_patterns = (pipe_conf["snv_vcf"] or "").split(",")
    any_snv_comparison = (
        comparisons is None
        or len(comparisons.intersection({f"basic_snv", f"score_snv", f"annotation_snv"})) > 0
    )
    if any_snv_comparison:
        if snv_vcf_path_patterns:
            snv_vcfs = get_vcf_pair(logger, snv_vcf_path_patterns, ro, r1_paths, r2_paths, rs.verbose, "snv")
            if snv_vcfs:
                vcf_comparisons(logger, comparisons, run_ids, outdir, rs, "snv", snv_vcfs)
        else:
            logger.warning("No SNV patterns matched, skipping")

    # SV comparisons
    sv_vcf_path_patterns = (pipe_conf["sv_vcf"] or "").split(",")
    any_sv_comparison = (
        comparisons is None
        or len(comparisons.intersection({f"basic_sv", f"score_sv", f"annotation_sv"})) > 0
    )
    if any_sv_comparison:
        if sv_vcf_path_patterns:
            sv_vcfs = get_vcf_pair(logger, sv_vcf_path_patterns, ro, r1_paths, r2_paths, rs.verbose, "sv")
            if sv_vcfs:
                vcf_comparisons(logger, comparisons, run_ids, outdir, rs, "sv", sv_vcfs)
        else:
            logger.warning("No SV patterns matched, skipping")
        

    scout_yaml_check = "scout_yaml"
    if comparisons is None or scout_yaml_check in comparisons and pipe_conf.get(scout_yaml_check):
        do_simple_diff(logger, ro, r1_paths, r2_paths, pipe_conf, scout_yaml_check, outdir, rs.verbose)

    qc_check = "qc"
    if comparisons is None or qc_check in comparisons and pipe_conf.get(qc_check):
        do_simple_diff(logger, ro, r1_paths, r2_paths, pipe_conf, qc_check, outdir, rs.verbose)

    version_check = "versions"
    if comparisons is None or version_check in comparisons and pipe_conf.get(version_check):
        do_simple_diff(logger, ro, r1_paths, r2_paths, pipe_conf, version_check, outdir, rs.verbose)


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--pipeline",
        help="The target pipeline. Currently only 'rd-const' is available",
        required=True,
    )
    parser.add_argument(
        "--run_id1",
        "-i1",
        help="The group ID is used in some file names and can differ between runs. If not provided, it is set to the base folder name.",
    )
    parser.add_argument("--run_id2", "-i2", help="See --run_id1 help")
    parser.add_argument("--results1", "-r1", "-1", required=True, type=Path)
    parser.add_argument("--results2", "-r2", "-2", required=True, type=Path)
    parser.add_argument("--config", help="Additional configurations")
    parser.add_argument(
        "--comparisons",
        help=f"Comma separated. Defaults to: default, run all by: {','.join(VALID_COMPARISONS)}",
        default="default",
    )
    parser.add_argument(
        "--score_threshold",
        type=int,
        help="Limit score comparisons to above this threshold",
        default=17,
    )
    parser.add_argument(
        "--max_display",
        type=int,
        default=15,
        help="Max number of top variants to print to STDOUT",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print additional information",
    )
    parser.add_argument("--outdir", help="Optional output folder to store result files")
    parser.add_argument(
        "--max_checked_annots",
        help="Max number of annotations to check",
        default=10000,
        type=int,
    )
    parser.add_argument(
        "-n",
        "--show_line_numbers",
        action="store_true",
        help="Show line numbers from original VCFs in output",
    )
    parser.add_argument("--annotations", help="INFO keys to include in output tables")
    parser.add_argument(
        "--silent", action="store_true", help="Run silently, produce only output files"
    )
    parser.add_argument(
        "--all_variants",
        action="store_true",
        help="Write score comparison including non-differing variants",
    )


def main_wrapper(args: argparse.Namespace):

    if args.silent:
        logger.setLevel(logging.WARNING)

    run_object = get_run_object(
        logger, args.run_id1, args.run_id2, args.results1, args.results2, args.verbose
    )

    extra_annot_keys: List[str] = []
    if args.annotations:
        extra_annot_keys = args.annotations.split(",")

    run_settings = RunSettings(
        args.pipeline,
        args.score_threshold,
        args.max_display,
        args.verbose,
        args.max_checked_annots,
        args.show_line_numbers,
        extra_annot_keys,
        args.all_variants,
    )

    main(
        run_object,
        run_settings,
        args.config,
        None if args.comparisons == "default" else set(args.comparisons.split(",")),
        Path(args.outdir) if args.outdir is not None else None,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
