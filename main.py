#!/usr/bin/env python3
"""Entry point for Siedler — a Settlers IV–like game.

    python3 main.py            # play
    python3 main.py --seed 5   # fixed map seed

Requires pygame:  python3 -m pip install pygame
"""

import argparse
import sys

from siedler.game import Game


def main(argv=None):
    parser = argparse.ArgumentParser(description="Siedler settlement game")
    parser.add_argument("--seed", type=int, default=None,
                        help="map generation seed")
    args = parser.parse_args(argv)

    game = Game(seed=args.seed)
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
