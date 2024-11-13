from pathlib import Path
import subprocess
from typing import Tuple


def checkout_repo(repo: Path, checkout_string: str) -> Tuple[int, str]:

    results = subprocess.run(
        ["git", "checkout", checkout_string],
        cwd=str(repo),
        # text=True is supported from Python 3.7
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return (results.returncode, results.stderr)


def check_if_on_branchhead(repo: Path) -> bool:
    results = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(repo),
        # text=True is supported from Python 3.7
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return results.stdout.strip() != "HEAD"


def pull_branch(repo: Path, branch: str) -> None:
    subprocess.run(
        ["git", "pull", "origin", branch],
        cwd=str(repo),
        # text=True is supported from Python 3.7
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def get_git_commit_hash_and_log(repo: Path) -> Tuple[str, str]:
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(repo),
        check=True,
        # text=True is supported from Python 3.7
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    last_log = result.stdout.splitlines()[0]
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


def check_valid_checkout(repo: Path, checkout_obj: str) -> Tuple[int, str]:
    results = subprocess.run(
        ["git", "rev-parse", "--verify", checkout_obj],
        cwd=str(repo),
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if results.returncode != 0:
        return (
            results.returncode,
            f"The string {checkout_obj} was not found in the repository",
        )
    return (0, "")
