import logging
from pathlib import Path

from pytest import LogCaptureFixture

from commands.eval.main import check_same_files
from commands.eval.utils import RunObject


def test_check_same_files_ignores_paths(caplog: LogCaptureFixture, tmp_path: Path):
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    r1.mkdir()
    r2.mkdir()

    (r1 / "analysis.txt").write_text("a")
    (r1 / "reviewer").mkdir()
    (r1 / "reviewer" / "comment.txt").write_text("c")
    (r2 / "analysis.txt").write_text("a")

    run_object = RunObject("run1", "run2", r1, r2)

    out = tmp_path / "out.txt"

    with caplog.at_level(logging.INFO):
        check_same_files(run_object, ["reviewer"], out)

    text = out.read_text()
    assert "reviewer/comment.txt" not in text
    assert "Ignored" in text
