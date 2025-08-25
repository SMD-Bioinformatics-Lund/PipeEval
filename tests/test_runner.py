import csv
import logging
from configparser import ConfigParser
from pathlib import Path
import sys

from pytest import MonkeyPatch

from commands.run import main as run_main
from commands.run.help_classes.config_classes import RunConfig
from tests.conftest import RunConfigs
from tests.conftest_utils.run_configs import ConfigSamplePathGroup

LOG = logging.getLogger()


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
    "read1",
    "read2",
    "analysis",
    "priority",
]


def test_single_run(monkeypatch: MonkeyPatch, base_dir: Path, run_config_paths: RunConfigs, config_sample_paths: ConfigSamplePathGroup):

    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_config = RunConfig(
        LOG, "single", run_config_paths.run_profile, run_config_paths.pipeline_settings, run_config_paths.samples
    )

    run_main.main(
        run_config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        stub_run=True,
        run_profile=run_config.run_profile.profile,
        skip_confirmation=True,
        queue=None,
        no_start=True,
        datestamp=False,
        verbose=False,
        assay=None,
        analysis=None,
    )

    run_label = "wgs-label-testcheckout-stub-fq"

    result_dir = base_dir / run_label

    assert (result_dir / "run.log").exists()
    assert (result_dir / "nextflow.config").exists()

    run_csv = result_dir / "run.csv"
    assert (run_csv).exists()

    with open(run_csv, newline="") as csv_fh:
        reader = csv.DictReader(csv_fh)
        assert reader.fieldnames == WGS_CSV_HEADERS
        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert row["id"] == "s_proband"
        assert row["type"] == "single"
        assert row["sex"] == "M"
        assert row["assay"] == "dev"
        assert row["diagnosis"] == "OMIM"
        assert row["group"] == run_label
        assert row["father"] == "0"
        assert row["mother"] == "0"
        assert str(row["read1"]) == str(config_sample_paths.proband.fq_fw)
        assert str(row["read2"]) == str(config_sample_paths.proband.fq_rv)


def test_duo_run(monkeypatch: MonkeyPatch, base_dir: Path, run_config_paths: RunConfigs):

    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_config = RunConfig(
        LOG, "duo", run_config_paths.run_profile, run_config_paths.pipeline_settings, run_config_paths.samples
    )

    run_main.main(
        run_config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        stub_run=True,
        run_profile=run_config.run_profile.profile,
        skip_confirmation=True,
        queue=None,
        no_start=True,
        datestamp=False,
        verbose=False,
        assay=None,
        analysis=None,
    )

    result_dir = base_dir / "wgs-label-testcheckout-stub-fq"

    assert (result_dir / "run.log").exists()
    assert (result_dir / "run.csv").exists()
    assert (result_dir / "nextflow.config").exists()


def test_trio_run(monkeypatch: MonkeyPatch, base_dir: Path, run_config_paths: RunConfigs):

    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_config = RunConfig(
        LOG, "trio", run_config_paths.run_profile, run_config_paths.pipeline_settings, run_config_paths.samples
    )

    run_main.main(
        run_config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        stub_run=True,
        run_profile=run_config.run_profile.profile,
        skip_confirmation=True,
        queue=None,
        no_start=True,
        datestamp=False,
        verbose=False,
        assay=None,
        analysis=None,
    )

    result_dir = base_dir / "wgs-label-testcheckout-stub-fq"

    assert (result_dir / "run.log").exists()
    assert (result_dir / "run.csv").exists()
    assert (result_dir / "nextflow.config").exists()


def test_override_assay(monkeypatch: MonkeyPatch, base_dir: Path, run_config_paths: RunConfigs):

    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_config = RunConfig(
        LOG, "trio", run_config_paths.run_profile, run_config_paths.pipeline_settings, run_config_paths.samples
    )

    run_main.main(
        run_config,
        label="label",
        checkout="testcheckout",
        base_dir=None,
        repo=None,
        start_data="fq",
        stub_run=True,
        run_profile=run_config.run_profile.profile,
        skip_confirmation=True,
        queue=None,
        no_start=True,
        datestamp=False,
        verbose=False,
        assay="prod",
        analysis="analysis_test",
    )

    result_dir = base_dir / "wgs-label-testcheckout-stub-fq"
    with open(result_dir / "run.csv", "r") as fh:
        lines = fh.read().splitlines()
    assert lines[1].split(",")[4] == "prod"
    assert lines[1].split(",")[14] == "analysis_test"
