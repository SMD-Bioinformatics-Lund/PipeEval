from typing import List


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
    ):
        self.pipeline = pipeline
        self.score_threshold = score_threshold
        self.max_display = max_display
        self.verbose = verbose
        self.max_checked_annots = max_checked_annots
        self.show_line_numbers = show_line_numbers
        self.annotation_info_keys = extra_annot_keys
        self.output_all_variants = output_all_variants
