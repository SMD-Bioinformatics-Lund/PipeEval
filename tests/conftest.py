from configparser import ConfigParser
from pathlib import Path
import textwrap
import pytest


@pytest.fixture()
def base_dir(tmp_path: Path) -> Path:
    base_dir = tmp_path / "results"
    base_dir.mkdir()
    return base_dir


@pytest.fixture()
def basic_config_path(tmp_path: Path, base_dir: Path) -> Path:

    # Setup dummy repository
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / "nextflow.config").write_text("nextflow")

    # Dummy input files
    fastq1 = tmp_path / "r1.fq"
    fastq2 = tmp_path / "r2.fq"
    fastq1.write_text("1")
    fastq2.write_text("2")
    bam = tmp_path / "dummy.bam"
    bam.write_text("bam")
    vcf = tmp_path / "dummy.vcf"
    vcf.write_text("vcf")

    config_text = textwrap.dedent(
        f"""
        [settings]
        start_nextflow_analysis = /usr/bin/env
        log_base_dir = {tmp_path}/log
        trace_base_dir = {tmp_path}/trace
        work_base_dir = {tmp_path}/work
        base = {base_dir}
        repo = {repo_dir}
        runscript = main.nf
        datestamp = false
        singularity_version = 3.8.0
        nextflow_version = 21.10.6
        queue = test
        executor = local
        cluster = local
        container = container.sif
        fq_fw = {fastq1}
        fq_rv = {fastq2}
        bam = {bam}
        vcf = {vcf}

        [test]
        profile = wgs
        trio = false
        case = samplecase
        default_panel = OMIM

        [samplecase]
        id = caseid
        clarity_pool_id = 0
        clarity_sample_id = sample0
        sex = M
        type = proband
        fq_fw = {fastq1}
        fq_rv = {fastq2}
        bam = {bam}
        vcf = {vcf}
        """
    )

    config_path = tmp_path / "config.ini"
    config_path.write_text(config_text)

    return config_path


