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
        raise ValueError(
            f"Both {label} must exist. Neither currently exists. Is the correct run_id detected/assigned?"
        )
    elif not r1_exists:
        raise ValueError(
            f"Both {label} must exist. {file1} is missing. Is the correct run_id detected/assigned?"
        )
    elif not r2_exists:
        raise ValueError(
            f"Both {label} must exist. {file2} is missing. Is the correct run_id detected/assigned?"
        )


def get_pair_match(
    logger: Logger,
    error_label: str,
    valid_patterns: List[str],
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    r1_base_dir: Path,
    r2_base_dir: Path,
    verbose: bool,
) -> Tuple[PathObj, PathObj]:
    r1_matching = get_single_file_ending_with(valid_patterns, r1_paths)
    r2_matching = get_single_file_ending_with(valid_patterns, r2_paths)
    if verbose:
        if r1_matching is not None:
            logger.info(
                f"Looking for pattern(s) {valid_patterns}, found {r1_matching.real_path} in r1"
            )
        else:
            logger.info(
                f"Looking for pattern(s) {valid_patterns}, did not match any file in {r1_base_dir}"
            )

        if r2_matching is not None:
            logger.info(
                f"Looking for pattern(s) {valid_patterns}, found {r2_matching.real_path} in r2"
            )
        else:
            logger.info(
                f"Looking for pattern(s) {valid_patterns}, did not match any file in {r2_base_dir}"
            )

    verify_pair_exists(error_label, r1_matching, r2_matching)
    if r1_matching is None or r2_matching is None:
        raise ValueError(
            "Missing files (should have been captured by verification call?)"
        )
    return (r1_matching, r2_matching)


def detect_run_id(logger: Logger, base_dir_name: str, verbose: bool) -> str:
    datestamp_start_match = re.match(r"\d{6}-\d{4}_(.*)", base_dir_name)
    if datestamp_start_match:
        non_date_part = datestamp_start_match.group(1)
        if verbose:
            logger.info(
                f"Datestamp detected, run ID assigned as remainder of base folder name"
            )
            logger.info(f"Full name: {base_dir_name}")
            logger.info(f"Detected ID: {non_date_part}")
        return non_date_part
    else:
        logger.info(f"Datestamp not detected, full folder name used as run ID")
        dir_name = str(base_dir_name)
        return dir_name


def parse_var_key_for_sort(entry: str) -> Tuple[int, int]:
    chrom, pos = entry.split("_")[0:2]
    # If prefixed with chr, remove it
    if chrom.startswith("chr"):
        chrom = chrom.replace("chr", "")
    chrom_map = {"X": 24, "Y": 25, "M": 26, "MT": 26}
    if chrom in chrom_map:
        chrom_numeric = chrom_map[chrom]
    else:
        try:
            chrom_numeric = int(chrom)
        except ValueError:
            raise ValueError(f"Unexpected chromosome format: {chrom}")
    return chrom_numeric, int(pos)
