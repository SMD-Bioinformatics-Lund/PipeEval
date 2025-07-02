import logging
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
            annotations,
        )

    assert len(caplog.records) > 0, "No logs were captured"

    assert not any(
        record.levelname == "ERROR" for record in caplog.records
    ), "Error logs were captured"

    expected_files = ["above_thres.txt", "score_all.txt"]

    for filename in expected_files:
        file_path = results / filename
        assert file_path.exists(), f"Expected file {filename} does not exist"
