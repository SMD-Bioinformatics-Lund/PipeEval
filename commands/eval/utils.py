from __future__ import annotations

import re
from logging import Logger
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from .classes.run_object import PathObj, RunObject


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
    ro: RunObject,
    verbose: bool,
) -> Optional[Tuple[Path, Path]]:
    r1_matching = get_single_file_ending_with(valid_patterns, ro.r1_paths)
    r2_matching = get_single_file_ending_with(valid_patterns, ro.r2_paths)
    if verbose:
        if r1_matching is not None:
            logger.info(
                f"Looking for pattern(s) {valid_patterns}, found {r1_matching.real_path} in r1"
            )
        else:
            logger.info(
                f"Looking for pattern(s) {valid_patterns}, did not match any file in {ro.r1_results}"
            )

        if r2_matching is not None:
            logger.info(
                f"Looking for pattern(s) {valid_patterns}, found {r2_matching.real_path} in r2"
            )
        else:
            logger.info(
                f"Looking for pattern(s) {valid_patterns}, did not match any file in {ro.r2_results}"
            )

    verify_pair_exists(error_label, r1_matching, r2_matching)

    if not r1_matching or not r2_matching:
        return None

    return (r1_matching.real_path, r2_matching.real_path)


def get_ignored(
    result_paths: Set[Path], ignore_files: List[str]
) -> Tuple[dict[str, int], list[Path]]:

    nbr_ignored_per_pattern: dict[str, int] = {}

    non_ignored: List[Path] = []
    for path in sorted(result_paths):
        if any_is_parent(path, ignore_files):
            nbr_ignored_per_pattern[str(path.parent)] += 1
        else:
            non_ignored.append(path)

    return (nbr_ignored_per_pattern, non_ignored)
