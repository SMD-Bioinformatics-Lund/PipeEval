from pathlib import Path
from typing import Optional


class ScorePaths:
    def __init__(
        self,
        label: str,
        outdir: Optional[Path],
        score_threshold: float,
        all_variants: bool,
    ):
        self.presence = outdir / f"scored_{label}_presence.txt" if outdir else None
        self.score_thres = (
            outdir / f"scored_{label}_score_thres_{score_threshold}.txt"
            if outdir
            else None
        )
        self.all_diffing = outdir / f"scored_{label}_score_all.txt" if outdir else None
        self.all = (
            outdir / f"scored_{label}_score_full.txt"
            if outdir and all_variants
            else None
        )
