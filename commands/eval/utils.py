from configparser import SectionProxy
import re
from collections import defaultdict
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from commands.eval.classes.helpers import VCFPair
from commands.eval.eval_functions import check_same_files, diff_compare_files
from commands.eval.main import FILE_NAMES
from shared.compare import do_comparison
from shared.vcf.vcf import parse_scored_vcf

from .classes.run_object import PathObj, RunObject


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


class SampleMatch:
    def __init__(self, sample_id, path):
        self.sample_id = sample_id
        self.path = path


def get_pair_matches(
    valid_pattern: str,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
) -> List[Tuple[SampleMatch, SampleMatch]]:

    re_pattern = re.compile(valid_pattern)

    def get_match(path: PathObj) -> Optional[SampleMatch]:
        match = re.search(re_pattern, str(path.real_path))
        if match:
            sample_id = match.groups()[0]
            match_obj = SampleMatch(sample_id, path.real_path)
            return match_obj
        return None

    r1_matches = {}
    for path in r1_paths:
        match = get_match(path)
        if match:
            r1_matches[match.sample_id] = match

    r2_matches = {}
    for path in r2_paths:
        match = get_match(path)
        if match:
            r2_matches[match.sample_id] = match

    matches = []
    for r1_id in r1_matches:
        if r2_matches.get(r1_id):
            match_pair = (r1_matches[r1_id], r2_matches[r1_id])
            matches.append(match_pair)

    # r1_matches = get_files_ending_with(pattern, paths)

    return matches


def get_pair_match(
    logger: Logger,
    error_label: str,
    valid_patterns: List[str],
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
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

    try:
        verify_pair_exists(error_label, r1_matching, r2_matching)
    except ValueError as e:
        logger.warning(e)

    if not r1_matching or not r2_matching:
        return None

    return (r1_matching.real_path, r2_matching.real_path)


def get_ignored(
    result_paths: Set[Path], ignore_files: List[str]
) -> Tuple[Dict[str, int], List[Path]]:

    nbr_ignored_per_pattern: Dict[str, int] = defaultdict(int)

    non_ignored: List[Path] = []
    for path in sorted(result_paths):
        if any_is_parent(path, ignore_files):
            parent = str(path.parent)
            nbr_ignored_per_pattern[parent] += 1
        else:
            non_ignored.append(path)

    return (nbr_ignored_per_pattern, non_ignored)


def get_vcf_pair(
    logger: Logger,
    vcf_paths: List[str],
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    verbose: bool,
    vcf_type: str,
) -> Optional[VCFPair]:
    vcf_pair_paths = get_pair_match(
        logger,
        vcf_type,
        vcf_paths,
        ro,
        r1_paths,
        r2_paths,
        verbose,
    )

    if vcf_pair_paths is None:
        logger.warning(f"Skipping {vcf_type} comparisons due to missing files ({vcf_pair_paths})")
        return None

    vcf_pair = parse_vcf_pair(logger, ro.run_ids, vcf_pair_paths, vcf_type)

    return vcf_pair


def parse_vcf_pair(
    logger: Logger, run_ids: Tuple[str, str], vcf_paths: Tuple[Path, Path], vcf_type: str
) -> VCFPair:
    logger.info(f"# Parsing {vcf_type} VCFs ...")

    vcf_r1 = parse_scored_vcf(vcf_paths[0], False)
    logger.info(f"{run_ids[0]} number variants: {len(vcf_r1.variants)}")
    vcf_r2 = parse_scored_vcf(vcf_paths[1], False)
    logger.info(f"{run_ids[1]} number variants: {len(vcf_r2.variants)}")

    comp_res = do_comparison(
        set(vcf_r1.variants.keys()),
        set(vcf_r2.variants.keys()),
    )
    logger.info(f"In common: {len(comp_res.shared)}")
    logger.info(f"Only in {run_ids[0]}: {len(comp_res.r1)}")
    logger.info(f"Only in {run_ids[1]}: {len(comp_res.r2)}")

    vcf_pair = VCFPair(vcf_r1, vcf_r2, comp_res)
    return vcf_pair

def do_file_diff(
    logger: Logger,
    outdir: Optional[Path],
    pipe_conf: SectionProxy,
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
):
    out_path = outdir / "check_sample_files.txt" if outdir else None
    logger.info("")
    logger.info("### Comparing existing files ###")

    ignore_file_string = pipe_conf.get("ignore") or ""
    ignore_files = ignore_file_string.split(",")

    check_same_files(
        ro,
        r1_paths,
        r2_paths,
        ignore_files,
        out_path,
    )

def do_simple_diff(
    logger: Logger,
    ro: RunObject,
    r1_paths: List[PathObj],
    r2_paths: List[PathObj],
    pipe_conf: SectionProxy,
    analysis: str,
    outdir: Optional[Path],
    verbose: bool,
):
    logger.info("")
    logger.info(f"--- Comparing: {analysis} ---")
    matched_pair = get_pair_match(
        logger,
        analysis,
        pipe_conf[analysis].split(","),
        ro,
        r1_paths,
        r2_paths,
        verbose,
    )
    if not matched_pair:
        logger.warning(f"At least one file missing ({matched_pair})")
    else:
        out_path = outdir / FILE_NAMES[analysis] if outdir else None
        diff_compare_files(ro.r1_id, ro.r2_id, matched_pair[0], matched_pair[1], out_path)

