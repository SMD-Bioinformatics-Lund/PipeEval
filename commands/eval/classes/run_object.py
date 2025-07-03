from logging import Logger
from pathlib import Path
import re
from typing import List, Optional

from commands.eval.classes.pathobj import PathObj
from commands.eval.utils import get_files_in_dir
from shared.constants import RUN_ID_PLACEHOLDER


def detect_run_id(logger: Logger, base_dir_name: str, verbose: bool) -> str:
    datestamp_start_match = re.match(r"\d{6}-\d{4}_(.*)", base_dir_name)
    if datestamp_start_match:
        non_date_part = datestamp_start_match.group(1)
        if verbose:
            logger.info(
                "Datestamp detected, run ID assigned as remainder of base folder name"
            )
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
        run_id1: Optional[str],
        run_id2: Optional[str],
        results1_dir: Path,
        results2_dir: Path,
    ):
        self._run_id1 = run_id1
        self._run_id2 = run_id2
        self.r1_results = results1_dir
        self.r2_results = results2_dir
        self._r1_paths: Optional[List[PathObj]] = None
        self._r2_paths: Optional[List[PathObj]] = None
        self._r1_vcfs: Optional[List[Path]] = None
        self._r2_vcfs: Optional[List[Path]] = None

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
