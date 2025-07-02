import logging
import subprocess
import sys
from pathlib import Path
from typing import List
from commands.vcf.main import main
from pytest import LogCaptureFixture


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
            annotations
        )

    assert len(caplog.records) > 0, "No logs were captured"

    assert not any(
        record.levelname == "ERROR" for record in caplog.records
    ), "Error logs were captured"

    expected_files = [
        "above_thres.txt",
        "score_all.txt"
    ]

    for filename in expected_files:
        file_path = results / filename
        assert file_path.exists(), f'Expected file {filename} does not exist'


def test_parse_scored_vcf_counts():
    """Verify that the helper used for the vcf command parses files correctly."""

    from shared.vcf.vcf import parse_scored_vcf

    vcf1_path = Path("tests/testdata/hg002_chr21.vcf.gz")
    vcf2_path = Path("tests/testdata/hg004_chr21.vcf.gz")

    vcf1 = parse_scored_vcf(vcf1_path, False)
    vcf2 = parse_scored_vcf(vcf2_path, False)

    assert len(vcf1.variants) == 1779
    assert len(vcf2.variants) == 2194


def test_vcf_cli(tmp_path: Path):
    """Run the vcf command through the main entry point."""

    results = tmp_path / "results"

    cmd = [
        sys.executable,
        "main.py",
        "vcf",
        "-1",
        str(Path("tests/testdata/hg002_chr21.vcf.gz")),
        "-2",
        str(Path("tests/testdata/hg004_chr21.vcf.gz")),
        "--results",
        str(results),
    ]

    completed = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    assert completed.returncode == 0
    assert "Parsing VCFs" in completed.stdout

    for filename in ["above_thres.txt", "score_all.txt", "presence.txt"]:
        file_path = results / filename
        assert file_path.exists(), f"Expected file {filename} does not exist"
