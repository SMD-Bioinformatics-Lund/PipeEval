from logging import Logger
from pathlib import Path
import re
from typing import Dict, Generic, List, Optional, Set, Tuple, TypeVar, Union

from .classes import PathObj, ScoredVariant

T = TypeVar("T")


def get_files_ending_with(pattern: str, paths: List[PathObj]) -> List[PathObj]:
    re_pattern = re.compile(pattern)
    matching = [path for path in paths if re.search(re_pattern, str(path)) is not None]
    return matching


def get_single_file_ending_with(
    patterns: List[str], paths: List[PathObj]
) -> Union[PathObj, None]:
    for pattern in patterns:
        matching = get_files_ending_with(pattern, paths)
        if len(matching) > 1:
            matches = [str(match) for match in matching]
            raise ValueError(
                f"Only one matching file allowed, found: {','.join(matches)}"
            )
        elif len(matching) == 1:
            return matching[0]
    return None


def any_is_parent(path: Path, names: List[str]) -> bool:
    """
    Among all parent dirs, does any match 'names'?
    Useful to filter files in ignored folders
    """
    for parent in path.parents:
        if parent.name in names:
            return True
    return False


class Comparison(Generic[T]):

    # After Python 3.7 a @dataclass can be used instead
    def __init__(self, r1: Set[T], r2: Set[T], shared: Set[T]):
        self.r1 = r1
        self.r2 = r2
        self.shared = shared


def do_comparison(set_1: Set[T], set_2: Set[T]) -> Comparison[T]:
    """Can compare both str and Path objects, thus the generics"""
    common = set_1 & set_2
    s1_only = set_1 - set_2
    s2_only = set_2 - set_1

    return Comparison(s1_only, s2_only, common)


def parse_vcf(vcf: PathObj, is_sv: bool) -> Dict[str, ScoredVariant]:

    sub_score_name_pattern = re.compile('ID=RankResult,.*Description="(.*)">')

    rank_sub_score_names = None

    variants: Dict[str, ScoredVariant] = {}
    with vcf.get_filehandle() as in_fh:
        for line in in_fh:
            line = line.rstrip()
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

            info_fields = [field.split("=") for field in info.split(";")]
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
            sv_length = (
                int(info_dict["SVLEN"]) if info_dict.get("SVLEN") is not None else None
            )

            sub_scores_dict: Dict[str, int] = {}
            if rank_sub_scores is not None:
                if rank_sub_score_names is None:
                    raise ValueError("Found rank sub scores, but not header")
                assert len(rank_sub_score_names) == len(
                    rank_sub_scores
                ), f"Length of sub score names and values should match, found {rank_sub_score_names} and {rank_sub_scores} in line: {line}"
                sub_scores_dict = dict(zip(rank_sub_score_names, rank_sub_scores))
            variant = ScoredVariant(
                chr, pos, ref, alt, rank_score, sub_scores_dict, is_sv, sv_length
            )
            key = variant.get_simple_key()
            variants[key] = variant
    return variants


def count_variants(vcf: PathObj) -> int:

    nbr_entries = 0
    with vcf.get_filehandle() as in_fh:
        for line in in_fh:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            nbr_entries += 1

    return nbr_entries


def get_files_in_dir(
    dir: Path,
    run_id: str,
    run_id_placeholder: str,
    base_dir: Path,
) -> List[PathObj]:
    processed_files_in_dir = [
        PathObj(path, run_id, run_id_placeholder, base_dir)
        for path in dir.rglob("*")
        if path.is_file()
    ]
    return processed_files_in_dir


def verify_pair_exists(
    label: str,
    file1: Optional[Union[Path, PathObj]],
    file2: Optional[Union[Path, PathObj]],
):

    r1_exists = file1 and file1.exists()
    r2_exists = file2 and file2.exists()

    if not r1_exists and not r2_exists:
        raise ValueError(f"Both {label} must exist. Neither currently exists.")
    elif not r1_exists:
        raise ValueError(f"Both {label} must exist. {file1} is missing.")
    elif not r2_exists:
        raise ValueError(f"Both {label} must exist. {file2} is missing.")


def get_pair_match(
    logger: Logger,
    error_label: str,
    valid_patterns: List[str],
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    verbose: bool,
) -> Tuple[PathObj, PathObj]:
    r1_matching = get_single_file_ending_with(valid_patterns, r1_paths)
    r2_matching = get_single_file_ending_with(valid_patterns, r2_paths)
    if verbose:
        logger.debug(f"Looking for pattern {valid_patterns}, found ${r1_paths} in r1")
        logger.debug(f"Looking for pattern {valid_patterns}, found ${r2_paths} in r2")

    verify_pair_exists(error_label, r1_matching, r2_matching)
    if r1_matching is None or r2_matching is None:
        raise ValueError(
            "Missing files (should have been captured by verification call?)"
        )
    return (r1_matching, r2_matching)
