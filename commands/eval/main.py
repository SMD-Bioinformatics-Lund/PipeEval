#!/usr/bin/env python3

import argparse
from io import TextIOWrapper
from pathlib import Path
import os
from typing import (
    List,
    Optional,
    Dict,
    Set,
)
from collections import defaultdict
import difflib
import logging

from shared.compare import do_comparison
from shared.constants import RUN_ID_PLACEHOLDER
from shared.file import check_valid_file, get_filehandle
from shared.util import load_config
from shared.vcf.main_functions import variant_comparisons
from shared.vcf.vcf import count_variants

from .util import (
    PathObj,
    any_is_parent,
    detect_run_id,
    get_files_in_dir,
    get_pair_match,
    get_files_ending_with,
    verify_pair_exists,
)

# logger = setup_stdout_logger()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VCF_SUFFIX = [".vcf", ".vcf.gz"]
VALID_COMPARISONS = set(
    [
        "default",
        "file",
        "vcf",
        "score_snv",
        "score_sv",
        "yaml",
        "annotation_snv",
        "annotation_sv",
    ]
)

description = """
Compare results for runs in the CMD constitutional pipeline.

Performs all or a subset of the comparisons:

- What files are present
- Do the VCF files have the same number of variants
- For the scored SNV and SV VCFs, what are call differences and differences in rank scores
- Are there differences in the Scout yaml
"""


def log_and_write(text: str, fh: Optional[TextIOWrapper]):
    logger.info(text)
    if fh is not None:
        print(text, file=fh)


def main(
    run_id1: Optional[str],
    run_id2: Optional[str],
    results1_dir: Path,
    results2_dir: Path,
    config_path: str,
    comparisons: Optional[Set[str]],
    score_threshold: int,
    max_display: int,
    outdir: Optional[Path],
    verbose: bool,
    max_checked_annots: int,
    show_line_numbers: bool,
    annotation_info_keys: List[str],
):

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    config = load_config(logger, curr_dir, config_path)

    if comparisons is not None and len(comparisons & VALID_COMPARISONS) == 0:
        raise ValueError(
            f"Valid comparisons are: {VALID_COMPARISONS}, found: {comparisons}"
        )

    verify_pair_exists("result dirs", results1_dir, results2_dir)

    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)

    if run_id1 is None:
        run_id1 = detect_run_id(logger, results1_dir.name, verbose)
        logger.info(f"# --run_id1 not set, assigned: {run_id1}")

    if run_id2 is None:
        run_id2 = detect_run_id(logger, results2_dir.name, verbose)
        logger.info(f"# --run_id2 not set, assigned: {run_id2}")

    r1_paths = get_files_in_dir(results1_dir, run_id1, RUN_ID_PLACEHOLDER, results1_dir)
    r2_paths = get_files_in_dir(results2_dir, run_id2, RUN_ID_PLACEHOLDER, results2_dir)

    if comparisons is None or "file" in comparisons:
        logger.info("")
        logger.info("### Comparing existing files ###")
        out_path = outdir / "check_sample_files.txt" if outdir else None

        check_same_files(
            run_id1,
            run_id2,
            r1_paths,
            r2_paths,
            config.get("settings", "ignore").split(","),
            out_path,
        )

    if comparisons is not None and "vcf" in comparisons:
        logger.info("")
        logger.info("--- Comparing VCF numbers ---")
        is_vcf_pattern = ".vcf$|.vcf.gz$"
        r1_vcfs = get_files_ending_with(is_vcf_pattern, r1_paths)
        r2_vcfs = get_files_ending_with(is_vcf_pattern, r2_paths)
        if verbose:
            logger.info(f"Looking for paths: {r1_paths} found: {r1_vcfs}")
            logger.info(f"Looking for paths: {r2_paths} found: {r2_vcfs}")
        if len(r1_vcfs) > 0 or len(r2_vcfs) > 0:
            out_path = outdir / "all_vcf_compare.txt" if outdir else None
            compare_all_vcfs(
                [path_obj.real_path for path_obj in r1_vcfs],
                [path_obj.real_path for path_obj in r2_vcfs],
                run_id1,
                run_id2,
                str(results1_dir),
                str(results2_dir),
                out_path,
            )
        else:
            logger.warning("No VCFs detected, skipping VCF comparison")

    if (
        comparisons is None
        or "score_snv" in comparisons
        or "annotation_snv" in comparisons
    ):
        logger.info("")
        logger.info("--- Comparing scored SNV VCFs ---")

        (r1_scored_snv_vcf, r2_scored_snv_vcf) = get_pair_match(
            logger,
            "scored SNVs",
            config["settings"]["scored_snv"].split(","),
            r1_paths,
            r2_paths,
            results1_dir,
            results2_dir,
            verbose,
        )

        out_path_presence = outdir / "scored_snv_presence.txt" if outdir else None
        out_path_score_thres = (
            outdir / f"scored_snv_score_thres_{score_threshold}.txt" if outdir else None
        )
        out_path_score_all = outdir / "scored_snv_score_all.txt" if outdir else None
        is_sv = False
        variant_comparisons(
            logger,
            run_id1,
            run_id2,
            r1_scored_snv_vcf,
            r2_scored_snv_vcf,
            is_sv,
            score_threshold,
            max_display,
            max_checked_annots,
            out_path_presence,
            out_path_score_thres,
            out_path_score_all,
            comparisons is None or "score_snv" in comparisons,
            comparisons is None or "annotation_snv" in comparisons,
            show_line_numbers,
            annotation_info_keys,
        )

    if (
        comparisons is None
        or "score_sv" in comparisons
        or "annotation_sv" in comparisons
    ):
        logger.info("")
        logger.info("--- Comparing scored SV VCFs ---")

        (r1_scored_sv_vcf, r2_scored_sv_vcf) = get_pair_match(
            logger,
            "scored SVs",
            config["settings"]["scored_sv"].split(","),
            r1_paths,
            r2_paths,
            results1_dir,
            results2_dir,
            verbose,
        )

        out_path_presence = outdir / "scored_sv_presence.txt" if outdir else None
        out_path_score_thres = (
            outdir / f"scored_sv_score_thres_{score_threshold}.txt" if outdir else None
        )
        out_path_score_all = outdir / "scored_sv_score.txt" if outdir else None
        is_sv = True
        variant_comparisons(
            logger,
            run_id1,
            run_id2,
            r1_scored_sv_vcf,
            r2_scored_sv_vcf,
            is_sv,
            score_threshold,
            max_display,
            max_checked_annots,
            out_path_presence,
            out_path_score_thres,
            out_path_score_all,
            comparisons is None or "score_sv" in comparisons,
            comparisons is None or "annotation_sv" in comparisons,
            show_line_numbers,
            annotation_info_keys,
        )

    if comparisons is None or "yaml" in comparisons:
        logger.info("")
        logger.info("--- Comparing YAML ---")
        (r1_yaml, r2_yaml) = get_pair_match(
            logger,
            "Scout YAMLs",
            config["settings"]["yaml"].split(","),
            r1_paths,
            r2_paths,
            results1_dir,
            results2_dir,
            verbose,
        )
        out_path = outdir / "yaml_diff.txt" if outdir else None
        diff_compare_files(run_id1, run_id2, r1_yaml, r2_yaml, out_path)

    if comparisons is None or "versions" in comparisons:
        logger.info("")
        logger.info("--- Comparing version files ---")
        (r1_versions, r2_versions) = get_pair_match(
            logger,
            "versions",
            config["settings"]["versions"].split(","),
            r1_paths,
            r2_paths,
            results1_dir,
            results2_dir,
            verbose,
        )
        out_path = outdir / "yaml_diff.txt" if outdir else None
        diff_compare_files(run_id1, run_id2, r1_versions, r2_versions, out_path)


def check_same_files(
    r1_label: str,
    r2_label: str,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    ignore_files: List[str],
    out_path: Optional[Path],
):

    files_in_results1 = set(path.relative_path for path in r1_paths)
    files_in_results2 = set(path.relative_path for path in r2_paths)

    comparison = do_comparison(files_in_results1, files_in_results2)
    ignored: defaultdict[str, int] = defaultdict(int)

    out_fh = open(out_path, "w") if out_path else None

    r1_non_ignored: Set[Path] = set()
    for path in sorted(comparison.r1):
        if any_is_parent(path, ignore_files):
            ignored[str(path.parent)] += 1
        else:
            r1_non_ignored.add(path)

    r2_non_ignored: Set[Path] = set()
    for path in sorted(comparison.r2):
        if any_is_parent(path, ignore_files):
            ignored[str(path.parent)] += 1
        else:
            r2_non_ignored.add(path)

    if len(r1_non_ignored) > 0:
        log_and_write(f"Files present in {r1_label} but missing in {r2_label}:", out_fh)
        for path in sorted(comparison.r1):
            log_and_write(f"  {path}", out_fh)

    if len(r2_non_ignored) > 0:
        log_and_write(f"Files present in {r2_label} but missing in {r1_label}:", out_fh)
        for path in sorted(comparison.r2):
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
    r1_vcfs: List[Path],
    r2_vcfs: List[Path],
    run_id1: str,
    run_id2: str,
    r1_base: str,
    r2_base: str,
    out_path: Optional[Path],
):
    r1_counts: Dict[str, int] = {}
    for vcf in r1_vcfs:
        if check_valid_file(vcf):
            n_variants = count_variants(vcf)
        else:
            n_variants = 0
        r1_counts[str(vcf).replace(r1_base, "")] = n_variants

    r2_counts: Dict[str, int] = {}
    for vcf in r2_vcfs:
        if check_valid_file(vcf):
            n_variants = count_variants(vcf)
        else:
            n_variants = 0
        r2_counts[str(vcf).replace(r2_base, "")] = n_variants

    paths = r1_counts.keys() | r2_counts.keys()

    max_path_length = max(len(path) for path in paths)

    out_fh = open(out_path, "w") if out_path else None
    log_and_write(f"{'Path':<{max_path_length}} {run_id1:>10} {run_id2:>10}", out_fh)
    for path in sorted(paths):
        r1_val = r1_counts.get(path) or "-"
        r2_val = r2_counts.get(path) or "-"
        log_and_write(
            f"{path:<{max_path_length}} {r1_val:>{len(run_id1)}} {r2_val:>{len(run_id2)}}",
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
        r1_lines = [
            line.replace(run_id1, RUN_ID_PLACEHOLDER) for line in r1_fh.readlines()
        ]
        r2_lines = [
            line.replace(run_id2, RUN_ID_PLACEHOLDER) for line in r2_fh.readlines()
        ]

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
        "--run_id1",
        "-i1",
        help="The group ID is used in some file names and can differ between runs. If not provided, it is set to the base folder name.",
    )
    parser.add_argument("--run_id2", "-i2", help="See --run_id1 help")
    parser.add_argument("--results1", "-r1", "-1", required=True)
    parser.add_argument("--results2", "-r2", "-2", required=True)
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


def main_wrapper(args: argparse.Namespace):
    main(
        args.run_id1,
        args.run_id2,
        Path(args.results1),
        Path(args.results2),
        args.config,
        None if args.comparisons == "default" else set(args.comparisons.split(",")),
        args.score_threshold,
        args.max_display,
        Path(args.outdir) if args.outdir is not None else None,
        args.verbose,
        args.max_checked_annots,
        args.show_line_numbers,
        args.annotations.split(",") if args.annotations is not None else [],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
