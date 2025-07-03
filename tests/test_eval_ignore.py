import logging
from pathlib import Path

from pytest import LogCaptureFixture

from commands.eval.classes import PathObj
from commands.eval.main import check_same_files
from commands.eval.util import RunObject
from shared.constants import RUN_ID_PLACEHOLDER


def _collect_paths(base: Path, run_id: str):
    return [
        PathObj(p, run_id, RUN_ID_PLACEHOLDER, base)
        for p in base.rglob("*")
        if p.is_file()
    ]


def test_check_same_files_ignores_paths(caplog: LogCaptureFixture, tmp_path: Path):
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    r1.mkdir()
    r2.mkdir()

    (r1 / "analysis.txt").write_text("a")
    (r1 / "reviewer").mkdir()
    (r1 / "reviewer" / "comment.txt").write_text("c")
    (r2 / "analysis.txt").write_text("a")

    # r1_paths = _collect_paths(r1, "run1")
    # r2_paths = _collect_paths(r2, "run2")

    run_object = RunObject("run1", "run2", r1, r2)

    out = tmp_path / "out.txt"

    with caplog.at_level(logging.INFO):
        check_same_files(run_object, ["reviewer"], out)
        # check_same_files("run1", "run2", r1_paths, r2_paths, ["reviewer"], out)

    text = out.read_text()
    assert "reviewer/comment.txt" not in text
    assert "Ignored" in text
