from decimal import Decimal
from typing import Generic, List, Optional, Set, Tuple, TypeVar

from shared.util import parse_decimal

T = TypeVar("T")


class Comparison(Generic[T]):

    # After Python 3.7 a @dataclass can be used instead
    def __init__(self, r1: Set[T], r2: Set[T], shared: Set[T]):
        self.r1 = r1
        self.r2 = r2
        self.shared = shared


class ColumnComparison:

    none_present: int
    v1_present: int
    v2_present: int
    both_present: int
    nbr_same: int

    all_numeric: bool
    numeric_pairs: List[Tuple[Decimal, Decimal]]
    categorical_pairs: List[Tuple[str, str]]

    def __str__(self) -> str:
        return f"{self.none_present} {self.v1_present} {self.v2_present} {self.both_present} {self.nbr_same} {self.all_numeric} nbr numeric {len(self.numeric_pairs)}"

    def __init__(self, val_pairs: List[Tuple[Optional[str], Optional[str]]]):

        self.none_present = 0
        self.v1_present = 0
        self.v2_present = 0
        self.both_present = 0
        self.nbr_same = 0
        self.all_numeric = False

        self.numeric_pairs = []
        self.categorical_pairs = []
        self.categorical_pairs: List[Tuple[str, str]] = []

        all_numeric = True

        for v1_val, v2_val in val_pairs:

            if not v1_val and not v2_val:
                self.none_present += 1
            elif not v2_val:
                self.v1_present += 1
            elif not v1_val:
                self.v2_present += 1
            else:
                pair = (v1_val, v2_val)
                self.categorical_pairs.append(pair)

                if all_numeric:
                    d1 = parse_decimal(v1_val)
                    d2 = parse_decimal(v2_val)

                    if d1 is None or d2 is None:
                        all_numeric = False
                    else:
                        self.numeric_pairs.append((d1, d2))

                self.both_present += 1
                if v1_val == v2_val:
                    self.nbr_same += 1
        self.all_numeric = all_numeric


def do_comparison(set_1: Set[T], set_2: Set[T]) -> Comparison[T]:
    """Can compare both str and Path objects, thus the generics"""
    common = set_1 & set_2
    s1_only = set_1 - set_2
    s2_only = set_2 - set_1

    return Comparison(s1_only, s2_only, common)


# FIXME: Cannot deal with non-expected chromosomes
# Think about how to do that
# Everything non-default should be sorted separately starting with a string
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
