from pathlib import Path

from util.file import get_filehandle

def count_variants(vcf: Path) -> int:

    nbr_entries = 0
    with get_filehandle(vcf) as in_fh:
        for line in in_fh:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            nbr_entries += 1

    return nbr_entries

