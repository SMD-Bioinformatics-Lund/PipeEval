from configparser import ConfigParser
from pathlib import Path
import logging

from commands.run import main as run_main


def test_basic_run(monkeypatch, tmp_path):
    # Setup dummy repository
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / "nextflow.config").write_text("nextflow")

    base_dir = tmp_path / "results"
    base_dir.mkdir()

    # Dummy input files
    fastq1 = tmp_path / "r1.fq"
    fastq2 = tmp_path / "r2.fq"
    fastq1.write_text("1")
    fastq2.write_text("2")
    bam = tmp_path / "dummy.bam"
    bam.write_text("bam")
    vcf = tmp_path / "dummy.vcf"
    vcf.write_text("vcf")

    config_text = f"""
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

    config = ConfigParser()
    config.read_string(config_text)

    # Patch external interactions
    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_main.main(
        config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        dry_run=False,
        stub_run=True,
        run_type="test",
        skip_confirmation=True,
        queue=None,
        no_start=True,
        datestamp=False,
        verbose=False,
    )

    result_dir = base_dir / "test-label-testcheckout-stub-fq"
    assert (result_dir / "run.log").exists()
    assert (result_dir / "run.csv").exists()
    assert (result_dir / "nextflow.config").exists()
