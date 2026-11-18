from collections import defaultdict
from itertools import islice
from logging import Logger
from typing import Dict, List, Optional, Set, Tuple

from shared.compare import do_comparison
from shared.constants import MAX_STR_LEN, RUN_ID_PLACEHOLDER
from shared.util import prettify_rows, truncate_string
from shared.vcf.vcf import ScoredVariant


class AnnotComp:
    def __init__(
        self,
        variant: ScoredVariant,
        r1_annot: str,
        r2_annot: str,
    ):
        self.variant = variant
        self.r1_annot = r1_annot
        self.r2_annot = r2_annot
        self.count = 1


def compare_variant_annotation(
    logger: Logger,
    run_ids: Tuple[str, str],
    shared_variant_keys: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    max_considered: Optional[int],
):

    total = len(shared_variant_keys)
    checked = total if max_considered is None else min(max_considered, total)
    if checked == 0:
        logger.info("# No shared variants checked")
        return

    (diffs_per_annot_key, r1_only_annots, r2_only_annots) = calculate_annotation_diffs(
        shared_variant_keys, variants_r1, variants_r2, max_considered, run_ids
    )

    logger.info(f"# Checked {checked} of {total} shared variants")

    if len(r1_only_annots) == 0 and len(r2_only_annots) == 0:
        logger.info(
            f"# No annotation keys found uniquely in one VCF among the {checked} variants checked"
        )
    else:
        if len(r1_only_annots) > 0:
            logger.info("")
            logger.info(
                f"# Annotation keys only found in {run_ids[0]} among the {checked} variants checked"
            )
            for variant_key in sorted(r1_only_annots):
                logger.info(f"{variant_key}: {r1_only_annots[variant_key]}")
        else:
            logger.info(f"No annotation keys found only in {run_ids[0]}")
        if len(r2_only_annots) > 0:
            logger.info("")
            logger.info(
                f"# Annotation keys only found in {run_ids[1]} among the {checked} variants checked"
            )
            for variant_key in sorted(r2_only_annots):
                logger.info(f"{variant_key}: {r2_only_annots[variant_key]}")
        else:
            logger.info(f"No annotation keys found only in {run_ids[1]}")

    if len(diffs_per_annot_key) == 0:
        logger.info(
            f"# All shared annotation values agreed across the {checked} variants checked"
        )
    else:
        logger.info("")
        logger.info(
            f"# Found {len(diffs_per_annot_key)} shared keys with differing annotation values among the {checked} variants checked"
        )
        logger.info("# Showing number differing and first variant for each annotation")
        annot_value_diff_summary_rows = get_annot_value_diff_summary(
            diffs_per_annot_key
        )
        for row in annot_value_diff_summary_rows:
            logger.info(row)


def calculate_annotation_diffs(
    shared_variant_keys: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    max_considered: Optional[int],
    run_ids: Tuple[str, str],
) -> Tuple[Dict[str, AnnotComp], Dict[str, int], Dict[str, int]]:
    r1_only_annots: Dict[str, int] = defaultdict(int)
    r2_only_annots: Dict[str, int] = defaultdict(int)

    diffs_per_annot_key: Dict[str, AnnotComp] = {}
    for variant_key in islice(sorted(shared_variant_keys), max_considered):
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
                run_ids[0], RUN_ID_PLACEHOLDER
            )
            info_val_r2 = var_r2.info_dict[shared_annot_key].replace(
                run_ids[1], RUN_ID_PLACEHOLDER
            )

            if info_val_r1 != info_val_r2:
                first_diff = diffs_per_annot_key.get(shared_annot_key)
                if first_diff is None:
                    diffs_per_annot_key[shared_annot_key] = AnnotComp(
                        var_r1, info_val_r1, info_val_r2
                    )
                else:
                    first_diff.count += 1
    return (diffs_per_annot_key, r1_only_annots, r2_only_annots)


def get_annot_value_diff_summary(
    diffs_per_annot: Dict[str, AnnotComp],
) -> List[str]:

    header = ["key", "number", "pos", "ref/alt", "first example"]
    output_rows = [header]
    for info_key, first_differing_variant in diffs_per_annot.items():
        r1_val = first_differing_variant.r1_annot
        r2_val = first_differing_variant.r2_annot
        var = first_differing_variant.variant
        variant_pos = f"{var.chr}:{var.pos}"
        variant_ref_alt = f"{var.get_trunc_ref()}:{var.get_trunc_alt()}"
        example_r1 = truncate_string(r1_val, MAX_STR_LEN)
        example_r2 = truncate_string(r2_val, MAX_STR_LEN)
        row = [
            info_key,
            str(first_differing_variant.count),
            variant_pos,
            variant_ref_alt,
            f"{example_r1} / {example_r2}",
        ]
        output_rows.append(row)

    pretty_rows = prettify_rows(output_rows, padding=2)
    return pretty_rows
