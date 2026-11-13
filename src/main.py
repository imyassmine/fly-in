import os, sys
from typing import List

from display import Renderer
from parser import MapParser, ParseError
from scheduler import Planner, PlanningError
from simulation import Simulation, SimulationError


class FlyInApp:
    """Command line application tying parser, planner and display."""

    def run(self, argv: List[str]) -> int:
        """Run the simulation on the map given in `argv`; return exit code."""
        if len(argv) != 1:
            print("usage: python3 main.py <map_file>", file=sys.stderr)
            return 2
        try:
            network = MapParser().parse(argv[0])
            if not network.has_route():
                print("Error: no path connects start_hub to end_hub",
                      file=sys.stderr)
                return 1
            plans = Planner(network).plan_all()
            turns = Simulation(network).run(plans)
        except (OSError, ParseError, PlanningError, SimulationError) as err:
            print(f"Error: {err}", file=sys.stderr)
            return 1
        color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        Renderer(color).render(turns)
        print(f"Total turns: {len(turns)}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(FlyInApp().run(sys.argv[1:]))
