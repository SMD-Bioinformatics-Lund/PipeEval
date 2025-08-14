#!/usr/bin/env python3

import argparse
import difflib
import logging
import os
from collections import Counter
from io import TextIOWrapper
from pathlib import Path
from typing import Dict, List, Optional, Set

from commands.eval.classes.pathobj import PathObj
from commands.eval.classes.run_object import (
    RunObject,
    get_files_in_dir,
    get_run_object,
)
from commands.eval.classes.run_settings import RunSettings
from commands.eval.classes.score_paths import ScorePaths
from shared.compare import do_comparison
from shared.constants import IS_VCF_PATTERN, RUN_ID_PLACEHOLDER
from shared.file import check_valid_file, get_filehandle
from shared.util import load_config
from shared.vcf.main_functions import variant_comparisons
from shared.vcf.vcf import count_variants

from .utils import (
    get_files_ending_with,
    get_ignored,
    get_pair_match,
    get_pair_matches,
    verify_pair_exists,
)

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
        "qc",
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
- Are there differences in the QC report
"""


def log_and_write(text: str, fh: Optional[TextIOWrapper]):
    logger.info(text)
    if fh is not None:
        print(text, file=fh)


def main(  # noqa: C901 (skipping complexity check)
    ro: RunObject,
    rs: RunSettings,
    config_path: Optional[str],
    comparisons: Optional[Set[str]],
    outdir: Optional[Path],
):

    r1_paths = get_files_in_dir(
        ro.r1_results, ro.r1_id, RUN_ID_PLACEHOLDER, ro.r1_results
    )
    r2_paths = get_files_in_dir(
        ro.r2_results, ro.r2_id, RUN_ID_PLACEHOLDER, ro.r2_results
    )

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    config = load_config(logger, curr_dir, config_path)

    if comparisons is not None and len(comparisons & VALID_COMPARISONS) == 0:
        raise ValueError(
            f"Valid comparisons are: {VALID_COMPARISONS}, found: {comparisons}"
        )

    verify_pair_exists("result dirs", ro.r1_results, ro.r2_results)

    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)

    if comparisons is None or "file" in comparisons:
        out_path = outdir / "check_sample_files.txt" if outdir else None
        logger.info("")
        logger.info("### Comparing existing files ###")

        ignore_files = config.get("settings", "ignore", fallback="").split(",")

        check_same_files(
            ro,
            r1_paths,
            r2_paths,
            ignore_files,
            out_path,
        )

    if comparisons is not None and "vcf" in comparisons:
        logger.info("")
        logger.info("--- Comparing VCF numbers ---")

        r1_vcfs = [p.real_path for p in get_files_ending_with(IS_VCF_PATTERN, r1_paths)]
        r2_vcfs = [p.real_path for p in get_files_ending_with(IS_VCF_PATTERN, r2_paths)]

        if len(r1_vcfs) > 0 or len(r2_vcfs) > 0:
            out_path = outdir / "all_vcf_compare.txt" if outdir else None
            compare_all_vcfs(
                ro,
                r1_vcfs,
                r2_vcfs,
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

        scored_snv_pair = get_pair_match(
            logger,
            "scored SNVs",
            config["settings"]["scored_snv"].split(","),
            ro,
            r1_paths,
            r2_paths,
            rs.verbose,
        )

        if scored_snv_pair is None:
            logger.warning(
                f"Skipping scored SNV comparison due to missing files ({scored_snv_pair})"
            )
        else:

            snv_score_paths = ScorePaths(
                "snv", outdir, rs.score_threshold, rs.output_all_variants
            )

            is_sv = False
            variant_comparisons(
                logger,
                ro.r1_id,
                ro.r2_id,
                scored_snv_pair[0],
                scored_snv_pair[1],
                is_sv,
                rs,
                snv_score_paths,
                comparisons is None or "score_snv" in comparisons,
                comparisons is None or "annotation_snv" in comparisons,
            )

    if (
        comparisons is None
        or "score_sv" in comparisons
        or "annotation_sv" in comparisons
    ):
        logger.info("")
        logger.info("--- Comparing scored SV VCFs ---")

        scored_sv_pair = get_pair_match(
            logger,
            "scored SVs",
            config["settings"]["scored_sv"].split(","),
            ro,
            r1_paths,
            r2_paths,
            rs.verbose,
        )

        if scored_sv_pair is None:
            logger.warning(
                f"Skipping scored SV comparison due to missing files {scored_sv_pair}"
            )
        else:

            sv_score_paths = ScorePaths(
                "sv", outdir, rs.score_threshold, rs.output_all_variants
            )

            is_sv = True
            variant_comparisons(
                logger,
                ro.r1_id,
                ro.r2_id,
                scored_sv_pair[0],
                scored_sv_pair[1],
                is_sv,
                rs,
                sv_score_paths,
                comparisons is None or "score_sv" in comparisons,
                comparisons is None or "annotation_sv" in comparisons,
            )

    if comparisons is None or "yaml" in comparisons:
        logger.info("")
        logger.info("--- Comparing YAML ---")
        yaml_pair = get_pair_match(
            logger,
            "Scout YAMLs",
            config["settings"]["yaml"].split(","),
            ro,
            r1_paths,
            r2_paths,
            rs.verbose,
        )
        if not yaml_pair:
            logging.warning(
                f"Skipping yaml comparison, at least one file missing ({yaml_pair})"
            )
        else:
            out_path = outdir / "yaml_diff.txt" if outdir else None
            diff_compare_files(ro.r1_id, ro.r2_id, yaml_pair[0], yaml_pair[1], out_path)

    if comparisons is None or "qc" in comparisons:
        logger.info("")
        logger.info("--- Comparing QC for samples ---")

        qc_pairs = get_pair_matches(
            logger,
            "QC files",
            config["settings"]["qc"],
            ro,
            r1_paths,
            r2_paths,
            rs.verbose,
        )
        if len(qc_pairs) == 0:
            logging.warning(
                f"Skipping QC comparisons, no matching pairs found"
            )
        else:
            for qc_pair in qc_pairs:
                out_path = outdir / f"qc_diff_{qc_pair[0].sample_id}.txt" if outdir else None
                logger.info(f"Showing differences for sample {qc_pair[0].sample_id}")
                diff_compare_files(ro.r1_id, ro.r2_id, qc_pair[0].path, qc_pair[1].path, out_path)

    if comparisons is None or "versions" in comparisons:
        logger.info("")
        logger.info("--- Comparing version files ---")
        version_pair = get_pair_match(
            logger,
            "versions",
            config["settings"]["versions"].split(","),
            ro,
            r1_paths,
            r2_paths,
            rs.verbose,
        )
        if not version_pair:
            logging.warning(f"At least one version file missing ({version_pair})")
        else:
            out_path = outdir / "yaml_diff.txt" if outdir else None
            diff_compare_files(
                ro.r1_id, ro.r2_id, version_pair[0], version_pair[1], out_path
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

    (r1_nbr_ignored_per_pattern, r1_non_ignored) = get_ignored(
        comparison.r1, ignore_files
    )
    (r2_nbr_ignored_per_pattern, r2_non_ignored) = get_ignored(
        comparison.r2, ignore_files
    )

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
