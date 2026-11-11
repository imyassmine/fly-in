"""Colored terminal display of the simulation."""

from typing import Dict, List

from simulation import Movement


class Renderer:
    """Print the turns, coloring each movement with its zone color."""

    CODES: Dict[str, int] = {
        "red": 196, "green": 40, "blue": 33, "yellow": 226, "orange": 208,
        "purple": 129, "brown": 130, "maroon": 88, "gold": 220,
        "darkred": 124, "crimson": 161, "violet": 177, "cyan": 51,
        "lime": 118, "magenta": 201, "gray": 245, "grey": 245,
        "black": 240, "white": 255, "pink": 213,
    }

    def __init__(self, use_color: bool) -> None:
        """Enable or disable ANSI colors."""
        self.use_color = use_color

    def paint(self, move: Movement) -> str:
        """Return the movement text, colored if its zone has a known color."""
        code = self.CODES.get((move.zone.color or "").lower())
        if not self.use_color or code is None:
            return str(move)
        return f"\033[38;5;{code}m{move}\033[0m"

    def render(self, turns: List[List[Movement]]) -> None:
        """Print one line per turn."""
        for moves in turns:
            print(" ".join(self.paint(move) for move in moves))
