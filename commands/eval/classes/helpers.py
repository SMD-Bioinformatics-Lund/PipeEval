from pathlib import Path
from typing import List, Set

from shared.compare import Comparison
from shared.vcf.vcf import ScoredVCF


class VCFPair:
    vcf1: ScoredVCF
    vcf2: ScoredVCF
    comp: Comparison[str]

    def __init__(self, vcf1: ScoredVCF, vcf2: ScoredVCF, comp: Comparison[str]):
        self.vcf1 = vcf1
        self.vcf2 = vcf2
        self.comp = comp


class RunSettings:
    def __init__(
        self,
        pipeline: str,
        score_threshold: int = 17,
        max_display: int = 10,
        verbose: bool = False,
        max_checked_annots: int = 10,
        show_line_numbers: bool = False,
        extra_annot_keys: List[str] = [],
        output_all_variants: bool = False,
        custom_info_keys_snv: Set[str] = set(),
        custom_info_keys_sv: Set[str] = set(),
    ):
        self.pipeline = pipeline
        self.score_threshold = score_threshold
        self.max_display = max_display
        self.verbose = verbose
        self.max_checked_annots = max_checked_annots
        self.show_line_numbers = show_line_numbers
        self.annotation_info_keys = extra_annot_keys
        self.output_all_variants = output_all_variants
        self.custom_info_keys_snv = custom_info_keys_snv
        self.custom_info_keys_sv = custom_info_keys_sv


class PathObj:
    """
    Extended Path object to make comparison between results dir more convenient.

    1. Relative paths to the base dir
    2. Can replace the run ID with the string 'RUNID'
    3. Can detect whether a file is text or gzip
    """

    def __init__(
        self,
        path: Path,
        run_id: str,
        id_placeholder: str,
        base_dir: Path,
    ):
        self.real_name = path.name
        self.real_path = path

        self.shared_name = path.name.replace(run_id, id_placeholder)
        self.shared_path = path.with_name(self.shared_name)
        self.relative_path = self.shared_path.relative_to(base_dir)

        self.run_id = run_id
        self.id_placeholder = id_placeholder

        self.is_gzipped = path.suffix == ".gz"

    def exists(self) -> bool:
        return self.real_path.exists()

    def __str__(self) -> str:
        return str(self.relative_path)
