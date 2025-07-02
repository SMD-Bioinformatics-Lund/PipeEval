import gzip
from pathlib import Path
from typing import TextIO


def get_filehandle(my_file: Path) -> TextIO:
    if my_file.suffix == ".gz":
        in_fh = gzip.open(str(my_file), "rt")
    else:
        in_fh = open(str(my_file), "r")
    return in_fh


def check_valid_file(my_file: Path) -> bool:
    try:
        if my_file.suffix == ".gz":
            with gzip.open(str(my_file), "rt") as fh:
                fh.read(1)
        else:
            with open(str(my_file), "r") as fh:
                fh.read(1)
    except:
        return False
    return True
