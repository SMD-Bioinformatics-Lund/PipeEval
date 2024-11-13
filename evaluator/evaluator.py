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

from util.shared_utils import load_config, prettify_rows

from .score_utils import get_table
from .classes import DiffScoredVariant
from .util import (
    Comparison,
    ScoredVariant,
    PathObj,
    any_is_parent,
    count_variants,
    detect_run_id,
    do_comparison,
    get_files_in_dir,
    get_pair_match,
    parse_var_key_for_sort,
    parse_vcf,
    get_files_ending_with,
    verify_pair_exists,
)

# logger = setup_stdout_logger()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RUN_ID_PLACEHOLDER = "RUNID"
VCF_SUFFIX = [".vcf", ".vcf.gz"]

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
):

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    config = load_config(curr_dir, config_path)

    valid_comparisons = set(["default", "file", "vcf", "score", "score_sv", "yaml"])
    if comparisons is not None and len(comparisons & valid_comparisons) == 0:
        raise ValueError(
            f"Valid comparisons are: {valid_comparisons}, found: {comparisons}"
        )

    verify_pair_exists("result dirs", results1_dir, results2_dir)

    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)

    if run_id1 is None:
        run_id1 = detect_run_id(logger, results1_dir.name, verbose)
        logger.info(f"--run_id1 not set, assigned: {run_id1}")

    if run_id2 is None:
        run_id2 = detect_run_id(logger, results2_dir.name, verbose)
        logger.info(f"--run_id2 not set, assigned: {run_id2}")

    r1_paths = get_files_in_dir(results1_dir, run_id1, RUN_ID_PLACEHOLDER, results1_dir)
    r2_paths = get_files_in_dir(results2_dir, run_id2, RUN_ID_PLACEHOLDER, results2_dir)

    if comparisons is None or "file" in comparisons:
        logger.info("")
        logger.info("--- Comparing existing files ---")
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
            compare_vcfs(
                r1_vcfs,
                r2_vcfs,
                run_id1,
                run_id2,
                str(results1_dir),
                str(results2_dir),
                out_path,
            )
        else:
            logger.warning("No VCFs detected, skipping VCF comparison")

    if comparisons is None or "score" in comparisons:
        logger.info("")
        logger.info("--- Comparing scored SNV VCFs ---")

        (r1_scored_snv_vcf, r2_scored_snv_vcf) = get_pair_match(
            logger,
            "scored SNVs",
            config["settings"]["scored_snv"].split(","),
            r1_paths,
            r2_paths,
            verbose,
        )

        out_path_presence = outdir / "scored_snv_presence.txt" if outdir else None
        out_path_score_thres = (
            outdir / f"scored_snv_score_thres_{score_threshold}.txt" if outdir else None
        )
        out_path_score_all = outdir / "scored_snv_score_all.txt" if outdir else None
        is_sv = False
        variant_comparison(
            run_id1,
            run_id2,
            r1_scored_snv_vcf,
            r2_scored_snv_vcf,
            is_sv,
            score_threshold,
            max_display,
            out_path_presence,
            out_path_score_thres,
            out_path_score_all,
        )

    if comparisons is None or "score_sv" in comparisons:
        logger.info("")
        logger.info("--- Comparing scored SV VCFs ---")

        (r1_scored_sv_vcf, r2_scored_sv_vcf) = get_pair_match(
            logger,
            "scored SVs",
            config["settings"]["scored_sv"].split(","),
            r1_paths,
            r2_paths,
            verbose,
        )

        out_path_presence = outdir / "scored_sv_presence.txt" if outdir else None
        out_path_score_thres = (
            outdir / f"scored_sv_score_thres_{score_threshold}.txt" if outdir else None
        )
        out_path_score_all = outdir / "scored_sv_score.txt" if outdir else None
        is_sv = True
        variant_comparison(
            run_id1,
            run_id2,
            r1_scored_sv_vcf,
            r2_scored_sv_vcf,
            is_sv,
            score_threshold,
            max_display,
            out_path_presence,
            out_path_score_thres,
            out_path_score_all,
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

    r1_non_ignored = set()
    for path in sorted(comparison.r1):
        if any_is_parent(path, ignore_files):
            ignored[str(path.parent)] += 1
        else:
            r1_non_ignored.add(path)

    r2_non_ignored = set()
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


def compare_variant_presence(
    label_r1: str,
    label_r2: str,
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    comparison_results: Comparison[str],
    max_display: int,
    out_path: Optional[Path],
):

    common = comparison_results.shared
    r1_only = comparison_results.r1
    r2_only = comparison_results.r2

    summary_lines = get_variant_presence_summary(
        label_r1,
        label_r2,
        common,
        r1_only,
        r2_only,
        variants_r1,
        variants_r2,
        max_display,
    )
    for line in summary_lines:
        logger.info(line)

    if out_path is not None:
        with out_path.open("w") as out_fh:
            for line in summary_lines:
                print(line, file=out_fh)


def get_variant_presence_summary(
    label_r1: str,
    label_r2: str,
    common: Set[str],
    r1_only: Set[str],
    r2_only: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    max_display: Optional[int],
) -> List[str]:
    output = []
    output.append(f"In common: {len(common)}")
    output.append(f"Only in {label_r1}: {len(r1_only)}")
    output.append(f"Only in {label_r2}: {len(r2_only)}")

    if len(r1_only) > 0:
        if max_display is not None:
            output.append(
                f"First {min(len(r1_only), max_display)} only found in {label_r1}"
            )
        else:
            output.append(f"Only found in {label_r1}")
        for key in sorted(list(r1_only), key=parse_var_key_for_sort)[0:max_display]:
            output.append(str(variants_r1[key]))
    if len(r2_only) > 0:
        if max_display is not None:
            output.append(
                f"First {min(len(r2_only), max_display)} only found in {label_r2}"
            )
        else:
            output.append(f"Only found in {label_r2}")
        for key in sorted(list(r2_only), key=parse_var_key_for_sort)[0:max_display]:
            output.append(str(variants_r2[key]))

    return output


def variant_comparison(
    run_id1: str,
    run_id2: str,
    r1_scored_vcf: PathObj,
    r2_scored_vcf: PathObj,
    is_sv: bool,
    score_threshold: int,
    max_display: int,
    out_path_presence: Optional[Path],
    out_path_score_above_thres: Optional[Path],
    out_path_score_all: Optional[Path],
):
    variants_r1 = parse_vcf(r1_scored_vcf, is_sv)
    variants_r2 = parse_vcf(r2_scored_vcf, is_sv)
    comparison_results = do_comparison(
        set(variants_r1.keys()),
        set(variants_r2.keys()),
    )
    compare_variant_presence(
        run_id1,
        run_id2,
        variants_r1,
        variants_r2,
        comparison_results,
        max_display,
        out_path_presence,
    )
    shared_variants = comparison_results.shared
    compare_variant_score(
        run_id1,
        run_id2,
        shared_variants,
        variants_r1,
        variants_r2,
        score_threshold,
        max_display,
        out_path_score_above_thres,
        out_path_score_all,
        is_sv,
    )


def compare_vcfs(
    r1_vcfs: List[PathObj],
    r2_vcfs: List[PathObj],
    run_id1: str,
    run_id2: str,
    r1_base: str,
    r2_base: str,
    out_path: Optional[Path],
):

    r1_counts: Dict[str, int] = {}
    for vcf in r1_vcfs:
        if vcf.check_valid_file():
            n_variants = count_variants(vcf)
        else:
            n_variants = 0
        r1_counts[str(vcf).replace(r1_base, "")] = n_variants

    r2_counts: Dict[str, int] = {}
    for vcf in r2_vcfs:
        if vcf.check_valid_file():
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


def compare_variant_score(
    run_id1: str,
    run_id2: str,
    shared_variants: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    score_threshold: int,
    max_count: int,
    out_path_above_thres: Optional[Path],
    out_path_all: Optional[Path],
    is_sv: bool,
):

    diff_scored_variants: List[DiffScoredVariant] = []

    for var_key in shared_variants:
        r1_variant = variants_r1[var_key]
        r2_variant = variants_r2[var_key]
        if r1_variant.rank_score != r2_variant.rank_score:
            diff_scored_variant = DiffScoredVariant(r1_variant, r2_variant)
            diff_scored_variants.append(diff_scored_variant)

    if len(diff_scored_variants) > 0:
        print_diff_score_info(
            run_id1,
            run_id2,
            diff_scored_variants,
            shared_variants,
            variants_r1,
            variants_r2,
            out_path_all,
            out_path_above_thres,
            max_count,
            score_threshold,
            is_sv,
        )
    else:
        logger.info("No differently scored variant found")


def print_diff_score_info(
    run_id1: str,
    run_id2: str,
    diff_scored_variants: List[DiffScoredVariant],
    shared_variant_keys: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    out_path_all: Optional[Path],
    out_path_above_thres: Optional[Path],
    max_count: int,
    score_threshold: int,
    is_sv: bool,
):

    diff_scored_variants.sort(
        key=lambda var: var.r1.get_rank_score(),
        reverse=True,
    )

    diff_variants_above_thres = [
        var for var in diff_scored_variants if var.any_above_thres(score_threshold)
    ]

    logger.info(
        f"Number differently scored total: {len(diff_scored_variants)}",
    )
    logger.info(
        f"Number differently scored above {score_threshold}: {len(diff_variants_above_thres)}",
    )

    full_comparison_table = get_table(
        run_id1,
        run_id2,
        diff_scored_variants,
        shared_variant_keys,
        variants_r1,
        variants_r2,
        is_sv,
    )
    if out_path_all is not None:
        with open(str(out_path_all), "w") as out_fh:
            for row in full_comparison_table:
                print("\t".join(row), file=out_fh)

    if len(diff_variants_above_thres) > max_count:
        logger.info(f"Only printing the {max_count} first")
    nbr_out_cols = 7 if is_sv else 6
    first_rows_and_cols = [
        full_row[0:nbr_out_cols] for full_row in full_comparison_table[0:max_count]
    ]
    pretty_rows = prettify_rows(first_rows_and_cols)
    for row in pretty_rows:
        logger.info(row)

    above_thres_comparison_table = get_table(
        run_id1,
        run_id2,
        diff_variants_above_thres,
        shared_variant_keys,
        variants_r1,
        variants_r2,
        is_sv,
    )
    if out_path_above_thres is not None:
        with open(str(out_path_above_thres), "w") as out_fh:
            for row in above_thres_comparison_table:
                print("\t".join(row), file=out_fh)


def diff_compare_files(
    run_id1: str,
    run_id2: str,
    file1: PathObj,
    file2: PathObj,
    out_path: Optional[Path],
):

    with file1.get_filehandle() as r1_fh, file2.get_filehandle() as r2_fh:
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
    parser.add_argument("--results1", "-r1", required=True)
    parser.add_argument("--results2", "-r2", required=True)
    parser.add_argument("--config", help="Additional configurations")
    parser.add_argument(
        "--comparisons",
        help="Comma separated. Defaults to: default, run all by: file,vcf,score,score_sv,yaml",
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
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
