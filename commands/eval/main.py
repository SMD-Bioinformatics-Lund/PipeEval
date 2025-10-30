#!/usr/bin/env python3

import argparse
import logging
import sys
from configparser import ConfigParser, SectionProxy
from pathlib import Path
from typing import List, Optional, Set, Tuple

from commands.eval.classes.helpers import PathObj, RunSettings
from commands.eval.classes.run_object import (
    RunObject,
    get_files_in_dir,
    get_run_object,
)
from commands.eval.main_functions import (
    VCFComparison,
    do_file_diff,
    do_simple_diff,
    do_vcf_comparisons,
)
from shared.constants import RUN_ID_PLACEHOLDER, VCFType

from .utils import (
    get_vcf_pair,
    verify_pair_exists,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VCF_SUFFIX = [".vcf", ".vcf.gz"]
VCF_COMPARISONS = [member.value for member in VCFComparison]
SNV_COMPARISONS = [f"{comp}_snv" for comp in VCF_COMPARISONS]
SV_COMPARISONS = [f"{comp}_sv" for comp in VCF_COMPARISONS]

VALID_COMPARISONS = set()
for comp in SNV_COMPARISONS:
    VALID_COMPARISONS.add(comp)
for comp in SV_COMPARISONS:
    VALID_COMPARISONS.add(comp)
for comp in {"default", "file", "scout_yaml", "qc", "versions"}:
    VALID_COMPARISONS.add(comp)

description = """
Compare results between runs for two versions of a pipeline.

Performs all or a subset of the comparisons:

- What files are present
- Do the VCF files have the same number of variants
- For the scored SNV and SV VCFs, what are call differences and differences in rank scores
- Are there differences in the Scout yaml
- Are there differences in the QC report
"""


def main(
    ro: RunObject,
    rs: RunSettings,
    args_config_path: Optional[str],
    args_comparisons: Optional[Set[str]],
    outdir: Optional[Path],
):

    r1_paths = get_files_in_dir(
        ro.r1_results, ro.r1_id, RUN_ID_PLACEHOLDER, ro.r1_results
    )
    r2_paths = get_files_in_dir(
        ro.r2_results, ro.r2_id, RUN_ID_PLACEHOLDER, ro.r2_results
    )

    parent_path = Path(__file__).resolve().parent
    config_path = args_config_path or parent_path / "default.ini"
    config = ConfigParser()
    config.read(config_path)

    if not config.has_section(rs.pipeline):
        available_sections = config.sections()
        raise ValueError(
            f"Pipeline \"{rs.pipeline}\" is not defined in config. Available in config file are: {', '.join(available_sections)}. Specify pipeline using the --pipeline flag."
        )

    pipe_conf = config[rs.pipeline]

    used_comparisons = get_comparisons(logger, args_comparisons, pipe_conf, rs)

    run_ids = (ro.r1_id, ro.r2_id)

    verify_pair_exists("result dirs", run_ids, ro.r1_results, ro.r2_results, None)

    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)

    if not used_comparisons or "file" in used_comparisons:
        do_file_diff(logger, outdir, pipe_conf, ro, r1_paths, r2_paths)

    snv_patterns = (
        set(pipe_conf["snv_vcf"].split(",")) if pipe_conf.get("snv_vcf") else set()
    )
    main_vcf_comparisons(
        run_ids,
        used_comparisons,
        ro,
        r1_paths,
        r2_paths,
        rs,
        snv_patterns,
        outdir,
        VCFType.snv,
        rs.custom_info_keys_snv,
        SNV_COMPARISONS,
    )

    sv_patterns = (
        set(pipe_conf["sv_vcf"].split(",")) if pipe_conf.get("sv_vcf") else set()
    )
    main_vcf_comparisons(
        run_ids,
        used_comparisons,
        ro,
        r1_paths,
        r2_paths,
        rs,
        sv_patterns,
        outdir,
        VCFType.sv,
        rs.custom_info_keys_sv,
        SV_COMPARISONS,
    )

    scout_yaml_check = "scout_yaml"
    if not used_comparisons or scout_yaml_check in used_comparisons:
        do_simple_diff(
            logger,
            ro,
            r1_paths,
            r2_paths,
            pipe_conf,
            scout_yaml_check,
            outdir,
            rs.verbose,
        )

    qc_check = "qc"
    if not used_comparisons or qc_check in used_comparisons:
        do_simple_diff(
            logger, ro, r1_paths, r2_paths, pipe_conf, qc_check, outdir, rs.verbose
        )

    version_check = "versions"
    if not used_comparisons or version_check in used_comparisons:
        do_simple_diff(
            logger, ro, r1_paths, r2_paths, pipe_conf, version_check, outdir, rs.verbose
        )


def get_comparisons(
    logger: logging.Logger,
    arg_comparisons: Optional[Set[str]],
    pipe_conf: SectionProxy,
    rs: RunSettings,
) -> Set[str]:
    used_comparison: Set[str] = set()
    if arg_comparisons:
        used_comparison = set(arg_comparisons)
    else:
        default_comp_str = pipe_conf.get("default_comparisons")
        if default_comp_str:
            used_comparison = set(
                filter(None, [c.strip() for c in default_comp_str.split(",")])
            )

    if len(rs.custom_info_keys_snv) > 0:
        used_comparison.add("custom_info_snv")
    if len(rs.custom_info_keys_sv) > 0:
        used_comparison.add("custom_info_sv")

    if used_comparison and len(used_comparison & VALID_COMPARISONS) == 0:
        logger.error(
            f"Valid comparisons are: {VALID_COMPARISONS}, found: {used_comparison}"
        )
        sys.exit(1)

    return used_comparison


def main_vcf_comparisons(
    run_ids: Tuple[str, str],
    comparisons: Set[str],
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    rs: RunSettings,
    vcf_path_patterns: Set[str],
    outdir: Optional[Path],
    vcf_type: VCFType,
    custom_info_keys: Set[str],
    all_comparisons: List[str],
):
    vcf_comparisons = set()
    if comparisons:
        vcf_comparisons = {
            VCFComparison(comp.replace(f"_{vcf_type.value}", ""))
            for comp in comparisons
            if comp in all_comparisons
        }

    if not comparisons or len(vcf_comparisons) > 0:
        if vcf_path_patterns:

            vcfs = get_vcf_pair(
                logger,
                list(vcf_path_patterns),
                ro,
                r1_paths,
                r2_paths,
                rs.verbose,
                vcf_type,
            )
            if vcfs:
                do_vcf_comparisons(
                    logger,
                    vcf_comparisons,
                    run_ids,
                    outdir,
                    rs,
                    vcf_type.value,
                    vcfs,
                    custom_info_keys,
                )
        else:
            logger.warning(f"No {vcf_type.value.upper()} patterns matched, skipping")


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--pipeline",
        help=(
            "The target pipeline (e.g. dna-const, rna-const). If not provided,"
            " eval attempts to read it from 'pipeline_info' in the results folders."
        ),
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
        help=(
            f"Comma separated. If omitted (or set to 'default'), use default_comparisons from the pipeline config. "
            f"Available: {','.join(sorted(VALID_COMPARISONS))}"
        ),
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
    parser.add_argument(
        "--custom_info_keys_snv", help="INFO keys to investigate closer in SNV vcf"
    )
    parser.add_argument(
        "--custom_info_keys_sv", help="INFO keys to investigate closer in SV vcf"
    )


def get_pipeline_from_run_folders(
    logger: logging.Logger, results1: Path, results2: Path
):
    """Checks for file pipeline_info in the results dir if pipeline"""
    pipeline1 = None
    pipeline2 = None
    try:
        info1 = (results1 / "pipeline_info").read_text().strip()
        pipeline1 = info1 if info1 else None
    except Exception:
        pipeline1 = None
    try:
        info2 = (results2 / "pipeline_info").read_text().strip()
        pipeline2 = info2 if info2 else None
    except Exception:
        pipeline2 = None

    if pipeline1 and pipeline2 and pipeline1 != pipeline2:
        logger.error(
            f"Found differing pipelines in the run dirs ({pipeline1} and {pipeline2}). Specify pipeline using the --pipeline flag"
        )

    return pipeline1 or pipeline2


def main_wrapper(args: argparse.Namespace):

    if args.silent:
        logger.setLevel(logging.WARNING)

    run_object = get_run_object(
        logger, args.run_id1, args.run_id2, args.results1, args.results2, args.verbose
    )

    extra_annot_keys: List[str] = []
    if args.annotations:
        extra_annot_keys = args.annotations.split(",")

    custom_info_keys_snv = (
        set()
        if not args.custom_info_keys_snv
        else set(args.custom_info_keys_snv.split(","))
    )
    custom_info_keys_sv = (
        set()
        if not args.custom_info_keys_sv
        else set(args.custom_info_keys_sv.split(","))
    )

    # The placeholder allows of a later graceful exit after the base config has been loaded
    pipeline_name = (
        args.pipeline
        or get_pipeline_from_run_folders(
            logger, run_object.r1_results, run_object.r2_results
        )
        or "No pipeline found"
    )

    run_settings = RunSettings(
        pipeline_name,
        args.score_threshold,
        args.max_display,
        args.verbose,
        args.max_checked_annots,
        args.show_line_numbers,
        extra_annot_keys,
        args.all_variants,
        custom_info_keys_snv,
        custom_info_keys_sv,
    )

    # Build comparisons from CLI; None means use default_comparisons in config
    if args.comparisons is None or args.comparisons == "default":
        comparisons = None
    else:
        comparisons = set(args.comparisons.split(","))

    main(
        run_object,
        run_settings,
        args.config,
        comparisons,
        Path(args.outdir) if args.outdir is not None else None,
    )
