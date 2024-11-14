from logging import Logger
from typing import Dict, Set, List
from collections import defaultdict

from evaluator.classes import ScoredVariant
from evaluator.util import do_comparison
from util.constants import MAX_STR_LEN
from util.shared_utils import prettify_rows, truncate_string


class AnnotComp:
    def __init__(
        self,
        variant_key: str,
        info_key: str,
        variant_basic_info: str,
        r1_annot: str,
        r2_annot: str,
    ):
        self.variant_key = variant_key
        self.info_key = info_key
        self.variant_basic_info = variant_basic_info
        self.r1_annot = r1_annot
        self.r2_annot = r2_annot


def compare_variant_annotation(
    logger: Logger,
    run_id1: str,
    run_id2: str,
    shared_variant_keys: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    max_considered: int,
):
    r1_only = defaultdict(int)
    r2_only = defaultdict(int)

    diffs_per_annot_key: defaultdict[str, List[AnnotComp]] = defaultdict(list)

    nbr_checked = 0
    for variant_key in sorted(shared_variant_keys):
        var_r1 = variants_r1[variant_key]
        var_r2 = variants_r2[variant_key]

        annot_keys_r1 = var_r1.info_dict.keys()
        annot_keys_r2 = var_r2.info_dict.keys()
        comparison_results = do_comparison(set(annot_keys_r1), set(annot_keys_r2))
        for info_key in comparison_results.r1:
            r1_only[info_key] += 1
        for info_key in comparison_results.r2:
            r2_only[info_key] += 1

        for shared_annot_key in comparison_results.shared:
            info_val_r1 = var_r1.info_dict[shared_annot_key]
            info_val_r2 = var_r2.info_dict[shared_annot_key]

            if info_val_r1 != info_val_r2:
                annot_comp = AnnotComp(
                    variant_key,
                    shared_annot_key,
                    variants_r1[variant_key].get_basic_info(),
                    info_val_r1,
                    info_val_r2,
                )
                diffs_per_annot_key[shared_annot_key].append(annot_comp)

        nbr_checked += 1
        if nbr_checked >= max_considered:
            logger.info(f"Breaking after looking at {nbr_checked} entries")
            break

    if len(r1_only) == 0 and len(r2_only) == 0:
        logger.info(
            f"No annotation keys found uniquely in one VCF among first {max_considered} variants"
        )
    else:
        if len(r1_only) > 0:
            logger.info(
                f"Annotation keys only found in {run_id1} among {max_considered} variants"
            )
            for variant_key, val in r1_only:
                logger.info(f"{variant_key}: {val}")
        if len(r2_only) > 0:
            logger.info(
                f"Annotation keys only found in {run_id2} among {max_considered} variants"
            )
            for variant_key, val in r2_only:
                logger.info(f"{variant_key}: {val}")

    if len(diffs_per_annot_key) == 0:
        logger.info(f"Among shared annotation keys, all values were the same")
    else:
        logger.info(
            f"Found {len(diffs_per_annot_key)} shared keys with differing annotation values among {max_considered} variants"
        )
        logger.info("Showing number differing and first variant for each annotation")
        print_annot_value_diff(logger, diffs_per_annot_key)


def print_annot_value_diff(logger: Logger, diffs_per_annot: Dict[str, List[AnnotComp]]):

    output_rows = []
    for info_key, annot_value_diffs in diffs_per_annot.items():
        first_differing_variant = annot_value_diffs[0]
        r1_val = first_differing_variant.r1_annot
        r2_val = first_differing_variant.r2_annot
        variant_info = first_differing_variant.variant_basic_info
        example_r1 = truncate_string(r1_val, MAX_STR_LEN)
        example_r2 = truncate_string(r2_val, MAX_STR_LEN)
        row = [
            info_key,
            len(annot_value_diffs),
            variant_info,
            f"{example_r1} / {example_r2}",
        ]
        output_rows.append(row)

    pretty_rows = prettify_rows(output_rows, padding=2)
    for pretty_row in pretty_rows:
        logger.info(pretty_row)


#     # Get max length of each column for visually nice padding
#     info_key_length = max([len(info_key) for info_key in diffs_per_annot])
#     # Get the str-length of the counts
#     count_length = max(
#         [len(str(len(info_nbr))) for info_nbr in diffs_per_annot.values()]
#     )
#     var_info_length = max(
#         [
#             len(differing_vals[0].variant_key)
#             for differing_vals in diffs_per_annot.values()
#         ]
#     )

#     for info_key, differing_vals in diffs_per_annot.items():
#         line = get_annot_info_for_one(
#             differing_vals,
#             MAX_STR_LEN,
#             info_key,
#             info_key_length,
#             count_length,
#             var_info_length,
#         )

#         logger.info(line)


# def get_annot_info_for_one(
#     differing_vals: List[AnnotComp],
#     max_str_len: int,
#     info_key: str,
#     info_key_length: int,
#     count_length: int,
#     var_info_length: int,
# ) -> str:
#     first_differing_variant = differing_vals[0]
#     r1_val = first_differing_variant.r1_annot
#     r2_val = first_differing_variant.r2_annot
#     variant_info = first_differing_variant.variant_basic_info
#     example_r1 = truncate_string(r1_val, max_str_len)
#     example_r2 = truncate_string(r2_val, max_str_len)

#     key_col = f"{info_key.ljust(info_key_length + 2)}"
#     count_col = f"{str(len(differing_vals)).ljust(count_length + 2)}"
#     variant_info_col = f"{variant_info.ljust(var_info_length + 2)}"

#     return f"{key_col} {count_col} {variant_info_col} {example_r1} / {example_r2}"
