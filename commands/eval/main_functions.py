import difflib
from collections import Counter
from configparser import SectionProxy
from io import TextIOWrapper
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from commands.eval.classes.helpers import PathObj, RunSettings, VCFPair
from commands.eval.classes.run_object import RunObject
from commands.eval.constants import FILE_NAMES
from commands.eval.utils import get_ignored, get_pair_match
from shared.compare import do_comparison
from shared.constants import RUN_ID_PLACEHOLDER
from shared.file import check_valid_file, get_filehandle
from shared.vcf.annotation import compare_variant_annotation
from shared.vcf.main_functions import (
    check_custom_info_field_differences,
    check_vcf_filter_differences,
    check_vcf_sample_differences,
    compare_variant_presence,
    compare_variant_score,
    write_full_score_table,
)
from shared.vcf.vcf import count_variants


def check_comparison(all_comparisons: Optional[Set[str]], target_comparison: str) -> bool:
    if all_comparisons is None:
        return True
    comparison_keys = [comp.split("=")[0] for comp in all_comparisons]
    return target_comparison in comparison_keys


def log_and_write(logger: Logger, text: str, fh: Optional[TextIOWrapper]):
    logger.info(text)
    if fh is not None:
        print(text, file=fh)


def vcf_comparisons(
    logger: Logger,
    comparisons: Optional[Set[str]],
    run_ids: Tuple[str, str],
    outdir: Optional[Path],
    rs: RunSettings,
    vcf_type: str,
    vcfs: VCFPair,
):

    if check_comparison(comparisons, f"filter_{vcf_type}") and vcfs is not None:
        logger.info("")
        logger.info("### Checking filter differences ###")
        check_vcf_filter_differences(logger, run_ids, vcfs, vcfs.comp.shared)

    if check_comparison(comparisons, f"sample_{vcf_type}") and vcfs is not None:
        logger.info("")
        logger.info("### Checking sample differences ###")
        check_vcf_sample_differences(logger, run_ids, vcfs, vcfs.comp.shared)

    if (
        comparisons is not None
        and check_comparison(comparisons, f"custom_info_{vcf_type}")
        and vcfs is not None
    ):
        custom_info_keys_field = [
            comp for comp in comparisons if comp.startswith(f"custom_info_{vcf_type}")
        ][0]
        info_keys = custom_info_keys_field.split("=")[1].split(",")

        logger.info("")
        logger.info(f"### Checking custom info keys {', '.join(info_keys)} ###")

        check_custom_info_field_differences(logger, run_ids, vcfs, vcfs.comp.shared, info_keys)

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
    logger: Logger,
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
        log_and_write(logger, f"Files present in {ro.r1_id} but missing in {ro.r2_id}:", out_fh)
        for path in sorted(r1_non_ignored):
            log_and_write(logger, f"  {path}", out_fh)

    if len(r2_non_ignored) > 0:
        log_and_write(logger, f"Files present in {ro.r2_id} but missing in {ro.r1_id}:", out_fh)
        for path in sorted(r2_non_ignored):
            log_and_write(logger, f"  {path}", out_fh)

    if len(r1_non_ignored) == 0 and len(r2_non_ignored) == 0:
        log_and_write(logger, "All non-ignored files present in both results", out_fh)

    if len(ignored) > 0:
        log_and_write(logger, "Ignored", out_fh)
        for key, val in ignored.items():
            log_and_write(logger, f"  {key}: {val}", out_fh)

    if out_fh:
        out_fh.close()


def do_file_diff(
    logger: Logger,
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
        logger,
        ro,
        r1_paths,
        r2_paths,
        ignore_files,
        out_path,
    )


def compare_all_vcfs(
    logger: Logger,
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
    log_and_write(logger, f"{'Path':<{max_path_length}} {ro.r1_id:>10} {ro.r2_id:>10}", out_fh)
    for path in sorted(paths):
        r1_val = r1_counts.get(path) or "-"
        r2_val = r2_counts.get(path) or "-"
        log_and_write(
            logger,
            f"{path:<{max_path_length}} {r1_val:>{len(ro.r1_id)}} {r2_val:>{len(ro.r2_id)}}",
            out_fh,
        )

    if out_fh:
        out_fh.close()


def diff_compare_files(
    logger: Logger,
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
            log_and_write(logger, line.rstrip(), out_fh)
    else:
        log_and_write(logger, "No difference found", out_fh)
    if out_fh:
        out_fh.close()


def do_simple_diff(
    logger: Logger,
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
        logger.warning(f"At least one file missing ({matched_pair})")
    else:
        out_path = outdir / FILE_NAMES[analysis] if outdir else None
        diff_compare_files(logger, ro.r1_id, ro.r2_id, matched_pair[0], matched_pair[1], out_path)
