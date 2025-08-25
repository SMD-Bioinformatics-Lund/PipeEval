#!/usr/bin/env python3

import argparse
import difflib
import logging
import os
from collections import Counter
from configparser import SectionProxy
from io import TextIOWrapper
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from commands.eval.classes.pathobj import PathObj
from commands.eval.classes.run_object import (
    RunObject,
    get_files_in_dir,
    get_run_object,
)
from commands.eval.classes.run_settings import RunSettings

# from commands.eval.classes.score_paths import ScorePaths
from shared.compare import Comparison, do_comparison
from shared.constants import RUN_ID_PLACEHOLDER
from shared.file import check_valid_file, get_filehandle
from shared.util import load_config
from shared.vcf.annotation import compare_variant_annotation
from shared.vcf.main_functions import (
    compare_variant_presence,
    compare_variant_score,
    write_full_score_table,
)
from shared.vcf.vcf import ScoredVCF, count_variants, parse_scored_vcf

from .utils import (
    get_ignored,
    get_pair_match,
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
Compare results for runs in two pipelines.

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


class VCFPair:
    vcf1: ScoredVCF
    vcf2: ScoredVCF
    comp: Comparison[str]

    def __init__(self, vcf1: ScoredVCF, vcf2: ScoredVCF, comp: Comparison[str]):
        self.vcf1 = vcf1
        self.vcf2 = vcf2
        self.comp = comp


def main(  # noqa: C901 (skipping complexity check)
    ro: RunObject,
    rs: RunSettings,
    config_path: Optional[str],
    comparisons: Optional[Set[str]],
    outdir: Optional[Path],
):

    r1_paths = get_files_in_dir(ro.r1_results, ro.r1_id, RUN_ID_PLACEHOLDER, ro.r1_results)
    r2_paths = get_files_in_dir(ro.r2_results, ro.r2_id, RUN_ID_PLACEHOLDER, ro.r2_results)

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    config = load_config(logger, curr_dir, config_path)

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
        do_file_diff(outdir, pipe_conf, ro, r1_paths, r2_paths)

    run_ids = (ro.r1_id, ro.r2_id)

    # SNV comparisons
    snv_vcf_path_patterns = (pipe_conf["snv_vcf"] or "").split(",")
    any_snv_comparison = (
        comparisons is None
        or len(comparisons.intersection({f"basic_snv", f"score_snv", f"annotation_snv"})) > 0
    )
    if any_snv_comparison:
        if snv_vcf_path_patterns:
            snv_vcfs = get_vcf_pair(snv_vcf_path_patterns, ro, r1_paths, r2_paths, rs.verbose, "snv")
            if snv_vcfs:
                vcf_comparisons(comparisons, run_ids, outdir, rs, "snv", snv_vcfs)
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
            sv_vcfs = get_vcf_pair(sv_vcf_path_patterns, ro, r1_paths, r2_paths, rs.verbose, "sv")
            if sv_vcfs:
                vcf_comparisons(comparisons, run_ids, outdir, rs, "sv", sv_vcfs)
        else:
            logger.warning("No SV patterns matched, skipping")
        

    scout_yaml_check = "scout_yaml"
    if comparisons is None or scout_yaml_check in comparisons and pipe_conf.get(scout_yaml_check):
        do_simple_diff(ro, r1_paths, r2_paths, pipe_conf, scout_yaml_check, outdir, rs.verbose)

    qc_check = "qc"
    if comparisons is None or qc_check in comparisons and pipe_conf.get(qc_check):
        do_simple_diff(ro, r1_paths, r2_paths, pipe_conf, qc_check, outdir, rs.verbose)

    version_check = "versions"
    if comparisons is None or version_check in comparisons and pipe_conf.get(version_check):
        do_simple_diff(ro, r1_paths, r2_paths, pipe_conf, version_check, outdir, rs.verbose)


def do_file_diff(
    outdir: Optional[Path],
    pipe_conf: SectionProxy,
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
):
    out_path = outdir / "check_sample_files.txt" if outdir else None
    logger.info("")
    logger.info("### Comparing existing files ###")

    ignore_file_string = pipe_conf.get("ignore") or ""
    ignore_files = ignore_file_string.split(",")

    check_same_files(
        ro,
        r1_paths,
        r2_paths,
        ignore_files,
        out_path,
    )


def get_vcf_pair(
    vcf_paths: List[str],
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    verbose: bool,
    vcf_type: str
) -> Optional[VCFPair]:
    vcf_pair_paths = get_pair_match(
        logger,
        vcf_type,
        vcf_paths,
        ro,
        r1_paths,
        r2_paths,
        verbose,
    )

    if vcf_pair_paths is None:
        logger.warning(f"Skipping {vcf_type} comparisons due to missing files ({vcf_pair_paths})")
        return None

    vcf_pair = parse_vcf_pair(ro.run_ids, vcf_pair_paths, vcf_type)

    return vcf_pair


def parse_vcf_pair(run_ids: Tuple[str, str], vcf_paths: Tuple[Path, Path], vcf_type: str) -> VCFPair:
    logger.info(f"# Parsing {vcf_type} VCFs ...")

    vcf_r1 = parse_scored_vcf(vcf_paths[0], False)
    logger.info(f"{run_ids[0]} number variants: {len(vcf_r1.variants)}")
    vcf_r2 = parse_scored_vcf(vcf_paths[1], False)
    logger.info(f"{run_ids[1]} number variants: {len(vcf_r2.variants)}")

    comp_res = do_comparison(
        set(vcf_r1.variants.keys()),
        set(vcf_r2.variants.keys()),
    )
    logger.info(f"In common: {len(comp_res.shared)}")
    logger.info(f"Only in {run_ids[0]}: {len(comp_res.r1)}")
    logger.info(f"Only in {run_ids[1]}: {len(comp_res.r2)}")

    vcf_pair = VCFPair(vcf_r1, vcf_r2, comp_res)
    return vcf_pair


def do_simple_diff(
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    pipe_conf: SectionProxy,
    analysis: str,
    outdir: Optional[Path],
    verbose: bool,
):
    logger.info("")
    logger.info(f"--- Comparing: {analysis} ---")
    matched_pair = get_pair_match(
        logger,
        analysis,
        pipe_conf[analysis].split(","),
        ro,
        r1_paths,
        r2_paths,
        verbose,
    )
    if not matched_pair:
        logging.warning(f"At least one file missing ({matched_pair})")
    else:
        out_path = outdir / FILE_NAMES[analysis] if outdir else None
        diff_compare_files(ro.r1_id, ro.r2_id, matched_pair[0], matched_pair[1], out_path)


def vcf_comparisons(
    comparisons: Optional[Set[str]],
    run_ids: Tuple[str, str],
    outdir: Optional[Path],
    rs: RunSettings,
    vcf_type: str,
    vcfs: VCFPair,
):
    if check_comparison(comparisons, f"presence_{vcf_type}") and vcfs is not None:
        logger.info("")
        logger.info("### Variants only present in one ###")
        presence_path = outdir / f"scored_{vcf_type}_presence.txt" if outdir else None
        compare_variant_presence(
            logger,
            run_ids,
            vcfs.vcf1.variants,
            vcfs.vcf2.variants,
            vcfs.comp,
            rs.max_display,
            presence_path,
            rs.show_line_numbers,
            rs.annotation_info_keys,
        )

    if check_comparison(comparisons, f"annotation_{vcf_type}") and vcfs:
        logger.info("")
        logger.info("### Comparing annotations ###")
        compare_variant_annotation(
            logger,
            run_ids,
            vcfs.comp.shared,
            vcfs.vcf1.variants,
            vcfs.vcf2.variants,
            rs.max_checked_annots,
        )

    if check_comparison(comparisons, f"score_{vcf_type}") and vcfs:
        logger.info("")
        logger.info("### Comparing score ###")
        score_thres_path = (
            outdir / f"scored_{vcf_type}_above_thres_{rs.score_threshold}.txt" if outdir else None
        )
        all_diffing_path = outdir / f"scored_{vcf_type}_all_diffing.txt" if outdir else None
        is_sv = False

        compare_variant_score(
            logger,
            run_ids,
            vcfs.comp.shared,
            vcfs.vcf1.variants,
            vcfs.vcf2.variants,
            rs.score_threshold,
            rs.max_display,
            score_thres_path,
            all_diffing_path,
            is_sv,
            rs.show_line_numbers,
            rs.annotation_info_keys,
        )
        if rs.output_all_variants is not None and outdir:
            all_path = outdir / f"scored_{vcf_type}_score_full.txt"
            write_full_score_table(
                run_ids,
                vcfs.comp.shared,
                vcfs.vcf1.variants,
                vcfs.vcf2.variants,
                all_path,
                is_sv,
                rs.show_line_numbers,
                rs.annotation_info_keys,
            )


def check_same_files(
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    ignore_files: List[str],
    out_path: Optional[Path],
):

    files_in_results1 = set(path.relative_path for path in r1_paths)
    files_in_results2 = set(path.relative_path for path in r2_paths)

    comparison = do_comparison(files_in_results1, files_in_results2)

    out_fh = open(out_path, "w") if out_path else None

    (r1_nbr_ignored_per_pattern, r1_non_ignored) = get_ignored(comparison.r1, ignore_files)
    (r2_nbr_ignored_per_pattern, r2_non_ignored) = get_ignored(comparison.r2, ignore_files)

    ignored = Counter(r1_nbr_ignored_per_pattern) + Counter(r2_nbr_ignored_per_pattern)

    if len(r1_non_ignored) > 0:
        log_and_write(f"Files present in {ro.r1_id} but missing in {ro.r2_id}:", out_fh)
        for path in sorted(r1_non_ignored):
            log_and_write(f"  {path}", out_fh)

    if len(r2_non_ignored) > 0:
        log_and_write(f"Files present in {ro.r2_id} but missing in {ro.r1_id}:", out_fh)
        for path in sorted(r2_non_ignored):
            log_and_write(f"  {path}", out_fh)

    if len(r1_non_ignored) == 0 and len(r2_non_ignored) == 0:
        log_and_write("All non-ignored files present in both results", out_fh)

    if len(ignored) > 0:
        log_and_write("Ignored", out_fh)
        for key, val in ignored.items():
            log_and_write(f"  {key}: {val}", out_fh)

    if out_fh:
        out_fh.close()


def compare_all_vcfs(
    ro: RunObject,
    r1_vcfs: List[Path],
    r2_vcfs: List[Path],
    out_path: Optional[Path],
):
    r1_counts: Dict[str, int] = {}
    for vcf in r1_vcfs:
        if check_valid_file(vcf):
            n_variants = count_variants(vcf)
        else:
            n_variants = 0
        r1_counts[str(vcf).replace(str(ro.r1_results), "")] = n_variants

    r2_counts: Dict[str, int] = {}
    for vcf in r2_vcfs:
        if check_valid_file(vcf):
            n_variants = count_variants(vcf)
        else:
            n_variants = 0
        r2_counts[str(vcf).replace(str(ro.r2_results), "")] = n_variants

    paths = r1_counts.keys() | r2_counts.keys()

    max_path_length = max(len(path) for path in paths)

    out_fh = open(out_path, "w") if out_path else None
    log_and_write(f"{'Path':<{max_path_length}} {ro.r1_id:>10} {ro.r2_id:>10}", out_fh)
    for path in sorted(paths):
        r1_val = r1_counts.get(path) or "-"
        r2_val = r2_counts.get(path) or "-"
        log_and_write(
            f"{path:<{max_path_length}} {r1_val:>{len(ro.r1_id)}} {r2_val:>{len(ro.r2_id)}}",
            out_fh,
        )

    if out_fh:
        out_fh.close()


def diff_compare_files(
    run_id1: str,
    run_id2: str,
    file1: Path,
    file2: Path,
    out_path: Optional[Path],
):

    with get_filehandle(file1) as r1_fh, get_filehandle(file2) as r2_fh:
        r1_lines = [line.replace(run_id1, RUN_ID_PLACEHOLDER) for line in r1_fh.readlines()]
        r2_lines = [line.replace(run_id2, RUN_ID_PLACEHOLDER) for line in r2_fh.readlines()]

    out_fh = open(out_path, "w") if out_path else None
    diff = list(difflib.unified_diff(r1_lines, r2_lines))
    if len(diff) > 0:
        for line in diff:
            log_and_write(line.rstrip(), out_fh)
    else:
        log_and_write("No difference found", out_fh)
    if out_fh:
        out_fh.close()


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
        # FIXME: Detect pipeline from the run.log ?
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
