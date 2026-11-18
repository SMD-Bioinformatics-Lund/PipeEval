import csv
import logging
import shlex
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from commands.run import main as run_main
from commands.run.help_classes.config_classes import RunConfig
from tests.conftest import RunConfigs
from tests.conftest_utils.run_configs import ConfigSamplePathGroup

LOG = logging.getLogger()


RNASEQ_CONST_CSV_HEADERS = [
    "sample",
    "case",
    "fastq_1",
    "fastq_2",
    "strandedness",
    "sex",
    "phenotype",
    "assay",
    "group",
]

WGS_CSV_HEADERS = [
    "clarity_sample_id",
    "id",
    "type",
    "sex",
    "assay",
    "diagnosis",
    "phenotype",
    "group",
    "father",
    "mother",
    "clarity_pool_id",
    "platform",
    "sequencing_run",
    "read1",
    "read2",
    "analysis",
    "priority",
]

SOMATIC_CSV_HEADERS = [
    "clarity_sample_id",
    "id",
    "type",
    "assay",
    "diagnosis",
    "group",
    "clarity_pool_id",
    "platform",
    "sequencing_run",
    "n_reads",
    "read1",
    "read2",
    "ffpe",
]


@pytest.fixture
def csv_base() -> Path:
    parent_path = Path(__file__).resolve().parent
    csv_base = parent_path.parent / "commands" / "run" / "config" / "csv_templates"
    return csv_base


@pytest.fixture
def mock_pipeline_checkout(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *args: None)
    monkeypatch.setattr(
        run_main, "get_git_commit_hash_and_log", lambda *args: ("abcd", "abcd")
    )
    monkeypatch.setattr(
        run_main, "create_revision_worktree", lambda logger, repo, *args: repo
    )


def test_single_dna_const_run(
    monkeypatch: MonkeyPatch,
    base_dir: Path,
    get_run_config_paths: RunConfigs,
    config_sample_paths: ConfigSamplePathGroup,
    csv_base: Path,
    mock_pipeline_checkout,
):
    paths = config_sample_paths

    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)

    run_config = RunConfig(
        LOG,
        "dna_single_const",
        get_run_config_paths.run_profile,
        get_run_config_paths.pipeline_settings,
        get_run_config_paths.samples,
    )

    run_main.main(
        run_config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        stub_run=True,
        run_profile=run_config.run_profile.run_profile,
        skip_confirmation=True,
        no_start=True,
        datestamp=False,
        verbose=False,
        assay=None,
        analysis=None,
        csv_base=csv_base,
        remote_name="origin",
    )

    run_label = "dna_single_const-label-testcheckout-stub-fq"

    result_dir = base_dir / run_label

    assert (result_dir / "run.log").exists()
    assert (result_dir / "nextflow.config").exists()

    run_csv = result_dir / "run.csv"
    assert (run_csv).exists()

    with open(run_csv, newline="") as csv_fh:
        reader = csv.DictReader(csv_fh)
        assert reader.fieldnames
        for i in range(len(reader.fieldnames)):
            assert (
                reader.fieldnames[i] == WGS_CSV_HEADERS[i]
            ), f"Fieldname in pos {i} should match expected"
        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "s_proband"
        assert row["type"] == "proband"
        assert row["sex"] == "M"
        assert row["assay"] == "dev"
        assert row["diagnosis"] == "itchy_nose"
        assert row["group"] == run_label
        assert row["father"] == ""
        assert row["mother"] == ""
        assert str(row["read1"]) == str(paths.proband.fq_fw)
        assert str(row["read2"]) == str(paths.proband.fq_rv)


def test_single_rna_const_run(
    monkeypatch: MonkeyPatch,
    base_dir: Path,
    get_run_config_paths: RunConfigs,
    config_sample_paths: ConfigSamplePathGroup,
    csv_base: Path,
    mock_pipeline_checkout,
):
    paths = config_sample_paths

    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)

    run_config = RunConfig(
        LOG,
        "rna_single_const",
        get_run_config_paths.run_profile,
        get_run_config_paths.pipeline_settings,
        get_run_config_paths.samples,
    )

    run_main.main(
        run_config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        stub_run=True,
        run_profile=run_config.run_profile.run_profile,
        skip_confirmation=True,
        no_start=True,
        datestamp=False,
        verbose=False,
        assay=None,
        analysis=None,
        csv_base=csv_base,
        remote_name="origin",
    )

    run_label = "rna_single_const-label-testcheckout-stub-fq"

    result_dir = base_dir / run_label

    assert (result_dir / "run.log").exists()
    assert (result_dir / "nextflow.config").exists()
    assert (result_dir / "child_nextflow.config").exists()

    run_csv = result_dir / "run.csv"
    assert (run_csv).exists()

    with open(run_csv, newline="") as csv_fh:
        reader = csv.DictReader(csv_fh)
        assert reader.fieldnames
        for i in range(len(reader.fieldnames)):
            assert (
                reader.fieldnames[i] == RNASEQ_CONST_CSV_HEADERS[i]
            ), f"Fieldname in pos {i} should match expected. Expected {reader.fieldnames[i]} found {WGS_CSV_HEADERS[i]}"

        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert row["sample"] == "s_rna"
        assert row["case"] == run_label
        assert str(row["fastq_1"]) == str(paths.rna.fq_fw)
        assert str(row["fastq_2"]) == str(paths.rna.fq_rv)
        assert row["strandedness"] == "reverse"
        assert row["sex"] == "M"
        assert row["phenotype"] == "2"


def test_paired_tumor_run(
    monkeypatch: MonkeyPatch,
    base_dir: Path,
    get_run_config_paths: RunConfigs,
    config_sample_paths: ConfigSamplePathGroup,
    csv_base: Path,
    mock_pipeline_checkout,
):

    paths = config_sample_paths
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)

    run_config = RunConfig(
        LOG,
        "somatic",
        get_run_config_paths.run_profile,
        get_run_config_paths.pipeline_settings,
        get_run_config_paths.samples,
    )

    run_main.main(
        run_config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        stub_run=True,
        run_profile=run_config.run_profile.run_profile,
        skip_confirmation=True,
        no_start=True,
        datestamp=False,
        verbose=False,
        assay=None,
        analysis=None,
        csv_base=csv_base,
        remote_name="origin",
    )

    run_label = "somatic-label-testcheckout-stub-fq"
    result_dir = base_dir / run_label

    assert (result_dir / "run.log").exists()
    assert (result_dir / "nextflow.config").exists()

    run_csv = result_dir / "run.csv"
    assert (run_csv).exists()

    with open(run_csv, newline="") as csv_fh:
        reader = csv.DictReader(csv_fh)
        assert reader.fieldnames == SOMATIC_CSV_HEADERS
        rows = list(reader)
        assert len(rows) == 2

        diagnosis = "other"
        assay = "tumwgs-hema"

        pb_row = rows[0]
        assert pb_row["id"] == "s_normal"
        assert pb_row["type"] == "N"
        assert pb_row["assay"] == assay
        assert pb_row["diagnosis"] == diagnosis
        assert pb_row["group"] == run_label
        assert str(pb_row["read1"]) == str(paths.normal.fq_fw)
        assert str(pb_row["read2"]) == str(paths.normal.fq_rv)

        mother_row = rows[1]
        assert mother_row["id"] == "s_tumor"
        assert mother_row["type"] == "T"
        assert mother_row["assay"] == assay
        assert mother_row["diagnosis"] == diagnosis
        assert mother_row["group"] == run_label
        assert str(mother_row["read1"]) == str(paths.tumor.fq_fw)
        assert str(mother_row["read2"]) == str(paths.tumor.fq_rv)


def test_trio_run(
    monkeypatch: MonkeyPatch,
    base_dir: Path,
    get_run_config_paths: RunConfigs,
    config_sample_paths: ConfigSamplePathGroup,
    csv_base: Path,
    mock_pipeline_checkout,
):

    paths = config_sample_paths

    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)

    run_config = RunConfig(
        LOG,
        "dna_trio_const",
        get_run_config_paths.run_profile,
        get_run_config_paths.pipeline_settings,
        get_run_config_paths.samples,
    )

    run_main.main(
        run_config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        stub_run=True,
        run_profile="trio",
        skip_confirmation=True,
        no_start=True,
        datestamp=False,
        verbose=False,
        assay=None,
        analysis=None,
        csv_base=csv_base,
        remote_name="origin",
    )

    run_label = "trio-label-testcheckout-stub-fq"
    result_dir = base_dir / run_label

    assert (result_dir / "run.log").exists()
    assert (result_dir / "nextflow.config").exists()

    run_csv = result_dir / "run.csv"
    assert (run_csv).exists()

    with open(run_csv, newline="") as csv_fh:
        reader = csv.DictReader(csv_fh)
        assert reader.fieldnames == WGS_CSV_HEADERS
        rows = list(reader)
        assert len(rows) == 3

        pb_row = rows[0]
        assert pb_row["id"] == "s_proband"
        assert pb_row["type"] == "proband"
        assert pb_row["sex"] == "M"
        assert pb_row["assay"] == "dev"
        assert pb_row["diagnosis"] == "stiff_neck"
        assert pb_row["group"] == run_label
        assert pb_row["father"] == "s_father"
        assert pb_row["mother"] == "s_mother"
        assert str(pb_row["read1"]) == str(paths.proband.fq_fw)
        assert str(pb_row["read2"]) == str(paths.proband.fq_rv)

        mother_row = rows[1]
        assert mother_row["id"] == "s_mother"
        assert mother_row["type"] == "relative"
        assert mother_row["sex"] == "F"
        assert mother_row["assay"] == "dev"
        assert mother_row["diagnosis"] == "stiff_neck"
        assert mother_row["group"] == run_label
        assert mother_row["father"] == ""
        assert mother_row["mother"] == ""
        assert str(mother_row["read1"]) == str(paths.mother.fq_fw)
        assert str(mother_row["read2"]) == str(paths.mother.fq_rv)

        father_row = rows[2]
        assert father_row["id"] == "s_father"
        assert father_row["type"] == "relative"
        assert father_row["sex"] == "M"
        assert father_row["assay"] == "dev"
        assert father_row["diagnosis"] == "stiff_neck"
        assert father_row["group"] == run_label
        assert father_row["father"] == ""
        assert father_row["mother"] == ""
        assert str(father_row["read1"]) == str(paths.father.fq_fw)
        assert str(father_row["read2"]) == str(paths.father.fq_rv)


def test_run_and_resume_use_the_recorded_revision(
    monkeypatch: MonkeyPatch,
    base_dir: Path,
    get_run_config_paths: RunConfigs,
    csv_base: Path,
):
    config_paths = get_run_config_paths
    config = RunConfig(
        LOG,
        "dna_single_const",
        config_paths.run_profile,
        config_paths.pipeline_settings,
        config_paths.samples,
    )
    repo = Path(config.general_settings.repo)

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE, text=True
        ).stdout.strip()

    git("init", "-q")
    git("remote", "add", "origin", ".")
    script = repo / "main.nf"
    nextflow_config = repo / "nextflow.config"
    script.write_text("first script\n")
    nextflow_config.write_text("first config\n")
    git("add", "main.nf", "nextflow.config")
    git(
        "-c",
        "user.name=PipeEval test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "First revision",
    )
    first = git("rev-parse", "HEAD")
    script.write_text("second script\n")
    nextflow_config.write_text("second config\n")
    git("add", "main.nf", "nextflow.config")
    git(
        "-c",
        "user.name=PipeEval test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "Second revision",
    )
    second = git("rev-parse", "HEAD")
    git("checkout", "-q", "--detach", first)
    script.write_text("dirty script\n")
    nextflow_config.write_text("dirty config\n")

    commands = []
    monkeypatch.setattr(
        run_main, "start_run", lambda args, confirmation: commands.append(args)
    )
    run_main.main(
        config,
        None,
        first,
        base_dir,
        repo,
        "fq",
        False,
        "dna_single_const",
        True,
        False,
        False,
        False,
        None,
        None,
        csv_base,
        "origin",
    )

    result = base_dir / f"dna_single_const-{first}-fq"
    (launch,) = commands

    def assert_revision(command):
        pipeline = shlex.split(command[command.index("--pipeline") + 1])
        flags = shlex.split(command[command.index("--custom_flags") + 1])
        assert Path(pipeline[0]).read_text() == "first script\n"
        assert Path(flags[1]).read_text() == "first config\n"
        assert (result / "nextflow.config").read_text() == "first config\n"
        assert f"commit hash: {first}" in (result / "run.log").read_text()

    assert_revision(launch)
    assert script.read_text() == "dirty script\n"
    script.write_text("first script\n")
    nextflow_config.write_text("first config\n")
    git("checkout", "-q", "--detach", second)
    resume = shlex.split((result / "resume.sh").read_text())
    assert resume == launch + ["--resume"]
    assert_revision(resume)
