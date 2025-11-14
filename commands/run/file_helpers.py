import sys
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Dict, List

from commands.run.help_classes.config_classes import (
    RunConfig,
    RunProfileConfig,
    SampleConfig,
)


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
    sample_configs: List[SampleConfig],
    run_label: str,
    run_profile: RunProfileConfig,
) -> Dict[str, str]:
    """
    Used to insert values into template placeholders in the template csv.
    Hard-coded entries are initially retrieved.
    Then, parameters are first retrieved from the run profile config section.
    For instance <default-panel> would be retrieved from corresponding key.
    Finally, parameters are retrieved from sample configs.
    For instance <sex proband> would be retrieved from "sex" attribute.
    Sample type for each sample is defined in the run-profile (as a sample can be a proband or a mother depending on context)
    """

    replace_map = get_replace_map_special_rules(
        logger, run_label, sample_configs, starting_run_from, run_profile.case_type
    )

    # Additional run profile attributes (analysis, default-panel etc)
    for attr, val in run_profile.items():
        placeholder = f"<{attr}>"
        if placeholder not in replace_map:
            replace_map[placeholder] = val

    # Additional sample attributes (sample type, sex etc)
    for sample_config in sample_configs:

        sample_type = sample_config.sample_type
        for attr, val in sample_config.items():
            placeholder = f"<{attr} {sample_type}>"
            if placeholder not in replace_map:
                replace_map[placeholder] = val

    return replace_map


def get_csv(
    logger: Logger,
    config: RunConfig,
    run_label: str,
    starting_run_from: str,
    csv_base: Path,
) -> str:

    csv_template_name = config.run_profile.csv_template
    csv_template_path = csv_base / csv_template_name

    csv_rows = csv_template_path.read_text().strip().split("\n")
    csv_header = csv_rows[0]
    csv_body_rows = csv_rows[1:]

    updated_rows = [csv_header]

    replace_map = get_replace_map(
        logger,
        starting_run_from,
        list(config.all_samples.values()),
        run_label,
        config.run_profile,
    )

    for i, row in enumerate(csv_body_rows):

        for key, val in replace_map.items():
            row = row.replace(key, val)

        updated_rows.append(row)

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


def get_replace_map_special_rules(
    logger: Logger,
    run_label: str,
    sample_configs: List[SampleConfig],
    starting_run_from: str,
    case_type: str,
) -> Dict[str, str]:
    """
    Special rules where values cannot simply be templated from config.
    An unfortunate fact of life. Avoid this if you can.

    Current hard-coded values

    * group - Defaults to the run label
    * read1 and read2 - Can be fastq, bam or vcf, all with the same header in SMDs CSV syntax
    * mother / father in trio - Special link between samples in the trio. Can it be put in config?
    """

    replace_map = {
        "<group>": run_label,
    }

    for sample in sample_configs:

        # This is a custom case needed to accomodate how the Lund DNA constitutional
        # pipeline uses the read1/read2 field to start from various data types
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
                logger.error("Start run from bam but bam is missing")
                sys.exit(1)
            replace_map[f"<read1 {sample.sample_type}>"] = sample.bam
            replace_map[f"<read2 {sample.sample_type}>"] = f"{sample.bam}.bai"
        elif starting_run_from == "vcf":
            if not sample.vcf:
                logger.error("Start run from vcf but vcf is missing")
                sys.exit(1)
            replace_map[f"<read1 {sample.sample_type}>"] = sample.vcf
            replace_map[f"<read2 {sample.sample_type}>"] = f"{sample.vcf}.bai"
        else:
            raise ValueError(
                f"start_run_from should be fq, bam or vcf, found: '{starting_run_from}'"
            )

    # Custom case for trio mode for Lund DNA constitutional pipeline
    if case_type == "trio":
        type_to_id = {}
        for sample in sample_configs:
            type_to_id[sample.sample_type] = sample.id

        replace_map["<father>"] = type_to_id["father"]
        replace_map["<mother>"] = type_to_id["mother"]

    return replace_map
