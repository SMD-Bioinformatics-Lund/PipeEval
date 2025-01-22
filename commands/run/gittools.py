from logging import Logger
from pathlib import Path
import subprocess
from typing import List, Tuple


def run_command(command: List[str], repo: Path) -> subprocess.CompletedProcess[str]:
    results = subprocess.run(
        command,
        cwd=str(repo),
        # text=True is supported from Python 3.7
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return results


def fetch_repo(logger: Logger, repo: Path, verbose: bool) -> Tuple[int, str]:
    command = ["git", "fetch"]
    if verbose:
        logger.info(f"Executing: {command} in {repo}")
    results = run_command(command, repo)
    return (results.returncode, results.stderr)


def checkout_repo(
    logger: Logger, repo: Path, checkout_string: str, verbose: bool
) -> Tuple[int, str]:

    command = ["git", "checkout", checkout_string]
    if verbose:
        logger.info(f"Executing: {command} in {repo}")
    results = run_command(command, repo)
    return (results.returncode, results.stderr)


def check_if_on_branchhead(logger: Logger, repo: Path, verbose: bool) -> bool:
    command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    if verbose:
        logger.info(f"Executing: {command} in {repo}")
    results = run_command(command, repo)
    return results.stdout.strip() != "HEAD"


def pull_branch(logger: Logger, repo: Path, branch: str, verbose: bool) -> None:
    command = ["git", "pull", "origin", branch]
    if verbose:
        logger.info(f"Executing: {command} in {repo}")
    results = run_command(command, repo)
    logger.info(results.stdout.rstrip())


def get_git_commit_hash_and_log(
    logger: Logger, repo: Path, verbose: bool
) -> Tuple[str, str]:
    command = ["git", "log", "--oneline"]
    if verbose:
        logger.info(f"Executing: {command} in {repo}")
    results = run_command(command, repo)
    last_log = results.stdout.splitlines()[0]
    commit_hash = last_log.split(" ")[0]
    return (commit_hash, last_log)


def check_valid_repo(repo: Path) -> Tuple[int, str]:
    if not repo.exists():
        return (1, f'The folder "{repo}" does not exist')

    if not repo.is_dir():
        return (1, f'"{repo}" is not a folder')

    if not (repo / ".git").is_dir():
        return (1, f'"{repo}" has no .git subdir. It should be a Git repository')

    return (0, "")


def check_valid_checkout(
    logger: Logger, repo: Path, checkout_obj: str, verbose: bool
) -> Tuple[int, str]:
    command = ["git", "rev-parse", "--verify", checkout_obj]
    if verbose:
        logger.info(f"Executing: {command} in {repo}")
    results = run_command(command, repo)
    if results.returncode != 0:
        return (
            results.returncode,
            f"The string {checkout_obj} was not found in the repository",
        )
    return (0, "")
