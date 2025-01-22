from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional, Set

from shared.compare import Comparison, do_comparison, parse_var_key_for_sort
from shared.util import prettify_rows
from shared.vcf.annotation import compare_variant_annotation
from shared.vcf.score import get_table
from shared.vcf.vcf import DiffScoredVariant, ScoredVariant, parse_scored_vcf


def compare_variant_presence(
    logger: Logger,
    label_r1: str,
    label_r2: str,
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    comparison_results: Comparison[str],
    max_display: int,
    out_path: Optional[Path],
    show_line_numbers: bool,
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
        show_line_numbers,
        max_display,
    )
    for line in summary_lines:
        logger.info(line)

    if out_path is not None:
        full_summary_lines = get_variant_presence_summary(
            label_r1,
            label_r2,
            common,
            r1_only,
            r2_only,
            variants_r1,
            variants_r2,
            show_line_numbers,
            max_display=None,
        )
        with out_path.open("w") as out_fh:
            for line in full_summary_lines:
                print(line, file=out_fh)


def get_variant_presence_summary(
    label_r1: str,
    label_r2: str,
    common: Set[str],
    r1_only: Set[str],
    r2_only: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    show_line_numbers: bool,
    max_display: Optional[int],
) -> List[str]:
    output: List[str] = []
    output.append(f"# In common: {len(common)}")
    output.append(f"# Only in {label_r1}: {len(r1_only)}")
    output.append(f"# Only in {label_r2}: {len(r2_only)}")

    if len(r1_only) > 0:
        if max_display is not None:
            output.append(
                f"# First {min(len(r1_only), max_display)} only found in {label_r1}"
            )
        else:
            output.append(f"Only found in {label_r1}")

        r1_table: List[List[str]] = []
        for key in sorted(list(r1_only), key=parse_var_key_for_sort)[0:max_display]:
            row_fields = variants_r1[key].get_row(show_line_numbers)
            r1_table.append(row_fields)
        pretty_rows = prettify_rows(r1_table)
        for row in pretty_rows:
            output.append(row)

    if len(r2_only) > 0:
        if max_display is not None:
            output.append(
                f"# First {min(len(r2_only), max_display)} only found in {label_r2}"
            )
        else:
            output.append(f"Only found in {label_r2}")

        r2_table: List[List[str]] = []
        for key in sorted(list(r2_only), key=parse_var_key_for_sort)[0:max_display]:
            row_fields = variants_r2[key].get_row(show_line_numbers)
            r2_table.append(row_fields)
        pretty_rows = prettify_rows(r2_table)
        for row in pretty_rows:
            output.append(row)

    return output


def compare_variant_score(
    logger: Logger,
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
    show_line_numbers: bool,
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
            logger,
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
            show_line_numbers,
        )
    else:
        logger.info("No differently scored variant found")


def print_diff_score_info(
    logger: Logger,
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
    show_line_numbers: bool,
):

    diff_scored_variants.sort(
        key=lambda var: var.r1.get_rank_score(),
        reverse=True,
    )

    diff_variants_above_thres = [
        var for var in diff_scored_variants if var.any_above_thres(score_threshold)
    ]

    logger.info(
        f"# Number differently scored total: {len(diff_scored_variants)}",
    )
    logger.info(
        f"# Number differently scored above {score_threshold}: {len(diff_variants_above_thres)}",
    )
    logger.info(
        f"# Total number shared variants: {len(shared_variant_keys)} ({run_id1}: {len(variants_r1)}, {run_id2}: {len(variants_r2)})",
    )

    # FIXME: Merge with variant.get_row() ? To use just one method
    full_comparison_table = get_table(
        run_id1,
        run_id2,
        diff_scored_variants,
        shared_variant_keys,
        variants_r1,
        variants_r2,
        is_sv,
        show_line_numbers,
    )
    if out_path_all is not None:
        with open(str(out_path_all), "w") as out_fh:
            for row in full_comparison_table:
                print("\t".join(row), file=out_fh)

    if len(diff_variants_above_thres) > max_count:
        logger.info(f"# Only printing the {max_count} first")
    # FIXME: Get rid of this uglyness. It should handle number of cols in a flexible way
    # variant.get_row() might be part of a solution
    nbr_out_cols = 6
    if is_sv:
        nbr_out_cols += 1
    if show_line_numbers:
        nbr_out_cols += 1
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
        show_line_numbers,
    )
    if out_path_above_thres is not None:
        with open(str(out_path_above_thres), "w") as out_fh:
            for row in above_thres_comparison_table:
                print("\t".join(row), file=out_fh)


def variant_comparisons(
    logger: Logger,
    run_id1: str,
    run_id2: str,
    r1_scored_vcf: Path,
    r2_scored_vcf: Path,
    is_sv: bool,
    score_threshold: int,
    max_display: int,
    max_checked_annots: int,
    out_path_presence: Optional[Path],
    out_path_score_above_thres: Optional[Path],
    out_path_score_all: Optional[Path],
    do_score_check: bool,
    do_annot_check: bool,
    show_line_numbers: bool,
):
    vcf_r1 = parse_scored_vcf(r1_scored_vcf, is_sv)
    vcf_r2 = parse_scored_vcf(r2_scored_vcf, is_sv)
    comparison_results = do_comparison(
        set(vcf_r1.variants.keys()),
        set(vcf_r2.variants.keys()),
    )
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
    if do_annot_check:
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