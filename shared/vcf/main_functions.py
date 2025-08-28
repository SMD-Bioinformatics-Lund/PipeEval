from collections import defaultdict
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from commands.eval.classes.helpers import VCFPair
from shared.compare import Comparison, parse_var_key_for_sort
from shared.util import prettify_rows
from shared.vcf.score import get_table, get_table_header
from shared.vcf.vcf import DiffScoredVariant, ScoredVariant


def show_categorical_comparisons(
    logger: Logger, run_ids: Tuple[str, str], category_entries: List[Tuple[str, str]]
):
    logger.info("Hi")

    nbr_identical = 0

    # vcf1_to_vcf2: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # vcf2_to_vcf1: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    vcf1_to_vcf2 = defaultdict(int)
    vcf2_to_vcf1 = defaultdict(int)

    for entry1, entry2 in category_entries:
        if entry1 == entry2:
            nbr_identical += 1

        combined_key = f"{entry1}___{entry2}"

        vcf1_to_vcf2[combined_key] += 1
        vcf2_to_vcf1[combined_key] += 1

    logger.info("Transitions vcf1 to vcf2, falling sorting")
    for key, value in sorted(vcf1_to_vcf2.items(), key=lambda pair: pair[1]):
        logger.info(f"Entry {key} {value}")

    logger.info("Transition vcf2 to vcf1, falling sorting")
    for key, value in sorted(vcf2_to_vcf1.items(), key=lambda pair: pair[1]):
        logger.info(f"Entry {key} {value}")

        # if entry1 not in source1_to_source2:
        #     source1_to_source2[entry1] = {}
        
        # if entry2 not in source1_to_source2[entry1]:
        #     source1_to_source2[entry1][entry2] = 0

        # if entry2 not in source2_to_source1:
        #     source2_to_source1[entry2][entry1] = 0


        


        
        




def check_vcf_filter_differences(
    logger: Logger, run_ids: Tuple[str, str], vcfs: VCFPair, shared_variant_keys: Set[str]
):

    # FIXME: Continue
    # filters = {}

    pairs = []

    for key in shared_variant_keys:
        v1 = vcfs.vcf1.variants[key]
        v2 = vcfs.vcf2.variants[key]

        v1_info = v1.filters
        v2_info = v2.filters

        pair = (v1_info, v2_info)
        pairs.append(pair)
        show_categorical_comparisons(logger, run_ids, pairs)

        # else:
        #     both_present += 1
        #     if v1_info == v2_info:
        #         nbr_same += 1

    # logger.info(
    #     f"Both {both_present} ({nbr_same} same) v1 only {v1_present} v2 only {v2_present} none present {none_present}"
    # )


def check_vcf_sample_differences(
    logger: Logger, run_ids: Tuple[str, str], vcfs: VCFPair, shared_variant_keys: Set[str]
): ...


def check_custom_info_field_differences(
    logger: Logger,
    run_ids: Tuple[str, str],
    vcfs: VCFPair,
    shared_variant_keys: Set[str],
    info_keys: List[str],
):
    for info_key in info_keys:
        logger.info(f"Checking info key {info_key}")
        none_present = 0
        v1_present = 0
        v2_present = 0
        both_present = 0
        nbr_same = 0
        for key in shared_variant_keys:
            v1 = vcfs.vcf1.variants[key]
            v2 = vcfs.vcf2.variants[key]

            v1_info = v1.info_dict.get(info_key)
            v2_info = v2.info_dict.get(info_key)

            if not v1_info and not v2_info:
                none_present += 1
            elif v1_info:
                v1_present += 1
            elif v2_info:
                v2_present += 1
            else:
                both_present += 1
                if v1_info == v2_info:
                    nbr_same += 1

        logger.info(
            f"Both {both_present} ({nbr_same} same) v1 only {v1_present} v2 only {v2_present} none present {none_present}"
        )


def compare_variant_presence(
    logger: Logger,
    run_ids: Tuple[str, str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    comparison_results: Comparison[str],
    max_display: int,
    out_path: Optional[Path],
    show_line_numbers: bool,
    additional_annotations: List[str],
):
    r1_only = comparison_results.r1
    r2_only = comparison_results.r2

    summary_lines = get_variant_presence_summary(
        run_ids,
        r1_only,
        r2_only,
        variants_r1,
        variants_r2,
        show_line_numbers,
        max_display,
        additional_annotations,
    )
    if len(summary_lines) > 0:
        for line in summary_lines:
            logger.info(line)
    else:
        logger.info("No difference found")

    if out_path is not None:
        full_summary_lines = get_variant_presence_summary(
            run_ids,
            r1_only,
            r2_only,
            variants_r1,
            variants_r2,
            show_line_numbers,
            max_display=None,
            additional_annotations=additional_annotations,
        )
        with out_path.open("w") as out_fh:
            for line in full_summary_lines:
                print(line, file=out_fh)


def get_variant_presence_summary(
    run_ids: Tuple[str, str],
    r1_only: Set[str],
    r2_only: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    show_line_numbers: bool,
    max_display: Optional[int],
    additional_annotations: List[str],
) -> List[str]:
    output: List[str] = []

    if len(r1_only) > 0:
        if max_display is not None:
            output.append(f"# First {min(len(r1_only), max_display)} only found in {run_ids[0]}")
        else:
            output.append(f"Only found in {run_ids[0]}")

        r1_table: List[List[str]] = []
        for key in sorted(list(r1_only), key=parse_var_key_for_sort)[0:max_display]:
            row_fields = variants_r1[key].get_row(show_line_numbers, additional_annotations)
            r1_table.append(row_fields)
        pretty_rows = prettify_rows(r1_table)
        for row in pretty_rows:
            output.append(row)

    if len(r2_only) > 0:
        if max_display is not None:
            output.append(f"# First {min(len(r2_only), max_display)} only found in {run_ids[1]}")
        else:
            output.append(f"Only found in {run_ids[1]}")

        r2_table: List[List[str]] = []
        for key in sorted(list(r2_only), key=parse_var_key_for_sort)[0:max_display]:
            row_fields = variants_r2[key].get_row(show_line_numbers, additional_annotations)
            r2_table.append(row_fields)
        pretty_rows = prettify_rows(r2_table)
        for row in pretty_rows:
            output.append(row)

    return output


def compare_variant_score(
    logger: Logger,
    run_ids: Tuple[str, str],
    shared_variants: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    score_threshold: int,
    max_count: int,
    out_path_above_thres: Optional[Path],
    out_path_all: Optional[Path],
    is_sv: bool,
    show_line_numbers: bool,
    annotation_info_keys: List[str],
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
            run_ids,
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
            annotation_info_keys,
        )
    else:
        logger.info("# No differently scored variants found")


def print_diff_score_info(
    logger: Logger,
    run_ids: Tuple[str, str],
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
    annotation_info_keys: List[str],
) -> None:

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
        f"# Total number shared variants: {len(shared_variant_keys)} ({run_ids[0]}: {len(variants_r1)}, {run_ids[1]}: {len(variants_r2)})",
    )

    limited_header = get_table_header(
        run_ids,
        shared_variant_keys,
        variants_r1,
        variants_r2,
        is_sv,
        show_line_numbers,
        annotation_info_keys,
        exclude_subscores=True,
    )

    full_header = get_table_header(
        run_ids,
        shared_variant_keys,
        variants_r1,
        variants_r2,
        is_sv,
        show_line_numbers,
        annotation_info_keys,
        exclude_subscores=False,
    )

    full_body = get_table(
        diff_scored_variants,
        is_sv,
        show_line_numbers,
        annotation_info_keys,
    )
    if out_path_all is not None:
        with open(str(out_path_all), "w") as out_fh:
            out_table = [full_header] + full_body
            for row in out_table:
                print("\t".join(row), file=out_fh)

    if len(diff_variants_above_thres) > max_count:
        logger.info(f"# Only printing the {max_count} first")
    first_rows_and_cols = [limited_header] + [
        row[0 : len(limited_header)] for row in full_body[0:max_count]
    ]

    pretty_rows = prettify_rows(first_rows_and_cols)
    for row in pretty_rows:
        logger.info(row)

    above_thres_comparison_rows = get_table(
        diff_variants_above_thres,
        is_sv,
        show_line_numbers,
        annotation_info_keys,
    )

    if out_path_above_thres is not None:
        full_table = [full_header] + above_thres_comparison_rows
        with open(str(out_path_above_thres), "w") as out_fh:
            for row in full_table:
                print("\t".join(row), file=out_fh)


def write_full_score_table(
    run_ids: Tuple[str, str],
    shared_variant_keys: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    out_path: Path,
    is_sv: bool,
    show_line_numbers: bool,
    annotation_info_keys: List[str],
) -> None:

    all_variants: list[DiffScoredVariant] = [
        DiffScoredVariant(variants_r1[key], variants_r2[key]) for key in shared_variant_keys
    ]

    all_variants.sort(key=lambda var: var.r1.get_rank_score(), reverse=True)

    header = get_table_header(
        run_ids,
        shared_variant_keys,
        variants_r1,
        variants_r2,
        is_sv,
        show_line_numbers,
        annotation_info_keys,
        exclude_subscores=False,
    )

    body = get_table(all_variants, is_sv, show_line_numbers, annotation_info_keys)
    with out_path.open("w") as out_fh:
        for row in [header] + body:
            print("\t".join(row), file=out_fh)
