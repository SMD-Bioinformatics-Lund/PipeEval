#!/usr/bin/env python3

description = """
The intent of this script is to make running control samples on specific versions of pipelines easy.

The steps it performs:

1. Check out commit, tag or branch in target repo
2. Prepare CSV file for the run
3. Execute the pipeline

It can be configured to run singles, trios and start with FASTQ, BAM and VCF.
"""

import argparse
from pathlib import Path
import subprocess
import logging
import sys
import os
from configparser import ConfigParser
from datetime import datetime
from typing import Any, List, Dict, Optional

from runner.gittools import (
    check_valid_checkout,
    check_valid_repo,
    checkout_repo,
    get_git_commit_hash_and_log,
)
from util.shared_utils import check_valid_config_path, load_config

from .help_classes import Case, CsvEntry


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOG = logging.getLogger(__name__)


def main(
    config_path: Optional[str],
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
):
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    config = load_config(curr_dir, config_path)

    check_valid_config_arguments(config, run_type, start_data, base_dir, repo)
    base_dir = (
        base_dir if base_dir is not None else Path(config.get("settings", "baseout"))
    )
    if repo is not None:
        logging.warning(
            "Note that the path specified in --repo might not be the same as specified in the assay as defined in the config. Most likely this will yield unexpected results."
        )
    repo = repo if repo is not None else Path(config.get("settings", "repo"))
    datestamp = datestamp or config.getboolean("settings", "datestamp")

    check_valid_repo(repo)
    check_valid_checkout(repo, checkout)
    LOG.info(f"Checking out: {checkout} in {str(repo)}")
    checkout_repo(repo, checkout)
    (commit_hash, last_log) = get_git_commit_hash_and_log(repo)
    LOG.info(last_log)

    run_label = build_run_label(run_type, checkout, label, stub_run, start_data)

    if not datestamp:
        results_dir = base_dir / run_label
    else:
        ds = datetime.now().strftime("%y%m%d-%H%M")
        results_dir = base_dir / f"{ds}_{run_label}"
    if results_dir.exists():
        confirmation = input(
            f"The results dir {results_dir} already exists. Do you want to proceed? (y/n) "
        )

        if confirmation != "y":
            LOG.info("Exiting ...")
            sys.exit(1)

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

    start_run(start_nextflow_command, dry_run, skip_confirmation)

    write_resume_script(
        results_dir,
        config["settings"]["start_nextflow_analysis"],
        out_csv,
        stub_run,
        dry_run,
    )

    setup_results_links(config, results_dir, run_label, run_type, dry_run)


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

    # FIXME: Look over the logic here. Not nice with repeated config.get at the moment
    if base_dir is None:
        if not check_valid_config_path(config, "settings", "baseout"):
            found = config.get("settings", "baseout")
            raise ValueError(
                f"A valid output base folder must be specified either through the '--baseout' flag, or in the config['settings']['baseout']. Found: {found}"
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
        LOG.warning(
            f"Found '/' characters in run label: {run_label}, replacing with '-'"
        )
        run_label = run_label.replace("/", "-")

    return run_label


def write_run_log(
    run_log_path: Path,
    run_type: str,
    tag: str,
    checkout_str: str,
    config: ConfigParser,
    commit_hash: str,
):
    with run_log_path.open("w") as out_fh:
        print("# Settings", file=out_fh)
        print(f"output dir: {run_log_path.parent}", file=out_fh)
        print(f"run type: {run_type}", file=out_fh)
        print(f"tag: {tag}", file=out_fh)
        print(f"checkout: {checkout_str}", file=out_fh)
        print(f"commit hash: {commit_hash}", file=out_fh)
        print("", file=out_fh)
        print("# Config file - settings", file=out_fh)
        for key, val in config["settings"].items():
            print(f"{key}: {val}", file=out_fh)

        print(f"# Config file - {run_type}", file=out_fh)
        for key, val in config[run_type].items():
            print(f"{key}: {val}", file=out_fh)


def get_single_csv(
    config: ConfigParser,
    run_type_settings: Dict[str, Any],
    run_label: str,
    start_data: str,
    queue: Optional[str],
    stub_run: bool,
):
    case_id = run_type_settings["case"]
    case = config[case_id]

    # Replace real data with dummy files in stub run to avoid scratching
    if stub_run:
        stub_case = config["settings"]
        for key in stub_case:
            case[key] = stub_case[key]

    case = parse_case(dict(case), start_data, is_trio=False)

    if not Path(case.read1).exists() or not Path(case.read2).exists():
        raise FileNotFoundError(f"One or both files missing: {case.read1} {case.read2}")

    run_csv = CsvEntry(run_label, [case], queue)
    return run_csv


def get_trio_csv(
    config: ConfigParser,
    run_type_settings: Dict[str, Any],
    run_label: str,
    start_data: str,
    queue: Optional[str],
    stub_run: bool,
):

    case_ids = run_type_settings["cases"].split(",")
    assert (
        len(case_ids) == 3
    ), f"For a trio, three fields are expected, found: {case_ids}"
    cases: List[Case] = []
    for case_id in case_ids:
        case_dict = config[case_id]

        # Replace real data with dummy files in stub run to avoid scratching
        if stub_run:
            stub_case = config["settings"]
            for key in stub_case:
                case_dict[key] = stub_case[key]

        case = parse_case(dict(case_dict), start_data, is_trio=True)

        if not Path(case.read1).exists() or not Path(case.read2).exists():
            raise FileNotFoundError(
                f"One or both files missing: {case.read1} {case.read2}"
            )

        cases.append(case)

    run_csv = CsvEntry(run_label, cases, queue)
    return run_csv


def parse_case(case_dict: Dict[str, str], start_data: str, is_trio: bool) -> Case:
    if start_data == "vcf":
        fw = case_dict["vcf"]
        rv = f"{fw}.tbi"
    elif start_data == "bam":
        fw = case_dict["bam"]
        rv = f"{fw}.bai"
    elif start_data == "fq":
        fw = case_dict["fq_fw"]
        rv = case_dict["fq_rv"]
    else:
        raise ValueError(
            f"Unknown start_data, found: {start_data}, valid are vcf, bam, fq"
        )

    case = Case(
        case_dict["id"],
        case_dict["clarity_pool_id"],
        case_dict["clarity_sample_id"],
        case_dict["sex"],
        case_dict["type"],
        fw,
        rv,
        mother=case_dict.get("mother") if is_trio else None,
        father=case_dict.get("father") if is_trio else None,
    )
    return case


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
        f"{runscript} -profile {profile}",
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
    joined_command = " ".join(start_nextflow_command)
    if not dry_run:
        if not skip_confirmation:
            confirmation = input(
                f"Do you want to run the following command:\n{joined_command}\n(y/n) "
            )

            if confirmation == "y":
                subprocess.run(start_nextflow_command, check=True)
            else:
                LOG.info("Exiting ...")
        else:
            subprocess.run(start_nextflow_command, check=True)
    else:
        LOG.info("(dry) " + joined_command)


def write_resume_script(
    results_dir: Path, run_command: str, csv: Path, stub_run: bool, dry_run: bool
):
    resume_command_parts = [
        run_command,
        str(csv.absolute()),
    ]
    if stub_run:
        resume_command_parts.append("--custom_flags")
        resume_command_parts.append("'-stub-run'")
    resume_command = " ".join(resume_command_parts)
    resume_script = results_dir / "resume.sh"
    if not dry_run:
        resume_script.write_text(resume_command)
    else:
        logging.info(f"(dry) Writing {resume_command} to {resume_script}")


def setup_results_links(
    config: ConfigParser, results_dir: Path, run_label: str, run_type: str, dry: bool
):

    assay = config[run_type]["assay"]

    log_base_dir = config["settings"]["log_base_dir"]
    trace_base_dir = config["settings"]["trace_base_dir"]
    work_base_dir = config["settings"]["work_base_dir"]

    current_date = datetime.now()
    date_stamp = current_date.strftime("%Y-%m-%d")

    log_link = results_dir / "nextflow.log"
    trace_link = results_dir / "trace.txt"
    work_link = results_dir / "work"

    log_link_target = Path(f"{log_base_dir}/{run_label}.{assay}.{date_stamp}.log")
    trace_link_target = Path(f"{trace_base_dir}/{run_label}.{assay}.trace.txt")
    work_link_target = Path(f"{work_base_dir}/{run_label}.{assay}")

    if log_link.exists():
        LOG.warning(f"{log_link} already exists, removing previous link")
        if not dry:
            log_link.unlink()

    if trace_link.exists():
        LOG.warning(f"{trace_link} already exists, removing previous link")
        if not dry:
            trace_link.unlink()

    if work_link.exists():
        LOG.warning(f"{work_link} already exists, removing previous link")
        if not dry:
            work_link.unlink()

    if not dry:
        log_link.symlink_to(log_link_target)
        trace_link.symlink_to(trace_link_target)
        work_link.symlink_to(work_link_target)
    else:
        LOG.info(f"(dry) Linking log from {log_link_target} to {log_link}")
        LOG.info(f"(dry) Linking trace from {trace_link_target} to {trace_link}")
        LOG.info(f"(dry) Linking work from {work_link_target} to {work_link}")


def main_wrapper(args: argparse.Namespace):
    if args.baseline is not None:
        logging.info(
            "Performing additional baseline run as specified by --baseline flag"
        )
        logging.warning(
            "--baseline flag might not work as intended at the moment, as it checks out a separate version of the repo where both baseline and checkout are executed."
        )
        main(
            args.config,
            "baseline" if args.label is None else f"{args.label}_baseline",
            args.baseline,
            Path(args.baseout) if args.baseout is not None else None,
            Path(args.repo) if args.repo is not None else None,
            args.start_data,
            args.dry,
            args.stub,
            args.run_type,
            args.skip_confirmation,
            args.queue,
            args.nostart,
            args.datestamp,
        )
        logging.info("Now proceeding with checking out the --checkout")
    main(
        args.config,
        args.label,
        args.checkout,
        Path(args.baseout) if args.baseout is not None else None,
        Path(args.repo) if args.repo is not None else None,
        args.start_data,
        args.dry,
        args.stub,
        args.run_type,
        args.skip_confirmation,
        args.queue,
        args.nostart,
        args.datestamp,
    )


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--label", help="Something for you to use to remember the run")
    parser.add_argument(
        "--checkout",
        required=True,
        help="Tag, commit or branch to check out in --repo",
    )
    parser.add_argument(
        "--baseout",
        help="The base folder into which results folders are created following the pattern: {base}/{label}_{run_type}_{checkout}). Can also be specified in the config.",
    )
    parser.add_argument(
        "--repo",
        help="Path to the Git repository of the pipeline. Can also be specified in the config.",
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
