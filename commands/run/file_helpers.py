import sys
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional

from commands.run.help_classes.config_classes import RunConfig, SampleConfig


def write_resume_script(results_dir: Path, run_command: List[str]):
    resume_command = run_command + ["--resume"]
    resume_script = results_dir / "resume.sh"
    resume_script.write_text(" ".join(resume_command))


def copy_nextflow_configs(repo: Path, results_dir: Path, configs: List[Path]):

    for config in configs:
        config_path = repo / config
        dest_path = results_dir / config.name
        dest_path.write_text(config_path.read_text())


def setup_results_links(
    logger: Logger,
    config: RunConfig,
    results_dir: Path,
    run_label: str,
    assay: str,
):

    log_base_dir = config.general_settings.log_base_dir
    trace_base_dir = config.general_settings.trace_base_dir
    work_base_dir = config.general_settings.work_base_dir

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


def get_replace_map(
    logger: Logger,
    starting_run_from: str,
    sample: SampleConfig,
    run_label: str,
    default_panel: Optional[str],
    case_type: str,
    all_sample_ids: List[str],
    all_sample_types: List[str],
) -> Dict[str, str]:

    replace_map = {
        f"<id {sample.sample_type}>": sample.id,
        f"<group>": run_label,
        f"<sex {sample.sample_type}>": sample.sex,
    }

    if default_panel:
        replace_map["<default_panel>"] = default_panel

    if starting_run_from == "fq":
        if not sample.fq_fw or not sample.fq_rv:
            logger.error(
                f"Start run from fastq but at least one file missing. Fw: {sample.fq_fw} Rv: {sample.fq_rv}"
            )
            sys.exit(1)
        replace_map[f"<read1 {sample.sample_type}>"] = sample.fq_fw
        replace_map[f"<read2 {sample.sample_type}>"] = sample.fq_rv
    elif starting_run_from == "bam":
        if not sample.bam:
            logger.error(f"Start run from bam but bam is missing")
            sys.exit(1)
        replace_map[f"<read1 {sample.sample_type}>"] = sample.bam
        replace_map[f"<read2 {sample.sample_type}>"] = f"{sample.bam}.bai"
    elif starting_run_from == "vcf":
        if not sample.vcf:
            logger.error(f"Start run from vcf but vcf is missing")
            sys.exit(1)
        replace_map[f"<read1 {sample.sample_type}>"] = sample.vcf
        replace_map[f"<read2 {sample.sample_type}>"] = f"{sample.vcf}.bai"
    else:
        raise ValueError(f"start_run_from should be fq, bam or vcf, found: '{starting_run_from}'")

    if case_type == "trio":
        type_to_id = dict(zip(all_sample_types, all_sample_ids))
        replace_map["<father>"] = type_to_id["father"]
        replace_map["<mother>"] = type_to_id["mother"]

    return replace_map


def get_csv(
    logger: Logger,
    config: RunConfig,
    run_label: str,
    starting_run_from: str,
    queue: Optional[str],
    assay: str,
    analysis: str,
    csv_base: Path,
) -> str:

    csv_template_name = config.run_profile.csv_template
    csv_template_path = csv_base / csv_template_name

    csv_rows = csv_template_path.read_text().strip().split("\n")
    all_sample_ids = config.run_profile.samples

    csv_header = csv_rows[0]
    csv_body_rows = csv_rows[1:]

    all_sample_ids = config.run_profile.samples
    all_sample_types = config.run_profile.sample_types

    updated_rows = [csv_header]

    for i, row in enumerate(csv_body_rows):

        sample_id = all_sample_ids[i]
        sample = config.all_samples[sample_id]

        replace_map = get_replace_map(
            logger,
            starting_run_from,
            sample,
            run_label,
            config.run_profile.default_panel,
            config.run_profile.case_type,
            all_sample_ids,
            all_sample_types,
        )

        print("replace map", replace_map)

        for key, val in replace_map.items():
            row = row.replace(key, val)

        updated_rows.append(row)

    print("Updated rows")
    print("\n".join(updated_rows))
    print("---")

    return "\n".join(updated_rows)


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
