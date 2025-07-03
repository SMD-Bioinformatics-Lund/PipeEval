import re
from logging import Logger
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .classes import PathObj


def get_files_ending_with(pattern: str, paths: List[PathObj]) -> List[PathObj]:
    re_pattern = re.compile(pattern)
    matching = [path for path in paths if re.search(re_pattern, str(path)) is not None]
    return matching


def get_single_file_ending_with(patterns: List[str], paths: List[PathObj]) -> Union[PathObj, None]:
    for pattern in patterns:
        matching = get_files_ending_with(pattern, paths)
        if len(matching) > 1:
            matches = [str(match) for match in matching]
            raise ValueError(f"Only one matching file allowed, found: {','.join(matches)}")
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
) -> Optional[Tuple[Path, Path]]:
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

    if not r1_matching or not r2_matching:
        return None

    return (r1_matching.real_path, r2_matching.real_path)


def detect_run_id(logger: Logger, base_dir_name: str, verbose: bool) -> str:
    datestamp_start_match = re.match(r"\d{6}-\d{4}_(.*)", base_dir_name)
    if datestamp_start_match:
        non_date_part = datestamp_start_match.group(1)
        if verbose:
            logger.info(f"Datestamp detected, run ID assigned as remainder of base folder name")
            logger.info(f"Full name: {base_dir_name}")
            logger.info(f"Detected ID: {non_date_part}")
        return non_date_part
    else:
        logger.info(f"Datestamp not detected, full folder name used as run ID")
        dir_name = str(base_dir_name)
        return dir_name


class ScorePaths:
    def __init__(
        self, label: str, outdir: Optional[Path], score_threshold: float, all_variants: bool
    ):
        self.presence = outdir / f"scored_{label}_presence.txt" if outdir else None
        self.score_thres = (
            outdir / f"scored_{label}_score_thres_{score_threshold}.txt" if outdir else None
        )
        self.all_diffing = outdir / f"scored_{label}_score_all.txt" if outdir else None
        self.all = outdir / f"scored_{label}_score_full.txt" if outdir and all_variants else None
