from typing import Set, List, Dict

from .classes import DiffScoredVariant, ScoredVariant


def get_table(
    variants: List[DiffScoredVariant],
    shared_variant_keys: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
) -> List[List[str]]:

    first_shared_key = list(shared_variant_keys)[0]
    header_fields = ["chr", "pos", "var", "r1", "r2"]
    for sub_score in variants_r1[first_shared_key].sub_scores:
        header_fields.append(f"r1_{sub_score}")
    for sub_score in variants_r2[first_shared_key].sub_scores:
        header_fields.append(f"r2_{sub_score}")
    rows = [header_fields]

    for variant in variants:
        comparison_fields = variant.r1.get_comparison_row(
            variant.r2, show_sub_scores=True
        )
        rows.append(comparison_fields)

    return rows
