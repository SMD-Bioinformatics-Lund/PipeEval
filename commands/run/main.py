#!/usr/bin/env python3

import argparse
import logging
import subprocess
import sys
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from commands.run.file_helpers import (
    copy_nextflow_configs,
    get_csv,
    setup_results_links,
    write_resume_script,
    write_run_log,
)
from commands.run.gittools import (
    check_if_on_branchhead,
    check_valid_checkout,
    check_valid_repo,
    checkout_remote_branch,
    checkout_repo,
    fetch_repo,
    get_git_commit_hash_and_log,
    pull_branch,
)
from commands.run.help_classes.config_classes import RunConfig
from shared.constants import ASSAY_PLACEHOLDER

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
    config: RunConfig,
    label: Optional[str],
    checkout: str,
    base_dir: Optional[Path],
    repo: Optional[Path],
    start_data: str,
    stub_run: bool,
    run_profile: str,
    skip_confirmation: bool,
    no_start: bool,
    datestamp: bool,
    verbose: bool,
    assay: Optional[str],
    analysis: Optional[str],
    csv_base: Path,
    remote_name: str,
):
    logger.info(f"Preparing run, type: {run_profile}, data: {start_data}")

    base_dir = (
        base_dir if base_dir is not None else Path(config.general_settings.out_base)
    )
    repo = repo if repo is not None else Path(config.general_settings.repo)
    datestamp = datestamp or config.general_settings.datestamp

    check_valid_repo(repo)

    do_repo_checkout(repo, checkout, verbose, skip_confirmation, remote_name)
    (commit_hash, last_log) = get_git_commit_hash_and_log(logger, repo, verbose)
    logger.info(last_log)
    run_label = build_run_label(run_profile, checkout, label, stub_run, start_data)

    if not datestamp:
        results_dir = base_dir / run_label
    else:
        ds = datetime.now().strftime("%y%m%d-%H%M")
        results_dir = base_dir / f"{ds}_{run_label}"

    confirm_run_if_results_exists(results_dir, skip_confirmation)

    results_dir.mkdir(exist_ok=True, parents=True)

    run_log_path = results_dir / "run.log"
    write_run_log(
        run_log_path,
        run_profile,
        label or "no label",
        checkout,
        config,
        commit_hash,
    )

    try:
        pipeline_info_path = results_dir / "pipeline_info"
        pipeline_name = config.run_profile.pipeline
        pipeline_info_path.write_text(pipeline_name)
    except Exception:
        logger.warning("Could not write pipeline_info file")

    assay = assay or ASSAY_PLACEHOLDER
    analysis = analysis or config.run_profile.run_profile

    out_csv = results_dir / "run.csv"
    csv_content = get_csv(logger, config, run_label, start_data, csv_base)

    out_csv.write_text(csv_content)

    def get_start_nextflow_command(quote_pipeline_arguments: bool) -> List[str]:
        command = build_start_nextflow_analysis_cmd(
            config.general_settings.start_nextflow_analysis,
            out_csv,
            results_dir,
            config.general_settings.executor,
            config.general_settings.cluster,
            config.general_settings.queue,
            config.general_settings.singularity_version,
            config.general_settings.nextflow_version,
            config.general_settings.container,
            str(repo / config.general_settings.runscript),
            config.run_profile.pipeline_profile,
            stub_run,
            no_start,
            quote_pipeline_arguments,
            [
                config.general_settings.repo / conf
                for conf in config.general_settings.nextflow_configs
            ],
        )
        return command

    write_resume_script(
        results_dir,
        get_start_nextflow_command(True),
    )
    logger.info("Copying nextflow configs")
    copy_nextflow_configs(repo, results_dir, config.general_settings.nextflow_configs)
    logger.info("Preparing results lists")
    setup_results_links(logger, config, results_dir, run_label, assay)

    start_run(get_start_nextflow_command(False), skip_confirmation)


def get_default_run_profiles() -> List[str]:
    config_path = Path(__file__).resolve().parent / "config/run_profile.ini"
    if not config_path.exists():
        return []
    config = ConfigParser()
    config.read(config_path)
    return sorted(config.sections())


def confirm_run_if_results_exists(results_dir: Path, skip_confirmation: bool):
    if results_dir.exists() and not skip_confirmation:
        confirmation = input(
            f"The results dir {results_dir} already exists. Do you want to proceed? (y/N) "
        )

        if confirmation != "y":
            logger.info("Exiting ...")
            sys.exit(1)


def do_repo_checkout(
    repo: Path, checkout: str, verbose: bool, skip_confirmation: bool, remote: str
):
    logger.info("Fetching latest changes for repo")

    # Sync with the remote repo
    fetch_repo(logger, repo, remote, verbose)

    # Consider that the checkout may be prefixed by the remote name
    # I.e. origin/my-branch
    remote_prefix = f"{remote}/"
    checkout_branch = checkout
    remote_checkout = None
    if checkout.startswith(remote_prefix):
        checkout_branch = checkout[len(remote_prefix) :]
        remote_checkout = checkout

    # Exists as something we can check out locally?
    valid_local = check_valid_checkout(logger, repo, checkout_branch, verbose)
    
    # If not, let's check in the remote
    # Can I create a local branch from the remote one?
    if not valid_local:
        logger.info(
            f"Did not find {checkout_branch} locally, checking in remote ({remote})"
        )
        if remote_checkout is None:
            remote_checkout = f"{remote}/{checkout_branch}"

        # Does it exist as a valid checkout on the remote?
        valid_remote = check_valid_checkout(logger, repo, remote_checkout, verbose)
        if not valid_remote:
            logger.error(
                f"Could not find checkout pattern {checkout} in local or remote"
            )
            sys.exit(1)

        logger.info(
            f"Checking out remote branch {remote_checkout} as {checkout_branch}"
        )
        # Yes, let's create a local branch from it
        checkout_remote_branch(
            logger, repo, checkout_branch, remote_checkout, verbose
        )
    else:
        logger.info(f"Checking out: {checkout_branch} in {str(repo)}")
        checkout_repo(logger, repo, checkout_branch, verbose)

    # Are we on a branch head?
    on_branch_head = check_if_on_branchhead(logger, repo, verbose)
    if on_branch_head:
        branch = checkout_branch
        if skip_confirmation:
            confirmation = "y"
        else:
            confirmation = input(
                f"You have checked out the branch {branch} in {repo}. Do you want to pull? (y/N) "
            )
        if confirmation == "y":
            logger.info(f"Pulling from {remote}")
            # Let's pull its latest content
            pull_branch(logger, repo, remote, branch, verbose)


def build_run_label(
    run_profile: str,
    checkout: str,
    label: Optional[str],
    stub_run: bool,
    start_data: str,
) -> str:
    label_parts = [run_profile]
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
    profile: Optional[str],
    stub_run: bool,
    no_start: bool,
    quote_pipeline_arguments: bool,
    nextflow_configs: List[Path],
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
    ]
    if quote_pipeline_arguments:
        start_nextflow_command.append(
            f'--pipeline "{runscript} -profile {profile}"',
        )
    else:
        start_nextflow_command.append(
            "--pipeline",
        )
        if profile:
            start_nextflow_command.append(
                f"{runscript} -profile {profile}",
            )
        else:
            start_nextflow_command.append(
                f"{runscript}",
            )

    # start_nextflow_command.append("--custom_flags")
    # Provide configs directly
    # Normally autodetected as nextflow.config in the repo base
    # This becomes important for instance for nf-core pipelines where we
    # use multiple config files
    custom_flag_parts = []
    for conf in nextflow_configs:
        custom_flag_parts.extend(["-c", str(conf)])
    if stub_run:
        custom_flag_parts.append("-stub-run")

    if len(custom_flag_parts) > 0:

        start_nextflow_command.append("--custom_flags")

        custom_flags = " ".join(custom_flag_parts)
        if quote_pipeline_arguments:
            custom_flags = f'"{custom_flags}"'

        start_nextflow_command.append(custom_flags)

    if no_start:
        start_nextflow_command.append("--nostart")

    return start_nextflow_command


def start_run(start_nextflow_command: List[str], skip_confirmation: bool):
    if not skip_confirmation:
        pretty_command = " \\\n    ".join(start_nextflow_command)
        confirmation = input(
            f"Do you want to run the following command:\n{pretty_command}\n(y/N) "
        )

        if confirmation != "y":
            logger.info("Exiting ...")
            return

    subprocess.run(start_nextflow_command, check=True)


def main_wrapper(args: argparse.Namespace):

    parent_path = Path(__file__).resolve().parent
    profile_conf_path = (
        args.run_profile_config or parent_path / "config/run_profile.ini"
    )
    pipeline_settings_path = (
        args.pipeline_settings_config or parent_path / "config/pipeline_settings.ini"
    )
    samples_path = args.samples_config or parent_path / "config/samples.ini"

    csv_base = args.csv_base or parent_path / "config/csv_templates"

    config = RunConfig(
        logger,
        args.run_profile,
        profile_conf_path,
        pipeline_settings_path,
        samples_path,
    )

    if args.silent:
        logger.setLevel(logging.WARNING)

    if args.baseline is not None:
        logger.info(
            "Performing additional baseline run as specified by --baseline flag"
        )

        if args.baseline_repo is not None:
            baseline_repo = str(args.baseline_repo)
        else:
            baseline_repo = config.general_settings.baseline_repo
            if not baseline_repo:
                logger.error(
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
            args.stub,
            args.run_profile,
            args.skip_confirmation,
            args.nostart,
            args.datestamp,
            args.verbose,
            args.assay,
            args.analysis,
            csv_base,
            args.remote,
        )
        logger.info("Now proceeding with checking out the --checkout")
    main(
        config,
        args.label,
        args.checkout,
        Path(args.base) if args.base is not None else None,
        Path(args.repo) if args.repo is not None else None,
        args.start_data,
        args.stub,
        args.run_profile,
        args.skip_confirmation,
        args.nostart,
        args.datestamp,
        args.verbose,
        args.assay,
        args.analysis,
        csv_base,
        args.remote,
    )


def add_arguments(parser: argparse.ArgumentParser):
    run_profiles = get_default_run_profiles()
    run_profile_help = (
        "Select run profile from the config. Multiple comma-separated can be specified."
    )
    if run_profiles:
        run_profile_help = f"{run_profile_help} Available profiles from config: {', '.join(run_profiles)}."

    parser.add_argument(
        "--label",
        help="Optional custom label that will be part of the run label and thus part of the results folder name",
    )
    parser.add_argument(
        "--checkout",
        required=True,
        help="Tag, commit or branch to check out in --repo",
    )
    parser.add_argument(
        "--base",
        help="The base folder into which results folders are created following the pattern: {base}/{label}_{run_profile}_{checkout}). Can also be specified in the config.",
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
        "--run_profile",
        help=run_profile_help,
        required=True,
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
        "--run_profile_config",
        help="Config file in INI format with PipeEval run profile info. Default path in commands/run/run_profile.config",
    )
    parser.add_argument(
        "--pipeline_settings_config",
        help="Config file in INI format with PipeEval run pipeline settings. Default path in commands/run/pipeline_settings.config",
    )
    parser.add_argument(
        "--samples_config",
        help="Config file in INI format with PipeEval samples info. Default path in commands/run/samples.config",
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
    parser.add_argument(
        "--assay",
        help="Specify a custom assay in the CSV file (for Scout yaml generation testing, otherwise defaults to 'dev')",
    )
    parser.add_argument(
        "--analysis",
        help="Specify a custom analysis in the CSV file (defaults to --run_profile argument)",
    )
    parser.add_argument("--csv_base", help="Base folder for CSV templates.")
    parser.add_argument(
        "--remote",
        help="Git remote from which to checkout if not present locally",
        default="origin",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
