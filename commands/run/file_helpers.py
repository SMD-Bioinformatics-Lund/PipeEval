from datetime import datetime
from logging import Logger
from pathlib import Path
import sys
from typing import Dict, List, Optional

from commands.run.help_classes.help_classes import Case, CsvEntry
from commands.run.help_classes.config_classes import RunConfig, SampleConfig


def write_resume_script(
    results_dir: Path, run_command: List[str]
):
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


def get_single_csv(
    logger: Logger,
    config: RunConfig,
    run_label: str,
    start_data: str,
    queue: Optional[str],
    assay: str,
    analysis: str,
):
    sample_id = config.run_profile.samples[0]
    sample_conf = config.get_sample_conf(sample_id)

    case = parse_sample(logger, sample_conf, start_data, "single")

    if not Path(case.read1).exists() or not Path(case.read2).exists():
        raise FileNotFoundError(f"One or both files missing: {case.read1} {case.read2}")

    diagnosis = config.run_profile.default_panel

    if not diagnosis:
        logger.error("No default ")
        sys.exit(1)

    run_csv = CsvEntry(run_label, [case], queue, assay, analysis, diagnosis)
    return run_csv


# FIXME: Generalize for other numbers of samples
# Also need to generalize different CSV formats, right?
# Hmm. That is a more tricky one.
def get_csv(
    logger: Logger,
    config: RunConfig,
    run_label: str,
    start_data: str,
    queue: Optional[str],
    assay: str,
    analysis: str,
):

    sample_ids = config.run_profile.samples
    samples: List[Case] = []
    for sample_id in sample_ids:
        sample_config = config.get_sample_conf(sample_id)

        case = parse_sample(logger, sample_config, start_data, "trio")

        if not Path(case.read1).exists() or not Path(case.read2).exists():
            raise FileNotFoundError(
                f"One or both files missing: {case.read1} {case.read2}"
            )

        samples.append(case)

    default_panel = config.run_profile.default_panel

    if not default_panel:
        logger.error("Expected a default panel, found none")
        sys.exit(1)

    run_csv = CsvEntry(run_label, samples, queue, assay, analysis, default_panel)
    return run_csv


def parse_sample(logger: Logger, conf: SampleConfig, start_data: str, sample_type: str) -> Case:
    if start_data == "vcf":

        if conf.vcf is None:
            logger.error(f'Run mode is "vcf" but missing in config')
            sys.exit(1)

        fw = conf.vcf
        rv = f"{fw}.tbi"
    elif start_data == "bam":

        if conf.bam is None:
            logger.error(f'Run mode is "bam" but missing in config')
            sys.exit(1)

        fw = conf.bam
        rv = f"{fw}.bai"
    elif start_data == "fq":

        if conf.fq_fw is None or conf.fq_rv is None:
            logger.error(f'Run mode is "fq" but missing at least one of fastq entries (fw: {conf.fq_fw} rv: {conf.fq_rv})')
            sys.exit(1)

        fw = conf.fq_fw
        rv = conf.fq_rv
    else:
        raise ValueError(
            f"Unknown start_data, found: {start_data}, valid are vcf, bam, fq"
        )

    case = Case(
        conf.id,
        str(conf.clarity_pool_id),
        conf.clarity_sample_id,
        conf.sex,
        conf.type,
        fw,
        rv,
        # FIXME: How to do this? "get_relative ?" No, need a trio / duo structure externally here
        # This requires more thought
        mother=None,
        father=None
        # mother=conf.mother if is_trio else None,
        # father=conf.father if is_trio else None,
    )
    return case


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
