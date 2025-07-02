from pathlib import Path


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

        self.is_gzipped = path.suffix.endswith(".gz")

    def exists(self) -> bool:
        return self.real_path.exists()

    def __str__(self) -> str:
        return str(self.relative_path)
