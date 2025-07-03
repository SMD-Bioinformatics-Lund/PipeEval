#!/usr/bin/env python3

import argparse
import sys

from commands.eval.main import add_arguments as eval_add_arguments
from commands.eval.main import main_wrapper as eval_main_wrapper
from commands.run.main import add_arguments as runner_add_arguments
from commands.run.main import main_wrapper as runner_main_wrapper
from commands.vcf.main import add_arguments as vcf_add_arguments
from commands.vcf.main import main_wrapper as vcf_main_wrapper

__version_info__ = ("1", "3", "1")
__version__ = ".".join(__version_info__)


def main():
    args = parse_arguments()

    if args.subcommand == "run":
        runner_main_wrapper(args)
    elif args.subcommand == "eval":
        eval_main_wrapper(args)
    elif args.subcommand == "vcf":
        vcf_main_wrapper(args)
    else:
        raise ValueError(
            f"Unknown sub command: {args.subcommand}. Check valid commands by running main.py --help"
        )


def parse_arguments():
    parent_parser = argparse.ArgumentParser(
        description="PipeEval provides tools to run and assess differences between runs in pipelines",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parent_parser.add_argument(
        "--version", action="version", version=f"%(prog)s ({__version__})"
    )
    subparsers = parent_parser.add_subparsers(dest="subcommand")

    run_parser = subparsers.add_parser(
        "run",
        description="Runs a pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    runner_add_arguments(run_parser)

    eval_parser = subparsers.add_parser(
        "eval",
        description="Takes two sets of results and generates a comparison",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    eval_add_arguments(eval_parser)

    vcf_parser = subparsers.add_parser(
        "vcf",
        description="Compare two VCFs directly",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    vcf_add_arguments(vcf_parser)

    args = parent_parser.parse_args()

    if args.subcommand is None:
        parent_parser.print_help()
        sys.exit(1)

    return args


if __name__ == "__main__":
    main()
