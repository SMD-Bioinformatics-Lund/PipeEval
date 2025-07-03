import logging
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest
from pytest import LogCaptureFixture

from commands.vcf.main import main

LOG = logging.getLogger(__name__)


@pytest.fixture
def hg002_vcf() -> Path:
    return Path("tests/testdata/hg002_chr21.vcf.gz")


@pytest.fixture
def hg004_vcf() -> Path:
    return Path("tests/testdata/hg004_chr21.vcf.gz")


@pytest.fixture
def results_above_thres() -> Path:
    return Path("tests/testdata/output/scored_snv_above_thres_17.txt")


@pytest.fixture
def results_presence() -> Path:
    return Path("tests/testdata/output/scored_snv_presence.txt")


@pytest.fixture
def results_score_all() -> Path:
    return Path("tests/testdata/output/scored_snv_score_all.txt")


def test_main(caplog: LogCaptureFixture, tmp_path: Path):

    vcf1_path = Path("tests/testdata/hg002_chr21.vcf.gz")
    vcf2_path = Path("tests/testdata/hg004_chr21.vcf.gz")

    is_sv = False
    max_display = 10
    max_checked_annots = 1000
    score_threshold = 17
    run_id1 = "Run ID1"
    run_id2 = "Run ID2"
    results = tmp_path / "results"
    results.mkdir()
    annotations: List[str] = []

    with caplog.at_level(logging.INFO):

        main(
            vcf1_path,
            vcf2_path,
            is_sv,
            max_display,
            max_checked_annots,
            score_threshold,
            run_id1,
            run_id2,
            results,
            annotations,
            output_all_variants=True,
        )

    assert len(caplog.records) > 0, "No logs were captured"

    assert not any(
        record.levelname == "ERROR" for record in caplog.records
    ), "Error logs were captured"

    expected_files = ["above_thres.txt", "score_all.txt", "score_full.txt"]

    for filename in expected_files:
        file_path = results / filename
        assert file_path.exists(), f"Expected file {filename} does not exist"


def test_parse_scored_vcf_counts():
    """Verify that the helper used for the vcf command parses files correctly."""

    from shared.vcf.vcf import parse_scored_vcf

    vcf1_path = Path("tests/testdata/hg002_chr21.vcf.gz")
    vcf2_path = Path("tests/testdata/hg004_chr21.vcf.gz")

    vcf1 = parse_scored_vcf(vcf1_path, False)
    vcf2 = parse_scored_vcf(vcf2_path, False)

    assert len(vcf1.variants) == 1779
    assert len(vcf2.variants) == 2194


def test_vcf_cli(
    tmp_path: Path,
    hg002_vcf: Path,
    hg004_vcf: Path,
    results_above_thres: Path,
    results_presence: Path,
    results_score_all: Path,
):
    """Run the vcf command through the main entry point."""

    results = tmp_path / "results"

    cmd = [
        sys.executable,
        "main.py",
        "vcf",
        "-1",
        str(hg002_vcf),
        "-2",
        str(hg004_vcf),
        "--results",
        str(results),
    ]

    completed = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    assert completed.returncode == 0
    assert "Parsing VCFs" in completed.stdout

    # Could be expanded upon

    above_thres = results / "above_thres.txt"
    LOG.warning(above_thres)
    assert above_thres.exists()
    above_thres_lines = above_thres.read_text().rstrip().split("\n")
    results_above_thres_lines = results_above_thres.read_text().rstrip().split("\n")
    assert len(above_thres_lines) == len(results_above_thres_lines)

    score_all = results / "score_all.txt"
    assert score_all.exists()
    score_all_lines = score_all.read_text().rstrip().split("\n")
    results_score_all_lines = results_score_all.read_text().rstrip().split("\n")
    assert len(score_all_lines) == len(results_score_all_lines)

    presence = results / "presence.txt"
    assert presence.exists()
    presence_lines = presence.read_text().rstrip().split("\n")
    results_presence_lines = results_presence.read_text().rstrip().split("\n")
    assert len(presence_lines) == len(results_presence_lines)
