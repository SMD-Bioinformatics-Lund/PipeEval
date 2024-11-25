import gzip
from pathlib import Path
from typing import Dict, Optional, TextIO, List

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

    def get_row_fields(self) -> List[str]:
        row = [self.chr, self.pos, self.get_trunc_ref(), self.get_trunc_alt()]
        if self.sv_length is not None:
            row.append(str(self.sv_length))
        if self.rank_score is not None:
            row.append(str(self.rank_score))
        return row

    def __eq__(self, other) -> bool:
        return (
            self.chr == other.chr
            and self.pos == other.pos
            and self.ref == other.ref
            and self.alt == other.alt
            and self.sv_length == other.sv_length
        )


class PathObj:
    """
    Extended Path object to make comparison between results dir more convenient.

    1. Relative paths to the base dir
    2. Can replace the run ID with the string 'RUNID'
    3. Can detect whether a file is text or gzip
    """

    def __init__(
        self,
        path: Path,
        run_id: str,
        id_placeholder: str,
        base_dir: Path,
    ):
        self.real_name = path.name
        self.real_path = path

        self.shared_name = path.name.replace(run_id, id_placeholder)
        self.shared_path = path.with_name(self.shared_name)
        self.relative_path = self.shared_path.relative_to(base_dir)

        self.run_id = run_id
        self.id_placeholder = id_placeholder

        self.is_gzipped = path.suffix.endswith(".gz")

    def exists(self) -> bool:
        return self.real_path.exists()

    def check_valid_file(self) -> bool:
        try:
            if self.is_gzipped:
                with gzip.open(str(self.real_path), "rt") as fh:
                    fh.read(1)
            else:
                with open(str(self.real_path), "r") as fh:
                    fh.read(1)
        except:
            return False
        return True

    def get_filehandle(self) -> TextIO:
        if self.is_gzipped:
            in_fh = gzip.open(str(self.real_path), "rt")
        else:
            in_fh = open(str(self.real_path), "r")
        return in_fh

    def __str__(self) -> str:
        return str(self.relative_path)


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
