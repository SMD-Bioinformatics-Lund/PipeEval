import argparse
from pathlib import Path


def main(vcf1: Path, vcf2: Path):
    pass

def main_wrapper(args: argparse.Namespace):
    main(args.vcf1, args.vcf2)

def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--vcf1", required=True)
    parser.add_argument("--vcf2", required=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    main_wrapper(args)
