import logging
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
    return Path("tests/testdata/output/scored_snv_all.txt")


def test_main(caplog: LogCaptureFixture, tmp_path: Path):

    vcf1_path = Path("tests/testdata/hg002_chr21.vcf.gz")
    vcf2_path = Path("tests/testdata/hg004_chr21.vcf.gz")

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
            max_display,
            max_checked_annots,
            score_threshold,
            run_id1,
            run_id2,
            results,
            annotations,
            output_all_variants=True,
            comparisons=set(),
            custom_info_keys=set(),
        )

    assert len(caplog.records) > 0, "No logs were captured"

    assert not any(
        record.levelname == "ERROR" for record in caplog.records
    ), "Error logs were captured"

    expected_files = [
        "scored_snv_above_thres_17.txt",
        "scored_snv_presence.txt",
        "scored_snv_all_diffing.txt",
    ]

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


def _write_vcf(path: Path, lines: List[str]) -> None:
    path.write_text("\n".join(lines))


def test_vcf_filter_sample_and_custom_info(tmp_path: Path, caplog: LogCaptureFixture):
    """Create minimal VCFs to exercise filter, sample (FORMAT), and custom INFO comparisons."""

    # Minimal headers with INFO and FORMAT definitions
    header = [
        "##fileformat=VCFv4.2",
        '##INFO=<ID=RankScore,Number=1,Type=String,Description="Rank score">',
        '##INFO=<ID=MYNUM,Number=1,Type=String,Description="Numeric test field">',
        '##INFO=<ID=MYSTAT,Number=1,Type=String,Description="Categorical test field">',
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
    ]

    # Shared variants across both VCFs with differences in FILTER, SAMPLE and INFO
    v1_body = [
        # pos 100: differing MYNUM and MYSTAT, DP differs; FILTER PASS
        "1\t100\t.\tA\tC\t.\tPASS\tRankScore=r1:10;MYNUM=1.0;MYSTAT=YES\tGT:DP\t0/1:10",
        # pos 200: differing FILTER; DP identical; custom info identical
        "1\t200\t.\tG\tT\t.\tLowQual\tRankScore=r1:12;MYNUM=3.0;MYSTAT=LOW\tGT:DP\t0/1:20",
        # pos 300: only present to ensure multiple entries
        "1\t300\t.\tC\tG\t.\tPASS\tRankScore=r1:8;MYNUM=5.0;MYSTAT=MID\tGT:DP\t0/0:5",
    ]
    v2_body = [
        # pos 100 counterpart
        "1\t100\t.\tA\tC\t.\tPASS\tRankScore=r2:11;MYNUM=2.0;MYSTAT=NO\tGT:DP\t0/1:15",
        # pos 200 counterpart with PASS (filter difference) and GT difference
        "1\t200\t.\tG\tT\t.\tPASS\tRankScore=r2:14;MYNUM=3.0;MYSTAT=LOW\tGT:DP\t0/0:20",
        # pos 300 counterpart
        "1\t300\t.\tC\tG\t.\tPASS\tRankScore=r2:9;MYNUM=5.0;MYSTAT=MID\tGT:DP\t0/0:7",
    ]

    vcf1 = tmp_path / "t1.vcf"
    vcf2 = tmp_path / "t2.vcf"
    _write_vcf(vcf1, header + v1_body)
    _write_vcf(vcf2, header + v2_body)

    outdir = tmp_path / "out"
    outdir.mkdir()

    with caplog.at_level(logging.INFO):
        main(
            vcf1,
            vcf2,
            max_display=10,
            max_checked_annots=100,
            score_threshold=17,
            run_id1="t1",
            run_id2="t2",
            results_folder=outdir,
            extra_annot_keys=[],
            output_all_variants=False,
            comparisons={"filter", "sample", "custom_info"},
            custom_info_keys={"MYNUM", "MYSTAT"},
        )

    # Basic sanity: no errors in logs
    assert len(caplog.records) > 0, "No logs were captured"
    assert not any(record.levelname == "ERROR" for record in caplog.records)

    # Verify filter comparison ran and reported categories
    text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "### Checking filter differences ###" in text
    assert "Comparing filter differences" in text
    assert "PASS" in text and "LowQual" in text

    # Verify sample comparison ran; numeric summary for DP and categorical for GT
    assert "### Checking sample differences ###" in text
    assert "Sample field: DP" in text
    assert "DP (numeric)" in text or "(numeric)" in text
    assert "Sample field: GT" in text

    # Verify custom info comparisons ran for both keys
    assert "### Checking custom info keys ###" in text
    assert "MYNUM" in text and "(numeric)" in text
    assert "MYSTAT" in text and "present in both" in text
