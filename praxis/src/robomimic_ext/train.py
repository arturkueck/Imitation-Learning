"""Train registered local algorithms with robomimic's training script."""

import argparse

import robomimic_ext  # noqa: F401 - registers config and algorithm
from robomimic.scripts.train import main


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--name")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    args.algo = None
    main(args)


if __name__ == "__main__":
    cli()
