from dataclasses import dataclass
from typing import Dict, List, Optional

from models import Connection, Location, Network, Transit, Zone, ZoneType
from scheduler import Plan


class SimulationError(Exception):
    """Raised when a plan breaks a movement or capacity rule."""


@dataclass(frozen=True)
class Movement:
    """One drone movement printed on a turn line."""

    drone: int
    label: str
    zone: Zone

    def __str__(self) -> str:
        """Format as D<ID>-<zone> or D<ID>-<connection>."""
        return f"D{self.drone}-{self.label}"


class Simulation:
    """Run the plans and produce the movements of every turn."""

    def __init__(self, network: Network) -> None:
        """Keep the network whose rules are enforced."""
        self.network = network

    def run(self, plans: List[Plan]) -> List[List[Movement]]:
        """Replay the plans; raise SimulationError on any rule violation."""
        total = max((plan.arrival for plan in plans), default=0)
        turns: List[List[Movement]] = []
        for turn in range(1, total + 1):
            load: Dict[Connection, int] = {}
            occupancy: Dict[Zone, int] = {}
            moves: List[Movement] = []
            for number, plan in enumerate(plans, 1):
                before, after = plan.location(turn - 1), plan.location(turn)
                used = self._check_step(number, turn, before, after)
                if used is not None:
                    load[used] = load.get(used, 0) + 1
                if after != before:
                    moves.append(self._movement(number, after))
                if isinstance(after, Zone):
                    occupancy[after] = occupancy.get(after, 0) + 1
            self._check_capacities(turn, load, occupancy)
            turns.append(moves)
        for number, plan in enumerate(plans, 1):
            if plan.location(total) is not self.network.end:
                raise SimulationError(f"D{number} never reaches the end")
        return turns

    def _check_step(self, number: int, turn: int, before: Location,
                    after: Location) -> Optional[Connection]:
        """Validate one drone move; return the connection it starts using."""
        who = f"turn {turn}: D{number}"
        if isinstance(before, Transit):
            if after is not before.destination:
                raise SimulationError(f"{who} must arrive on "
                                      f"{before.destination.name}")
            return None
        if after is before:
            return None
        if isinstance(after, Transit):
            conn, dest = after.connection, after.destination
            if (before not in (conn.a, conn.b)
                    or conn.other(before) is not dest
                    or dest.cost != 2):
                raise SimulationError(f"{who} makes an illegal crossing")
            return conn
        conn_used = self.network.link(before, after)
        if (conn_used is None or after.zone_type is ZoneType.BLOCKED
                or after.cost != 1):
            raise SimulationError(
                f"{who} cannot go from {before.name} to {after.name}")
        return conn_used

    @staticmethod
    def _movement(number: int, after: Location) -> Movement:
        """Build the printed movement for a drone that moved."""
        if isinstance(after, Transit):
            return Movement(number, after.connection.name, after.destination)
        return Movement(number, after.name, after)

    @staticmethod
    def _check_capacities(turn: int, load: Dict[Connection, int],
                          occupancy: Dict[Zone, int]) -> None:
        """Check connection loads and zone occupancy at the end of a turn."""
        for conn, count in load.items():
            if count > conn.capacity:
                raise SimulationError(
                    f"turn {turn}: connection {conn.name} is over capacity")
        for zone, count in occupancy.items():
            if not zone.unlimited and count > zone.max_drones:
                raise SimulationError(
                    f"turn {turn}: zone {zone.name} is over capacity")
