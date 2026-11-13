"""Domain objects shared by the parser, the planner and the simulation."""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


class FlyInError(Exception):
    """An error reported to the user with a clear message."""


class ZoneType(Enum):
    """Kind of a zone, which drives the cost of entering it."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass(eq=False)
class Zone:
    """A hub of the network."""

    name: str
    x: int
    y: int
    zone_type: ZoneType
    color: str | None
    max_drones: int
    is_start: bool = False
    is_end: bool = False

    @property
    def cost(self) -> int:
        """Number of turns needed to enter this zone."""
        return 2 if self.zone_type is ZoneType.RESTRICTED else 1

    def can_hold(self, occupants: int) -> bool:
        """Tell whether `occupants` drones fit in this zone."""
        return (self.is_start or self.is_end
                or occupants <= self.max_drones)


@dataclass(eq=False)
class Connection:
    """A bidirectional link between two zones."""

    a: Zone
    b: Zone
    capacity: int

    @property
    def name(self) -> str:
        """Name of the connection, as written in the map."""
        return f"{self.a.name}-{self.b.name}"

    def other(self, zone: Zone) -> Zone:
        """Return the end of the connection that is not `zone`."""
        return self.b if zone is self.a else self.a


class Transit(NamedTuple):
    """A drone in flight on a connection toward a restricted zone."""

    connection: Connection
    destination: Zone


Location = Zone | Transit
Itinerary = list[Location]
Move = tuple[str, Zone]


class Network:
    """The whole graph of zones and connections."""

    def __init__(self, nb_drones: int, zones: list[Zone],
                 connections: list[Connection],
                 start: Zone, end: Zone) -> None:
        """Build the network and its adjacency index."""
        self.nb_drones = nb_drones
        self.zones = zones
        self.start = start
        self.end = end
        self._adjacent: dict[Zone, list[Connection]] = {
            zone: [] for zone in zones}
        for conn in connections:
            self._adjacent[conn.a].append(conn)
            self._adjacent[conn.b].append(conn)

    def moves_from(self, zone: Zone) -> list[tuple[Connection, Zone]]:
        """List the (connection, destination) pairs usable from `zone`."""
        if zone.zone_type is ZoneType.BLOCKED:
            return []
        return [(conn, conn.other(zone)) for conn in self._adjacent[zone]
                if conn.other(zone).zone_type is not ZoneType.BLOCKED]

    def link(self, a: Zone, b: Zone) -> Connection | None:
        """Return the connection between two zones, if any."""
        return next((conn for conn in self._adjacent[a]
                     if conn.other(a) is b), None)
