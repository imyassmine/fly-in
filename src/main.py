"""Command line entry point and colored rendering."""

import os
import sys

from models import FlyInError, Move
from parser import MapParser
from scheduler import Planner, Simulation


class FlyInApp:
    """Run a map, plan the drones and print the simulation."""

    CODES: dict[str, int] = {
        "red": 196, "green": 40, "blue": 33, "yellow": 226, "orange": 208,
        "purple": 129, "brown": 130, "maroon": 88, "gold": 220,
        "darkred": 124, "crimson": 161, "violet": 177, "cyan": 51,
        "lime": 118, "magenta": 201, "gray": 245, "grey": 245,
        "black": 240, "white": 255, "pink": 213,
    }

    def run(self, argv: list[str]) -> int:
        """Run the simulation on the map given in `argv`; return exit code."""
        if len(argv) != 1:
            print("usage: python3 main.py <map_file>", file=sys.stderr)
            return 2
        try:
            network = MapParser().parse(argv[0])
            plans = Planner(network).plan_all()
            turns = Simulation(network).run(plans)
        except (OSError, FlyInError) as err:
            print(f"Error: {err}", file=sys.stderr)
            return 1
        color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        for moves in turns:
            print(" ".join(self._paint(move, color) for move in moves))
        print(f"Total turns: {len(turns)}", file=sys.stderr)
        return 0

    def _paint(self, move: Move, color: bool) -> str:
        """Return the movement text, colored if requested and known."""
        label, zone = move
        code = self.CODES.get((zone.color or "").lower())
        if not color or code is None:
            return label
        return f"\033[38;5;{code}m{label}\033[0m"


if __name__ == "__main__":
    sys.exit(FlyInApp().run(sys.argv[1:]))
