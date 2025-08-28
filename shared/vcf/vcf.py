import re
from pathlib import Path
from typing import Dict, List, Optional

from shared.file import get_filehandle
from shared.string import get_match_or_crash

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
        filters: str,
        line_number: int,
        sample_dict: Dict[str, str],
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
        self.filters = filters
        self.line_number = line_number
        self.sample_dict = sample_dict

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

    def get_row(
        self, show_line_numbers: bool, additional_annotations: List[str]
    ) -> List[str]:
        row = [self.chr, str(self.pos), self.get_trunc_ref(), self.get_trunc_alt()]
        if show_line_numbers:
            row.append(str(self.line_number))
        if self.sv_length is not None:
            row.append(str(self.sv_length))
        if self.rank_score is not None:
            row.append(str(self.rank_score))
        if len(additional_annotations):
            for annot_key in additional_annotations:
                annot_val = self.info_dict.get(annot_key)
                row.append(annot_val if annot_val is not None else "")
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


class ScoredVCF:
    def __init__(
        self,
        path: Path,
        is_sv: bool,
        info: Dict[str, str],
        variants: Dict[str, ScoredVariant],
    ):
        self.path = path
        self.is_sv = is_sv
        self.info = info
        self.variants = variants


def parse_scored_vcf(vcf: Path, is_sv: bool) -> ScoredVCF:

    sub_score_name_pattern = re.compile('ID=RankResult,.*Description="(.*)">')
    info_id_pattern = re.compile("ID=(.*),")

    rank_sub_score_names = None

    info_rows: Dict[str, str] = {}
    variants: Dict[str, ScoredVariant] = {}
    with get_filehandle(vcf) as in_fh:
        line_nbr = 0
        for line in in_fh:
            line = line.rstrip()
            line_nbr += 1
            if line.startswith("#"):

                if line.startswith("##INFO="):
                    info_id = get_match_or_crash(
                        info_id_pattern, line, f"Expected ID match in line: {line}"
                    )
                    info_rows[info_id] = line

                if rank_sub_score_names is None and line.startswith(
                    "##INFO=<ID=RankResult,"
                ):
                    sub_scores_names = get_match_or_crash(
                        sub_score_name_pattern,
                        line,
                        f"Rankscore categories expected but not found in: ${line}",
                    )

                    rank_sub_score_names = sub_scores_names.split("|")

                continue
            fields = line.split("\t")
            chr = fields[0]
            pos = int(fields[1])
            ref = fields[3]
            alt = fields[4]
            filters = fields[6]
            info = fields[7]
            fmt = fields[8] if len(fields) > 8 else None
            sample_field = fields[9] if len(fields) > 9 else None

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
            # Parse sample FORMAT values (first sample column if present)
            sample_dict: Dict[str, str] = {}
            if fmt and sample_field:
                fmt_keys = fmt.split(":")
                fmt_values = sample_field.split(":")
                # Map keys to values, missing values become empty strings
                for i, key in enumerate(fmt_keys):
                    sample_dict[key] = fmt_values[i] if i < len(fmt_values) else ""

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
                filters,
                line_nbr,
                sample_dict,
            )
            key = variant.get_simple_key()
            variants[key] = variant

    scored_vcf = ScoredVCF(vcf, is_sv, info_rows, variants)

    return scored_vcf


def count_variants(vcf: Path) -> int:

    nbr_entries = 0
    with get_filehandle(vcf) as in_fh:
        for line in in_fh:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            nbr_entries += 1

    return nbr_entries
