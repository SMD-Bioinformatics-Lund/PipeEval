import logging
from configparser import ConfigParser
from pathlib import Path

from pytest import MonkeyPatch

from commands.run import main as run_main
from commands.run.help_classes.config_classes import RunConfig
from tests.conftest import RunConfigs

LOG = logging.getLogger()


def test_single_run(monkeypatch: MonkeyPatch, base_dir: Path, run_configs: RunConfigs):

    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_config = RunConfig(
        LOG, "single", run_configs.run_profile, run_configs.pipeline_settings, run_configs.samples
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


def test_duo_run(monkeypatch: MonkeyPatch, base_dir: Path, run_configs: RunConfigs):

    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_config = RunConfig(
        LOG, "duo", run_configs.run_profile, run_configs.pipeline_settings, run_configs.samples
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


def test_trio_run(monkeypatch: MonkeyPatch, base_dir: Path, run_configs: RunConfigs):

    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_config = RunConfig(
        LOG, "trio", run_configs.run_profile, run_configs.pipeline_settings, run_configs.samples
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


def test_override_assay(monkeypatch: MonkeyPatch, base_dir: Path, run_configs: RunConfigs):

    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_config = RunConfig(
        LOG, "trio", run_configs.run_profile, run_configs.pipeline_settings, run_configs.samples
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
