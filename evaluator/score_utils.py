from typing import Set, List, Dict

from .classes import DiffScoredVariant, ScoredVariant


def get_comparison_row(
    var1: ScoredVariant,
    var2: ScoredVariant,
    show_sub_scores: bool,
    show_sub_score_summary: bool,
) -> List[str]:

    if var1 != var2:
        raise ValueError(
            f"Must compare the same variant. This: {str(var1)} Other: {str(var2)}"
        )

    fields = [
        var1.chr,
        str(var1.pos),
        f"{var1.ref}/{var1.alt}",
        var1.get_rank_score_str(),
        var2.get_rank_score_str(),
    ]

    if show_sub_score_summary:
        sub_score_sum_str = sub_score_summary(var1.sub_scores, var2.sub_scores)
        fields.append(sub_score_sum_str)

    if show_sub_scores:
        for sub_score_val in var1.sub_scores.values():
            fields.append(str(sub_score_val))
        for sub_score_val in var2.sub_scores.values():
            fields.append(str(sub_score_val))
    return fields


def get_table(
    variants: List[DiffScoredVariant],
    shared_variant_keys: Set[str],
    variants_r1: Dict[str, ScoredVariant],
    variants_r2: Dict[str, ScoredVariant],
    with_subscore_summary: bool,
) -> List[List[str]]:

    first_shared_key = list(shared_variant_keys)[0]
    header_fields = ["chr", "pos", "var", "score_r1", "score_r2"]

    if with_subscore_summary:
        header_fields.append("score_diff_summary")

    for sub_score in variants_r1[first_shared_key].sub_scores:
        header_fields.append(f"r1_{sub_score}")
    for sub_score in variants_r2[first_shared_key].sub_scores:
        header_fields.append(f"r2_{sub_score}")
    rows = [header_fields]

    for variant in variants:
        comparison_fields = get_comparison_row(
            variant.r1, variant.r2, show_sub_scores=True, show_sub_score_summary=True
        )
        rows.append(comparison_fields)

    return rows


def sub_score_summary(subscores1: Dict[str, int], subscores2: Dict[str, int]) -> str:

    assert (
        subscores1.keys() == subscores2.keys()
    ), f"Subscore keys differing. Found: {subscores1.keys()} and {subscores2.keys()}"

    assert len(subscores1) == len(
        subscores2
    ), f"Number of categories must be same as subscores. Found: {len(subscores1)} and {len(subscores2)}"

    sub_score_diff_info = []
    for category in subscores1:
        sc1 = subscores1[category]
        sc2 = subscores2[category]
        if sc1 != sc2:
            diff_str = f"{category}:{sc1}/{sc2}"
            sub_score_diff_info.append(diff_str)
    if len(sub_score_diff_info) > 0:
        return ",".join(sub_score_diff_info)
    else:
        return "-"
