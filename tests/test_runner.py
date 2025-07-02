from configparser import ConfigParser
from pathlib import Path
import logging

from pytest import MonkeyPatch

from commands.run import main as run_main

LOG = logging.getLogger()

def test_basic_run(monkeypatch: MonkeyPatch, base_dir: Path, basic_config: ConfigParser):

    # Patch external interactions
    monkeypatch.setattr(run_main, "do_repo_checkout", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(run_main, "get_git_commit_hash_and_log", lambda *a, **k: ("abcd", "abcd"))

    run_main.main(
        basic_config,
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
