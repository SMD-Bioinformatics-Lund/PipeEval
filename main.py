#!/usr/bin/env python3

import argparse
import sys

from runner.runner import add_arguments as runner_add_arguments
from runner.runner import main_wrapper as runner_main_wrapper
from evaluator.evaluator import add_arguments as eval_add_arguments
from evaluator.evaluator import main_wrapper as eval_main_wrapper


__version_info__ = ("1", "0", "0")
__version__ = ".".join(__version_info__)


def main():
    args = parse_arguments()

    if args.subcommand == "run":
        runner_main_wrapper(args)
    elif args.subcommand == "eval":
        eval_main_wrapper(args)
    else:
        raise ValueError(f"Unknown sub command: {args.subcommand}. Check valid commands by running main.py --help")


def parse_arguments():
    parent_parser = argparse.ArgumentParser(description="PipeEval provides tools to run and assess differences between runs in pipelines")
    parent_parser.add_argument(
        "--version", action="version", version=f"%(prog)s ({__version__})"
    )
    subparsers = parent_parser.add_subparsers(dest="subcommand")

    run_parser = subparsers.add_parser("run", description="Runs a pipeline.")
    runner_add_arguments(run_parser)
    eval_parser = subparsers.add_parser("eval", description="Takes two sets of results and generates a comparison")
    eval_add_arguments(eval_parser)

    args = parent_parser.parse_args()

    if args.subcommand is None:
        parent_parser.print_help()
        sys.exit(1)

    return args


if __name__ == "__main__":
    main()
