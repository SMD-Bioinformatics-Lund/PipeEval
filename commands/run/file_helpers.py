import sys
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional

from commands.run.help_classes.config_classes import RunConfig, SampleConfig
from commands.run.help_classes.help_classes import CsvEntry, CSVRow


def write_resume_script(results_dir: Path, run_command: List[str]):
    resume_command = run_command + ["--resume"]
    resume_script = results_dir / "resume.sh"
    resume_script.write_text(" ".join(resume_command))


def copy_nextflow_config(repo: Path, results_dir: Path):
    config_path = repo / "nextflow.config"
    dest_path = results_dir / "nextflow.config"
    dest_path.write_text(config_path.read_text())


def setup_results_links(
    logger: Logger,
    config: RunConfig,
    results_dir: Path,
    run_label: str,
    assay: str,
):

    log_base_dir = config.pipeline_settings.log_base_dir
    trace_base_dir = config.pipeline_settings.trace_base_dir
    work_base_dir = config.pipeline_settings.work_base_dir

    current_date = datetime.now()
    date_stamp = current_date.strftime("%Y-%m-%d")

    log_link = results_dir / "nextflow.log"
    trace_link = results_dir / "trace.txt"
    work_link = results_dir / "work"

    log_link_target = Path(f"{log_base_dir}/{run_label}.{assay}.{date_stamp}.log")
    trace_link_target = Path(f"{trace_base_dir}/{run_label}.{assay}.trace.txt")
    work_link_target = Path(f"{work_base_dir}/{run_label}.{assay}")

    if log_link.exists():
        logger.warning(f"{log_link} already exists, removing previous link")
        log_link.unlink()

    if trace_link.exists():
        logger.warning(f"{trace_link} already exists, removing previous link")
        trace_link.unlink()

    if work_link.exists():
        logger.warning(f"{work_link} already exists, removing previous link")
        work_link.unlink()

    log_link.symlink_to(log_link_target)
    trace_link.symlink_to(trace_link_target)
    work_link.symlink_to(work_link_target)


def get_csv(
    logger: Logger,
    config: RunConfig,
    run_label: str,
    starting_run_from: str,
    queue: Optional[str],
    assay: str,
    analysis: str,
) -> CsvEntry:

    sample_ids = config.run_profile.samples
    samples = []

    for i, sample_id in enumerate(sample_ids):
        sample_type = config.run_profile.sample_types[i]
        sample = parse_sample(
            logger,
            sample_id,
            config.run_profile.samples,
            sample_type,
            config.all_samples,
            starting_run_from,
            config.run_profile.case_type,
            config.run_profile.sample_types,
        )
        if not Path(sample.read1).exists() or not Path(sample.read2).exists():
            raise FileNotFoundError(
                f"One or both files missing: {sample.read1} {sample.read2}"
            )
        samples.append(sample)

    default_panel = config.run_profile.default_panel

    # if not default_panel:
    #     logger.error("Expected a default panel, found none")
    #     sys.exit(1)

    run_csv = CsvEntry(run_label, samples, queue, assay, analysis, default_panel)

    return run_csv


def parse_sample(
    logger: Logger,
    sample_id: str,
    case_sample_ids: List[str],
    sample_type: str,
    all_samples_dict: Dict[str, SampleConfig],
    starting_run_from: str,
    case_type: str,
    sample_types: List[str],
) -> CSVRow:

    target_sample = all_samples_dict[sample_id]

    if starting_run_from == "vcf":

        if target_sample.vcf is None:
            logger.error('Run mode is "vcf" but missing in config')
            sys.exit(1)

        fw = target_sample.vcf
        rv = f"{fw}.tbi"
    elif starting_run_from == "bam":

        if target_sample.bam is None:
            logger.error('Run mode is "bam" but missing in config')
            sys.exit(1)

        fw = target_sample.bam
        rv = f"{fw}.bai"
    elif starting_run_from == "fq":

        if target_sample.fq_fw is None or target_sample.fq_rv is None:
            logger.error(
                f'Run mode is "fq" but missing at least one of fastq entries (fw: {target_sample.fq_fw} rv: {target_sample.fq_rv})'
            )
            sys.exit(1)

        fw = target_sample.fq_fw
        rv = target_sample.fq_rv
    else:
        raise ValueError(
            f"Unknown start_data, found: {starting_run_from}, valid are vcf, bam, fq"
        )

    if case_type == "trio" and sample_type == "proband":
        print("Hitting the if with sample types", sample_types)
        mother_idx = [
            i for (i, sample_type) in enumerate(sample_types) if sample_type == "mother"
        ][0]
        mother = case_sample_ids[mother_idx]
        father_idx = [
            i for (i, sample_type) in enumerate(sample_types) if sample_type == "father"
        ][0]
        father = case_sample_ids[father_idx]

        print("mother and father", mother, father)
    else:
        mother = None
        father = None

    if len(case_sample_ids) == 1 and sample_type is None:
        sample_type = "proband"

    csv_row = CSVRow(
        target_sample.id,
        str(target_sample.clarity_pool_id),
        target_sample.clarity_sample_id,
        target_sample.sex,
        sample_type,
        fw,
        rv,
        mother,
        father,
    )
    return csv_row


def write_run_log(
    run_log_path: Path,
    run_profile: str,
    label: str,
    checkout_str: str,
    config: RunConfig,
    commit_hash: str,
):
    with run_log_path.open("w") as out_fh:
        print("# Settings", file=out_fh)
        print(f"output dir: {run_log_path.parent}", file=out_fh)
        print(f"run profile: {run_profile}", file=out_fh)
        print(f"run label: {label}", file=out_fh)
        print(f"checkout: {checkout_str}", file=out_fh)
        print(f"commit hash: {commit_hash}", file=out_fh)
        print("", file=out_fh)
        print("# Config file - settings", file=out_fh)
        for key, val in config.get_setting_entries().items():
            print(f"{key}: {val}", file=out_fh)

        print(f"# Config file - {run_profile}", file=out_fh)
        for key, val in config.get_profile_entries().items():
            print(f"{key}: {val}", file=out_fh)
