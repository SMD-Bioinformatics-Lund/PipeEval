import gzip
import logging
from pathlib import Path
from typing import List

import pytest
from pytest import LogCaptureFixture

from commands.eval.classes.helpers import RunSettings
from commands.eval.classes.run_object import RunObject
from commands.eval.main import main


def write_vcf(path: Path, lines: List[str]):
    if path.suffix == ".gz":
        with gzip.open(path, "wt") as fh:
            fh.write("\n".join(lines))
    else:
        with open(path, "w") as fh:
            fh.write("\n".join(lines))


def create_results_dir(base: Path, run_id: str, diff_scores: bool = False):
    vcf_dir = base / "vcf"
    yaml_dir = base / "yaml"
    version_dir = base / "versions"
    qc_dir = base / "qc"
    vcf_dir.mkdir(parents=True)
    yaml_dir.mkdir()
    version_dir.mkdir()
    qc_dir.mkdir()

    snv_vcf = vcf_dir / f"{run_id}.snv.rescored.sorted.vcf.gz"
    score1 = 10
    score2 = 20
    if diff_scores:
        score1 += 5
        score2 += 5

    snv_lines = [
        "##fileformat=VCFv4.2",
        '##INFO=<ID=RankScore,Number=.,Type=String,Description="Rank score">',
        '##INFO=<ID=RankResult,Number=.,Type=String,Description="A|B">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
        f"1\t100\t.\tA\tC\t.\tPASS\tRankScore={run_id}:{score1};RankResult=1|2",
        f"1\t200\t.\tG\tT\t.\tPASS\tRankScore={run_id}:{score2};RankResult=3|4",
    ]
    write_vcf(snv_vcf, snv_lines)

    sv_score = 8
    if diff_scores:
        sv_score += 5

    sv_vcf = vcf_dir / f"{run_id}.sv.scored.vcf"
    sv_lines = [
        "##fileformat=VCFv4.2",
        '##INFO=<ID=END,Number=1,Type=Integer,Description="End position">',
        '##INFO=<ID=RankScore,Number=.,Type=String,Description="Rank score">',
        '##INFO=<ID=RankResult,Number=.,Type=String,Description="A|B">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
        f"1\t300\t.\tN\t<DEL>\t.\tPASS\tEND=310;RankScore={run_id}:{sv_score};RankResult=1|1",
    ]
    write_vcf(sv_vcf, sv_lines)

    with open(yaml_dir / f"{run_id}.yaml", "w") as fh:
        fh.write(f"sample: {run_id}\n")

    with open(version_dir / f"{run_id}.versions.yml", "w") as fh:
        fh.write(f"version: {run_id}\n")

    with open(qc_dir / f"{run_id}.QC", "w") as fh:
        fh.write(f"QC: {run_id}\n")


@pytest.fixture()
def mock_results(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create two result directories with VCFs differing in rank score"""

    results1 = tmp_path / "results1"
    results2 = tmp_path / "results2"

    create_results_dir(results1, "r1")
    create_results_dir(results2, "r2", diff_scores=True)

    outdir = tmp_path / "out"
    outdir.mkdir()

    return results1, results2, outdir


def test_eval_main(
    caplog: LogCaptureFixture,
    mock_results: tuple[Path, Path, Path],
):
    """
    Given a valid dataset, check that the command runs without errors,
    outputs expected files, and do some sanity checking on the score comparisons
    """
    results1, results2, outdir = mock_results

    run_object = RunObject("r1", "r2", results1, results2)
    run_settings = RunSettings("dna-const", score_threshold=17)

    with caplog.at_level(logging.INFO):
        main(run_object, run_settings, None, set(), outdir)

    assert len(caplog.records) > 0, "No logs were captured"
    assert not any(record.levelname == "ERROR" for record in caplog.records)

    expected_files: List[str] = [
        "check_sample_files.txt",
        "scored_snv_presence.txt",
        "scored_snv_above_thres_17.txt",
        "scored_snv_all_diffing.txt",
        "scored_sv_presence.txt",
        "scored_sv_above_thres_17.txt",
        "scored_sv_all_diffing.txt",
        "scout_yaml.diff",
    ]

    for fname in expected_files:
        assert (outdir / fname).exists(), f"Expected file {fname} does not exist"

    # Verify that differences were detected and written to the output files
    snv_score_thres = (
        (outdir / "scored_snv_above_thres_17.txt").read_text().splitlines()
    )
    assert any(
        "G/T" in line for line in snv_score_thres
    ), "Expected SNV difference missing"

    snv_score_all = (outdir / "scored_snv_all_diffing.txt").read_text().splitlines()
    assert len(snv_score_all) == 3

    sv_score = (outdir / "scored_sv_all_diffing.txt").read_text().splitlines()
    assert any("<DEL>" in line for line in sv_score)


def test_reused_score_reports_are_replaced_after_clean_comparison(mock_results):
    results1, results2, outdir = mock_results
    run_object = RunObject("r1", "r2", results1, results2)
    settings = RunSettings("dna-const")
    filenames = ["scored_snv_all_diffing.txt", "scored_snv_above_thres_17.txt"]

    main(run_object, settings, None, {"score_snv"}, outdir)
    assert all(len((outdir / name).read_text().splitlines()) > 1 for name in filenames)

    with gzip.open(results1 / "vcf/r1.snv.rescored.sorted.vcf.gz", "rt") as source:
        lines = source.read().splitlines()
    write_vcf(results2 / "vcf/r2.snv.rescored.sorted.vcf.gz", lines)

    main(run_object, settings, None, {"score_snv"}, outdir)
    for name in filenames:
        lines = (outdir / name).read_text().splitlines()
        assert len(lines) == 1
        assert lines[0].startswith("chr\tpos\tvar\t")


def test_eval_fails_if_requested_vcf_is_missing(mock_results):
    results1, results2, outdir = mock_results
    path = results2 / "vcf/r2.snv.rescored.sorted.vcf.gz"
    path.rename(results2 / "unused.vcf.gz")
    run_object = RunObject("r1", "r2", results1, results2)

    with pytest.raises(ValueError, match="Cannot compare snv VCFs"):
        main(run_object, RunSettings("dna-const"), None, {"score_snv"}, outdir)
