from logging import Logger
from typing import Dict, Set, List, Tuple
from collections import defaultdict

from shared.compare import do_comparison, parse_var_key_for_sort
from shared.constants import MAX_STR_LEN, RUN_ID_PLACEHOLDER
from shared.util import prettify_rows, truncate_string
from shared.vcf.vcf import ScoredVariant


class AnnotComp:
    def __init__(
        self,
        variant_key: str,
        info_key: str,
        variant: ScoredVariant,
        r1_annot: str,
        r2_annot: str,
    ):
        self.variant_key = variant_key
        self.info_key = info_key
        self.variant_pos = variant
        self.variant = variant
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

    (diffs_per_annot_key, r1_only_annots, r2_only_annots) = calculate_annotation_diffs(
        shared_variant_keys, variants_r1, variants_r2, max_considered, run_id1, run_id2
    )

    if max_considered < len(shared_variant_keys):
        logger.info(
            f"Checking first {max_considered} out of {len(shared_variant_keys)} variants"
        )

    if len(r1_only_annots) == 0 and len(r2_only_annots) == 0:
        logger.info(
            f"No annotation keys found uniquely in one VCF among first {max_considered} variants"
        )
    else:
        if len(r1_only_annots) > 0:
            logger.info(
                f"Annotation keys only found in {run_id1} among {max_considered} variants"
            )
            for variant_key, val in r1_only_annots.items():
                logger.info(f"{variant_key}: {val}")
        else:
            logger.info(f"No annotation keys found only in {run_id1}")
        if len(r2_only_annots) > 0:
            logger.info(
                f"Annotation keys only found in {run_id2} among {max_considered} variants"
            )
            for variant_key, val in r2_only_annots.items():
                logger.info(f"{variant_key}: {val}")
        else:
            logger.info(f"No annotation keys found only in {run_id2}")

    if len(diffs_per_annot_key) == 0:
        logger.info(f"Among shared annotation keys, all values were the same")
    else:
        logger.info(
            f"Found {len(diffs_per_annot_key)} shared keys with differing annotation values among {max_considered} variants"
        )
        logger.info("Showing number differing and first variant for each annotation")
        annot_value_diff_summary_rows = get_annot_value_diff_summary(
            diffs_per_annot_key
        )
        for row in annot_value_diff_summary_rows:
            logger.info(row)


def calculate_annotation_diffs(
    shared_variant_keys: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    max_considered: int,
    run_id1: str,
    run_id2: str,
) -> Tuple[Dict[str, List[AnnotComp]], Dict[str, int], Dict[str, int]]:
    r1_only_annots: Dict[str, int] = defaultdict(int)
    r2_only_annots: Dict[str, int] = defaultdict(int)

    diffs_per_annot_key: defaultdict[str, List[AnnotComp]] = defaultdict(list)
    nbr_checked = 0
    for variant_key in sorted(shared_variant_keys, key=parse_var_key_for_sort):
        var_r1 = variants_r1[variant_key]
        var_r2 = variants_r2[variant_key]

        annot_keys_r1 = var_r1.info_dict.keys()
        annot_keys_r2 = var_r2.info_dict.keys()
        comparison_results = do_comparison(set(annot_keys_r1), set(annot_keys_r2))
        for info_key in comparison_results.r1:
            r1_only_annots[info_key] += 1
        for info_key in comparison_results.r2:
            r2_only_annots[info_key] += 1

        for shared_annot_key in comparison_results.shared:
            info_val_r1 = var_r1.info_dict[shared_annot_key].replace(
                run_id1, RUN_ID_PLACEHOLDER
            )
            info_val_r2 = var_r2.info_dict[shared_annot_key].replace(
                run_id2, RUN_ID_PLACEHOLDER
            )

            if info_val_r1 != info_val_r2:
                annot_comp = AnnotComp(
                    variant_key,
                    shared_annot_key,
                    variants_r1[variant_key],
                    info_val_r1,
                    info_val_r2,
                )
                diffs_per_annot_key[shared_annot_key].append(annot_comp)

        nbr_checked += 1
        if nbr_checked >= max_considered:
            break
    return (diffs_per_annot_key, r1_only_annots, r2_only_annots)


def get_annot_value_diff_summary(
    diffs_per_annot: Dict[str, List[AnnotComp]]
) -> List[str]:

    header = ["key", "number", "pos", "ref/alt", "first example"]
    output_rows = [header]
    for info_key, annot_value_diffs in diffs_per_annot.items():
        first_differing_variant = annot_value_diffs[0]
        r1_val = first_differing_variant.r1_annot
        r2_val = first_differing_variant.r2_annot
        var = first_differing_variant.variant
        variant_pos = f"{var.chr}:{var.pos}"
        variant_ref_alt = f"{var.get_trunc_ref()}:{var.get_trunc_alt()}"
        example_r1 = truncate_string(r1_val, MAX_STR_LEN)
        example_r2 = truncate_string(r2_val, MAX_STR_LEN)
        row = [
            info_key,
            str(len(annot_value_diffs)),
            variant_pos,
            variant_ref_alt,
            f"{example_r1} / {example_r2}",
        ]
        output_rows.append(row)

    pretty_rows = prettify_rows(output_rows, padding=2)
    return pretty_rows
