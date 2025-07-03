from logging import Logger
from pathlib import Path
import re
from typing import List, Optional

from commands.eval.classes.pathobj import PathObj
from shared.constants import RUN_ID_PLACEHOLDER


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


class RunObject:
    def __init__(
        self,
        run_id1: str,
        run_id2: str,
        results1_dir: Path,
        results2_dir: Path,
    ):
        self.r1_results: Path = results1_dir
        self.r2_results: Path = results2_dir

        self.r1_id: str = run_id1
        self.r2_id: str = run_id2


def get_run_object(
    logger: Logger, id1: Optional[str], id2: Optional[str], results1: Path, results2: Path, verbose: bool
) -> RunObject:
    if id1 is None:
        id1 = detect_run_id(logger, results1.name, verbose)
        logger.info(f"# --run_id1 not set, assigned: {id1}")

    if id2 is None:
        id2 = detect_run_id(logger, results2.name, verbose)
        logger.info(f"# --run_id1 not set, assigned: {id2}")

    run_object = RunObject(
        id1,
        id2,
        results1,
        results2,
    )

    return run_object
