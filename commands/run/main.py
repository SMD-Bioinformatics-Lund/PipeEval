#!/usr/bin/env python3

import argparse
import logging
import os
import subprocess
import sys
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from commands.run.file_helpers import (
    copy_nextflow_config,
    get_single_csv,
    get_trio_csv,
    setup_results_links,
    write_resume_script,
    write_run_log,
)
from commands.run.gittools import (
    check_if_on_branchhead,
    check_valid_checkout,
    check_valid_repo,
    checkout_repo,
    fetch_repo,
    get_git_commit_hash_and_log,
    pull_branch,
)
from shared.util import check_valid_config_path, load_config

description = """
The intent of this script is to make running control samples on specific versions of pipelines easy.

The steps it performs:

1. Check out commit, tag or branch in target repo
2. Prepare CSV file for the run
3. Execute the pipeline

It can be configured to run singles, trios and start with FASTQ, BAM and VCF.
"""

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main(
    config: ConfigParser,
    label: Optional[str],
    checkout: str,
    base_dir: Optional[Path],
    repo: Optional[Path],
    start_data: str,
    dry_run: bool,
    stub_run: bool,
    run_type: str,
    skip_confirmation: bool,
    queue: Optional[str],
    no_start: bool,
    datestamp: bool,
    verbose: bool,
):
    logger.info(f"Preparing run, type: {run_type}, data: {start_data}")

    check_valid_config_arguments(config, run_type, start_data, base_dir, repo)
    base_dir = (
        base_dir if base_dir is not None else Path(config.get("settings", "base"))
    )
    repo = repo if repo is not None else Path(config.get("settings", "repo"))
    datestamp = datestamp or config.getboolean("settings", "datestamp")

    check_valid_repo(repo)
    do_repo_checkout(repo, checkout, verbose, skip_confirmation)
    (commit_hash, last_log) = get_git_commit_hash_and_log(logger, repo, verbose)
    logger.info(last_log)
    run_label = build_run_label(run_type, checkout, label, stub_run, start_data)

    if not datestamp:
        results_dir = base_dir / run_label
    else:
        ds = datetime.now().strftime("%y%m%d-%H%M")
        results_dir = base_dir / f"{ds}_{run_label}"

    confirm_run_if_results_exists(results_dir, skip_confirmation)

    if not dry_run:
        results_dir.mkdir(exist_ok=True, parents=True)

    run_log_path = results_dir / "run.log"
    if dry_run:
        logging.info(f"(dry) Writing log to {run_log_path}")
    else:
        write_run_log(
            run_log_path,
            run_type,
            label or "no label",
            checkout,
            config,
            commit_hash,
        )

    run_type_settings = dict(config[run_type])

    if not config.getboolean(run_type, "trio"):
        csv = get_single_csv(
            config, run_type_settings, run_label, start_data, queue, stub_run
        )
    else:
        csv = get_trio_csv(
            config, run_type_settings, run_label, start_data, queue, stub_run
        )
    out_csv = results_dir / "run.csv"
    if dry_run:
        logging.info(f"(dry) Writing CSV to {out_csv}")
    else:
        csv.write_to_file(str(out_csv))

    start_nextflow_command = build_start_nextflow_analysis_cmd(
        config["settings"]["start_nextflow_analysis"],
        out_csv,
        results_dir,
        config["settings"]["executor"],
        config["settings"]["cluster"],
        config["settings"]["queue"],
        config["settings"]["singularity_version"],
        config["settings"]["nextflow_version"],
        config["settings"]["container"],
        str(repo / config["settings"]["runscript"]),
        run_type_settings["profile"],
        stub_run,
        no_start,
    )

    # Setup results files
    write_resume_script(
        logger,
        results_dir,
        start_nextflow_command,
        dry_run,
    )
    copy_nextflow_config(repo, results_dir)
    setup_results_links(logger, config, results_dir, run_label, dry_run)

    start_run(start_nextflow_command, dry_run, skip_confirmation)


def confirm_run_if_results_exists(results_dir: Path, skip_confirmation: bool):
    if results_dir.exists() and not skip_confirmation:
        confirmation = input(
            f"The results dir {results_dir} already exists. Do you want to proceed? (y/n) "
        )

        if confirmation != "y":
            logger.info("Exiting ...")
            sys.exit(1)


def do_repo_checkout(repo: Path, checkout: str, verbose: bool, skip_confirmation: bool):
    logger.info("Fetching latest changes for repo")
    fetch_repo(logger, repo, verbose)
    check_valid_checkout(logger, repo, checkout, verbose)
    logger.info(f"Checking out: {checkout} in {str(repo)}")
    checkout_repo(logger, repo, checkout, verbose)
    on_branch_head = check_if_on_branchhead(logger, repo, verbose)
    if on_branch_head:
        branch = checkout
        if skip_confirmation:
            confirmation = "y"
        else:
            confirmation = input(
                f"You have checked out the branch {branch} in {repo}. Do you want to pull? (y/n) "
            )
        if confirmation == "y":
            logger.info("Pulling from origin")
            pull_branch(logger, repo, branch, verbose)


def check_valid_config_arguments(
    config: ConfigParser,
    run_type: str,
    start_data: str,
    base_dir: Optional[Path],
    repo: Optional[Path],
):
    if not config.has_section(run_type):
        raise ValueError(f"Valid config keys are: {config.sections()}")
    valid_start_data = ["fq", "bam", "vcf"]
    if start_data not in valid_start_data:
        raise ValueError(f"Valid start_data types are: {', '.join(valid_start_data)}")

    if base_dir is None:
        if not check_valid_config_path(config, "settings", "base"):
            found = config.get("settings", "base")
            raise ValueError(
                f"A valid output base folder must be specified either through the '--base' flag, or in the config['settings']['base']. Found: {found}"
            )

    if repo is None:
        if not check_valid_config_path(config, "settings", "repo"):
            found = config.get("settings", "repo")
            raise ValueError(
                f"A valid repo must be specified either through the '--repo' flag, or in the config['settings']['repo']. Found: {found}"
            )


def build_run_label(
    run_type: str, checkout: str, label: Optional[str], stub_run: bool, start_data: str
) -> str:
    label_parts = [run_type]
    if label is not None:
        label_parts.append(label)
    label_parts.append(checkout)
    if stub_run:
        label_parts.append("stub")
    label_parts.append(start_data)
    run_label = "-".join(label_parts)

    if run_label.find("/") != -1:
        logger.warning(
            f"Found '/' characters in run label: {run_label}, replacing with '-'"
        )
        run_label = run_label.replace("/", "-")

    return run_label


def build_start_nextflow_analysis_cmd(
    start_nextflow_analysis_pl: str,
    csv: Path,
    results_dir: Path,
    executor: str,
    cluster: str,
    queue: str,
    singularity_version: str,
    nextflow_version: str,
    container: str,
    runscript: str,
    profile: str,
    stub_run: bool,
    no_start: bool,
) -> List[str]:

    out_dir = results_dir
    cron_dir = results_dir

    start_nextflow_command = [
        start_nextflow_analysis_pl,
        str(csv.resolve()),
        "--outdir",
        str(out_dir.resolve()),
        "--crondir",
        str(cron_dir.resolve()),
        "--executor",
        executor,
        "--cluster",
        cluster,
        "--queue",
        queue,
        "--singularity_version",
        singularity_version,
        "--nextflow_version",
        nextflow_version,
        "--container",
        container,
        "--pipeline",
        f'"{runscript} -profile {profile}"',
    ]
    if stub_run:
        start_nextflow_command.append("--custom_flags")
        start_nextflow_command.append("'-stub-run'")
        # start_nextflow_command.append("'-stub-run --no_scratch'")

    if no_start:
        start_nextflow_command.append("--nostart")

    return start_nextflow_command


def start_run(
    start_nextflow_command: List[str], dry_run: bool, skip_confirmation: bool
):
    if not dry_run:
        if not skip_confirmation:
            pretty_command = " \\\n    ".join(start_nextflow_command)
            confirmation = input(
                f"Do you want to run the following command:\n{pretty_command}\n(y/n) "
            )

            if confirmation == "y":
                subprocess.run(start_nextflow_command, check=True)
            else:
                logger.info("Exiting ...")
        else:
            subprocess.run(start_nextflow_command, check=True)
    else:
        joined_command = " ".join(start_nextflow_command)
        logger.info("(dry) " + joined_command)


def main_wrapper(args: argparse.Namespace):

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    config = load_config(logger, curr_dir, args.config)

    if args.silent:
        logger.setLevel(logging.WARNING)

    if args.baseline is not None:
        logging.info(
            "Performing additional baseline run as specified by --baseline flag"
        )

        if args.baseline_repo is not None:
            baseline_repo = str(args.baseline_repo)
        else:
            baseline_repo = config.get("settings", "baseline_repo", fallback="")
            if baseline_repo == "":
                logging.error(
                    "When running with --baseline a baseline repo must either be provided using --baseline_repo option or in the config"
                )
                sys.exit(1)

        main(
            config,
            "baseline" if args.label is None else f"{args.label}_baseline",
            args.baseline,
            Path(args.base) if args.base is not None else None,
            Path(baseline_repo),
            args.start_data,
            args.dry,
            args.stub,
            args.run_type,
            args.skip_confirmation,
            args.queue,
            args.nostart,
            args.datestamp,
            args.verbose,
        )
        logging.info("Now proceeding with checking out the --checkout")
    main(
        config,
        args.label,
        args.checkout,
        Path(args.base) if args.base is not None else None,
        Path(args.repo) if args.repo is not None else None,
        args.start_data,
        args.dry,
        args.stub,
        args.run_type,
        args.skip_confirmation,
        args.queue,
        args.nostart,
        args.datestamp,
        args.verbose,
    )


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--label", help="Something for you to use to remember the run")
    parser.add_argument(
        "--checkout",
        required=True,
        help="Tag, commit or branch to check out in --repo",
    )
    parser.add_argument(
        "--base",
        help="The base folder into which results folders are created following the pattern: {base}/{label}_{run_type}_{checkout}). Can also be specified in the config.",
    )
    parser.add_argument(
        "--repo",
        help="Path to the Git repository of the pipeline. Can also be specified in the config.",
    )
    parser.add_argument(
        "--baseline_repo",
        help="Optional second repo if running with --baseline option. Can also be specified in the config.",
    )
    parser.add_argument(
        "--start_data",
        default="fq",
        help="Start run from FASTQ (fq), BAM (bam) or VCF (vcf) (must be present in config)",
    )
    parser.add_argument(
        "--run_type",
        help="Select run type from the config (i.e. giab-single, giab-trio, seracare ...). Multiple comma-separated can be specified.",
        required=True,
    )
    parser.add_argument(
        "--dry",
        "-n",
        action="store_true",
        help="Go through the motions, but don't execute the pipeline",
    )
    parser.add_argument(
        "--skip_confirmation",
        action="store_true",
        help="If not set, you will be asked before starting the pipeline run",
    )
    parser.add_argument(
        "--stub", action="store_true", help="Pass the -stub-run flag to the pipeline"
    )
    parser.add_argument(
        "--config",
        help="Config file in INI format containing information about run types and cases",
    )
    parser.add_argument(
        "--queue",
        help="Optionally specify in which queue to run (i.e. low, grace-normal etc.)",
    )
    parser.add_argument(
        "--datestamp",
        help="Prefix output folder with datestamp (241111_1033_)",
        action="store_true",
    )
    parser.add_argument(
        "--nostart",
        action="store_true",
        help="Run start_nextflow_analysis.pl with nostart, printing the path to the SLURM job only",
    )
    parser.add_argument(
        "--baseline", help="Start a second baseline run and specified checkout"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print additional debug output"
    )
    parser.add_argument(
        "--silent", action="store_true", help="Run silently, produce only output files"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
