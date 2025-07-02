from typing import Generic, Set, Tuple, TypeVar

T = TypeVar("T")


class Comparison(Generic[T]):

    # After Python 3.7 a @dataclass can be used instead
    def __init__(self, r1: Set[T], r2: Set[T], shared: Set[T]):
        self.r1 = r1
        self.r2 = r2
        self.shared = shared


def do_comparison(set_1: Set[T], set_2: Set[T]) -> Comparison[T]:
    """Can compare both str and Path objects, thus the generics"""
    common = set_1 & set_2
    s1_only = set_1 - set_2
    s2_only = set_2 - set_1

    return Comparison(s1_only, s2_only, common)


def parse_var_key_for_sort(entry: str) -> Tuple[int, int]:
    chrom, pos = entry.split("_")[0:2]
    # If prefixed with chr, remove it
    if chrom.startswith("chr"):
        chrom = chrom.replace("chr", "")
    chrom_map = {"X": 24, "Y": 25, "M": 26, "MT": 26}
    if chrom in chrom_map:
        chrom_numeric = chrom_map[chrom]
    else:
        try:
            chrom_numeric = int(chrom)
        except ValueError:
            raise ValueError(f"Unexpected chromosome format: {chrom}")
    return chrom_numeric, int(pos)
