from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional, Set
import re

from shared.score_utils import get_table
from shared.annotation_utils import compare_variant_annotation
from shared.compare import Comparison, do_comparison, parse_var_key_for_sort
from shared.file import get_filehandle
from shared.shared_utils import prettify_rows

TRUNC_LENGTH = 30


class ScoredVariant:
    """Represents position, call and scores of a variant"""

    def __init__(
        self,
        chr: str,
        pos: int,
        ref: str,
        alt: str,
        rank_score: Optional[int],
        sub_scores: Dict[str, int],
        is_sv: bool,
        sv_length: Optional[int],
        info_dict: Dict[str, str],
        line_number: int,
    ):
        self.chr = chr
        self.pos = pos
        self.ref = ref
        self.alt = alt
        self.rank_score = rank_score
        self.sub_scores = sub_scores
        self.is_sv = is_sv
        self.sv_length = sv_length
        self.info_dict = info_dict
        self.line_number = line_number

    def get_trunc_ref(self) -> str:
        trunc_ref = (
            self.ref[0:TRUNC_LENGTH] + "..."
            if len(self.ref) > TRUNC_LENGTH
            else self.ref
        )
        return trunc_ref

    def get_trunc_alt(self) -> str:
        trunc_alt = (
            self.alt[0:TRUNC_LENGTH] + "..."
            if len(self.alt) > TRUNC_LENGTH
            else self.alt
        )
        return trunc_alt

    def __str__(self) -> str:
        trunc_ref = self.get_trunc_ref()
        trunc_alt = self.get_trunc_alt()
        return (
            f"{self.chr}:{self.pos} {trunc_ref}/{trunc_alt} (Score: {self.rank_score})"
        )

    def get_simple_key(self) -> str:
        if not self.is_sv:
            return f"{self.chr}_{self.pos}_{self.ref}_{self.alt}"
        else:
            return f"{self.chr}_{self.pos}_{self.sv_length}_{self.ref}_{self.alt}"

    def get_rank_score(self) -> int:
        if self.rank_score is None:
            raise ValueError(
                f"Rank score not present, check before using 'get_rank_score'. Variant: {str(self)}"
            )
        return self.rank_score

    def get_rank_score_str(self) -> str:
        return str(self.rank_score) if self.rank_score is not None else ""

    def get_basic_info(self) -> str:
        return f"{self.chr}:{self.pos} {self.get_trunc_ref()}/{self.get_trunc_alt()}"

    def get_row(self, show_line_numbers: bool) -> List[str]:
        row = [self.chr, str(self.pos), self.get_trunc_ref(), self.get_trunc_alt()]
        if show_line_numbers:
            row.append(str(self.line_number))
        if self.sv_length is not None:
            row.append(str(self.sv_length))
        if self.rank_score is not None:
            row.append(str(self.rank_score))
        return row

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScoredVariant):
            return False
        is_same = (
            self.chr == other.chr
            and self.pos == other.pos
            and self.ref == other.ref
            and self.alt == other.alt
            and self.sv_length == other.sv_length
        )
        return is_same


class DiffScoredVariant:
    """Container for comparison of differently scored variants in the same location"""

    def __init__(self, r1_variant: ScoredVariant, r2_variant: ScoredVariant):

        self.r1 = r1_variant
        self.r2 = r2_variant

    def any_above_thres(self, score_threshold: int) -> bool:
        r1_above_thres = (
            self.r1.rank_score is not None and self.r1.rank_score >= score_threshold
        )
        r2_above_thres = (
            self.r2.rank_score is not None and self.r2.rank_score >= score_threshold
        )
        any_above_thres = r1_above_thres or r2_above_thres
        return any_above_thres



def parse_vcf(vcf: Path, is_sv: bool) -> Dict[str, ScoredVariant]:

    sub_score_name_pattern = re.compile('ID=RankResult,.*Description="(.*)">')

    rank_sub_score_names = None

    variants: Dict[str, ScoredVariant] = {}
    with get_filehandle(vcf) as in_fh:
        line_nbr = 0
        for line in in_fh:
            line = line.rstrip()
            line_nbr += 1
            if line.startswith("#"):

                if rank_sub_score_names is None and line.startswith(
                    "##INFO=<ID=RankResult,"
                ):
                    match = sub_score_name_pattern.search(line)
                    if match is None:
                        raise ValueError(
                            f"Rankscore categories expected but not found in: ${line}"
                        )
                    match_string = match.group(1)
                    rank_sub_score_names = match_string.split("|")

                continue
            fields = line.split("\t")
            chr = fields[0]
            pos = int(fields[1])
            ref = fields[3]
            alt = fields[4]
            info = fields[7]

            # Some INFO fields are not in the expected format key=value
            info_fields = [
                field.split("=") if field.find("=") != -1 else [field, "<MISSING>"]
                for field in info.split(";")
            ]
            info_dict = dict(info_fields)

            rank_score = (
                int(info_dict["RankScore"].split(":")[1].replace(".0", ""))
                if info_dict.get("RankScore") is not None
                else None
            )
            rank_sub_scores = (
                [int(sub_sc) for sub_sc in info_dict["RankResult"].split("|")]
                if info_dict.get("RankResult") is not None
                else None
            )
            if info_dict.get("END") is not None:
                sv_end = int(info_dict["END"])
                sv_length = sv_end - pos + 1
            else:
                sv_length = None

            sub_scores_dict: Dict[str, int] = {}
            if rank_sub_scores is not None:
                if rank_sub_score_names is None:
                    raise ValueError("Found rank sub scores, but not header")
                assert len(rank_sub_score_names) == len(
                    rank_sub_scores
                ), f"Length of sub score names and values should match, found {rank_sub_score_names} and {rank_sub_scores} in line: {line}"
                sub_scores_dict = dict(zip(rank_sub_score_names, rank_sub_scores))
            variant = ScoredVariant(
                chr,
                pos,
                ref,
                alt,
                rank_score,
                sub_scores_dict,
                is_sv,
                sv_length,
                info_dict,
                line_nbr,
            )
            key = variant.get_simple_key()
            variants[key] = variant
    return variants

def count_variants(vcf: Path) -> int:

    nbr_entries = 0
    with get_filehandle(vcf) as in_fh:
        for line in in_fh:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            nbr_entries += 1

    return nbr_entries


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
                f"First {min(len(r2_only), max_display)} only found in {label_r2}"
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
        f"Number differently scored total: {len(diff_scored_variants)}",
    )
    logger.info(
        f"Number differently scored above {score_threshold}: {len(diff_variants_above_thres)}",
    )
    logger.info(
        f"Total number shared variants: {len(shared_variant_keys)} (r1: {len(variants_r1)}, r2: {len(variants_r2)})",
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
        logger.info(f"Only printing the {max_count} first")
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
    variants_r1 = parse_vcf(r1_scored_vcf, is_sv)
    variants_r2 = parse_vcf(r2_scored_vcf, is_sv)
    comparison_results = do_comparison(
        set(variants_r1.keys()),
        set(variants_r2.keys()),
    )
    compare_variant_presence(
        logger,
        run_id1,
        run_id2,
        variants_r1,
        variants_r2,
        comparison_results,
        max_display,
        out_path_presence,
        show_line_numbers,
    )
    shared_variants = comparison_results.shared
    if do_annot_check:
        logger.info("")
        logger.info("--- Comparing annotations ---")
        compare_variant_annotation(
            logger,
            run_id1,
            run_id2,
            shared_variants,
            variants_r1,
            variants_r2,
            max_checked_annots,
        )
    if do_score_check:
        logger.info("")
        logger.info("--- Comparing score ---")
        compare_variant_score(
            logger,
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
            show_line_numbers,
        )