from __future__ import annotations

import re
from logging import Logger
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from shared.constants import IS_VCF_PATTERN, RUN_ID_PLACEHOLDER

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
    ro: RunObject,
    # r1_paths: List[PathObj],
    # r2_paths: List[PathObj],
    # r1_results: Path,
    # r2_results: Path,
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


def detect_run_id(logger: Logger, base_dir_name: str, verbose: bool) -> str:
    datestamp_start_match = re.match(r"\d{6}-\d{4}_(.*)", base_dir_name)
    if datestamp_start_match:
        non_date_part = datestamp_start_match.group(1)
        if verbose:
            logger.info("Datestamp detected, run ID assigned as remainder of base folder name")
            logger.info(f"Full name: {base_dir_name}")
            logger.info(f"Detected ID: {non_date_part}")
        return non_date_part
    else:
        logger.info("Datestamp not detected, full folder name used as run ID")
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


class RunObject:
    def __init__(
        self,
        run_id1: Optional[str],
        run_id2: Optional[str],
        results1_dir: Path,
        results2_dir: Path,
    ):
        self._run_id1 = run_id1
        self._run_id2 = run_id2
        self.r1_results = results1_dir
        self.r2_results = results2_dir
        self._r1_paths = None
        self._r2_paths = None
        self._r1_vcfs = None
        self._r2_vcfs = None

    @property
    def r1_id(self) -> str:
        if self._run_id1:
            return self._run_id1
        raise ValueError("Trying to access run id before init")

    @property
    def r2_id(self) -> str:
        if self._run_id1:
            return self._run_id1
        raise ValueError("Trying to access run id before init")

    @property
    def r1_paths(self) -> List[PathObj]:
        if self._r1_paths:
            return self._r1_paths
        raise ValueError("Trying to access run id before init")

    @property
    def r2_paths(self) -> List[PathObj]:
        if self._r2_paths:
            return self._r2_paths
        raise ValueError("Trying to access run id before init")

    @property
    def r1_vcfs(self) -> List[Path]:
        if self._r1_vcfs:
            return self._r1_vcfs
        raise ValueError("Trying to access run id before init")

    @property
    def r2_vcfs(self) -> List[Path]:
        if self._r2_vcfs:
            return self._r2_vcfs
        raise ValueError("Trying to access run id before init")



    def init(self, logger: Logger, verbose: bool):

        if self._run_id1 is None:
            self._run_id1 = detect_run_id(logger, self.r1_results.name, verbose)
            logger.info(f"# --run_id1 not set, assigned: {self.r1_id}")

        if self._run_id2 is None:
            self._run_id2 = detect_run_id(logger, self.r2_results.name, verbose)
            logger.info(f"# --run_id2 not set, assigned: {self._run_id2}")

        self._r1_paths = get_files_in_dir(
            self.r1_results, self.r1_id, RUN_ID_PLACEHOLDER, self.r1_results
        )
        self._r2_paths = get_files_in_dir(
            self.r2_results, self.r2_id, RUN_ID_PLACEHOLDER, self.r2_results
        )

        self._r1_vcfs = [p.real_path for p in get_files_ending_with(IS_VCF_PATTERN, self.r1_paths)]
        self._r2_vcfs = [p.real_path for p in get_files_ending_with(IS_VCF_PATTERN, self.r2_paths)]
        logger.info(f"Looking for paths: {self.r1_paths} found: {self._r1_vcfs}")
        logger.info(f"Looking for paths: {self.r2_paths} found: {self._r2_vcfs}")



class RunSettings:
    def __init__(
        self,
        score_threshold: int,
        max_display: int,
        verbose: bool,
        max_checked_annots: int,
        show_line_numbers: bool,
        extra_annot_keys: List[str],
        output_all_variants: bool,
    ):
        self.score_threshold = score_threshold
        self.max_display = max_display
        self.verbose = verbose
        self.max_checked_annots = max_checked_annots
        self.show_line_numbers = show_line_numbers
        self.annotation_info_keys = extra_annot_keys
        self.output_all_variants = output_all_variants
