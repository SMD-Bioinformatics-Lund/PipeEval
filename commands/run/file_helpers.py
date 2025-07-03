from configparser import ConfigParser
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Any, Dict, List, Optional

from commands.run.help_classes import Case, CsvEntry
from shared.constants import ASSAY_PLACEHOLDER

def write_resume_script(
    logging: Logger, results_dir: Path, run_command: List[str], dry_run: bool
):
    resume_command = run_command + ["--resume"]
    resume_script = results_dir / "resume.sh"
    if not dry_run:
        resume_script.write_text(" ".join(resume_command))
    else:
        logging.info(f"(dry) Writing {resume_command} to {resume_script}")


def copy_nextflow_config(repo: Path, results_dir: Path):
    config_path = repo / "nextflow.config"
    dest_path = results_dir / "nextflow.config"
    dest_path.write_text(config_path.read_text())


def setup_results_links(
    logger: Logger, config: ConfigParser, results_dir: Path, run_label: str, dry: bool
):

    log_base_dir = config["settings"]["log_base_dir"]
    trace_base_dir = config["settings"]["trace_base_dir"]
    work_base_dir = config["settings"]["work_base_dir"]

    current_date = datetime.now()
    date_stamp = current_date.strftime("%Y-%m-%d")

    log_link = results_dir / "nextflow.log"
    trace_link = results_dir / "trace.txt"
    work_link = results_dir / "work"

    log_link_target = Path(
        f"{log_base_dir}/{run_label}.{ASSAY_PLACEHOLDER}.{date_stamp}.log"
    )
    trace_link_target = Path(
        f"{trace_base_dir}/{run_label}.{ASSAY_PLACEHOLDER}.trace.txt"
    )
    work_link_target = Path(f"{work_base_dir}/{run_label}.{ASSAY_PLACEHOLDER}")

    if log_link.exists():
        logger.warning(f"{log_link} already exists, removing previous link")
        if not dry:
            log_link.unlink()

    if trace_link.exists():
        logger.warning(f"{trace_link} already exists, removing previous link")
        if not dry:
            trace_link.unlink()

    if work_link.exists():
        logger.warning(f"{work_link} already exists, removing previous link")
        if not dry:
            work_link.unlink()

    if not dry:
        log_link.symlink_to(log_link_target)
        trace_link.symlink_to(trace_link_target)
        work_link.symlink_to(work_link_target)
    else:
        logger.info(f"(dry) Linking log from {log_link_target} to {log_link}")
        logger.info(f"(dry) Linking trace from {trace_link_target} to {trace_link}")
        logger.info(f"(dry) Linking work from {work_link_target} to {work_link}")


def get_single_csv(
    config: ConfigParser,
    run_type_settings: Dict[str, Any],
    run_label: str,
    start_data: str,
    queue: Optional[str],
    stub_run: bool,
):
    case_id = run_type_settings["case"]
    case_conf = config[case_id]

    # Replace real data with dummy files in stub run to avoid scratching
    if stub_run:
        stub_case = config["settings"]
        for key in stub_case:
            case_conf[key] = stub_case[key]

    case = parse_case(dict(case_conf), start_data, is_trio=False)

    if not Path(case.read1).exists() or not Path(case.read2).exists():
        raise FileNotFoundError(f"One or both files missing: {case.read1} {case.read2}")

    analysis = run_type_settings["profile"]
    default_panel = run_type_settings["default_panel"]
    run_csv = CsvEntry(
        run_label, [case], queue, ASSAY_PLACEHOLDER, analysis, default_panel
    )
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

    analysis = run_type_settings["profile"]
    default_panel = run_type_settings["default_panel"]
    run_csv = CsvEntry(
        run_label, cases, queue, ASSAY_PLACEHOLDER, analysis, default_panel
    )
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


def write_run_log(
    run_log_path: Path,
    run_type: str,
    label: str,
    checkout_str: str,
    config: ConfigParser,
    commit_hash: str,
):
    with run_log_path.open("w") as out_fh:
        print("# Settings", file=out_fh)
        print(f"output dir: {run_log_path.parent}", file=out_fh)
        print(f"run type: {run_type}", file=out_fh)
        print(f"run label: {label}", file=out_fh)
        print(f"checkout: {checkout_str}", file=out_fh)
        print(f"commit hash: {commit_hash}", file=out_fh)
        print("", file=out_fh)
        print("# Config file - settings", file=out_fh)
        for key, val in config["settings"].items():
            print(f"{key}: {val}", file=out_fh)

        print(f"# Config file - {run_type}", file=out_fh)
        for key, val in config[run_type].items():
            print(f"{key}: {val}", file=out_fh)
