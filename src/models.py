from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque, Dict, List, Optional, Set, Tuple, Union


class ZoneType(Enum):
    """Kind of a zone, which drives the cost of entering it."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone:
    """A hub of the network."""

    def __init__(self, name: str, x: int, y: int, zone_type: ZoneType,
                 color: Optional[str], max_drones: int,
                 is_start: bool = False, is_end: bool = False) -> None:
        """Create a zone.

        Args:
            name: Unique zone name.
            x: Integer x coordinate.
            y: Integer y coordinate.
            zone_type: Kind of zone.
            color: Optional color name used by the display.
            max_drones: Maximum number of drones present at the same time.
            is_start: True for the start hub.
            is_end: True for the end hub.
        """
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones
        self.is_start = is_start
        self.is_end = is_end

    @property
    def cost(self) -> int:
        """Number of turns needed to enter this zone."""
        return 2 if self.zone_type is ZoneType.RESTRICTED else 1

    @property
    def unlimited(self) -> bool:
        """Start and end hubs have no capacity limit."""
        return self.is_start or self.is_end

    def has_room(self, occupants: int) -> bool:
        """Tell whether one more drone fits next to `occupants` drones."""
        return self.unlimited or occupants < self.max_drones


class Connection:
    """A bidirectional link between two zones."""

    def __init__(self, a: Zone, b: Zone, capacity: int) -> None:
        """Create a connection named after its two ends, as in the map."""
        self.a = a
        self.b = b
        self.capacity = capacity
        self.name = f"{a.name}-{b.name}"

    def other(self, zone: Zone) -> Zone:
        """Return the end of the connection that is not `zone`."""
        return self.b if zone is self.a else self.a


@dataclass(frozen=True)
class Transit:
    """A drone in flight on a connection toward a restricted zone."""

    connection: Connection
    destination: Zone


Location = Union[Zone, Transit]


class Network:
    """The whole graph of zones and connections."""

    def __init__(self, nb_drones: int, zones: List[Zone],
                 connections: List[Connection],
                 start: Zone, end: Zone) -> None:
        """Build the network and its adjacency index."""
        self.nb_drones = nb_drones
        self.zones = zones
        self.connections = connections
        self.start = start
        self.end = end
        self._adjacent: Dict[Zone, List[Connection]] = {z: [] for z in zones}
        self._links: Dict[Tuple[Zone, Zone], Connection] = {}
        for conn in connections:
            self._adjacent[conn.a].append(conn)
            self._adjacent[conn.b].append(conn)
            self._links[(conn.a, conn.b)] = conn
            self._links[(conn.b, conn.a)] = conn

    def moves_from(self, zone: Zone) -> List[Tuple[Connection, Zone]]:
        """List the (connection, destination) pairs usable from `zone`."""
        moves = []
        for conn in self._adjacent[zone]:
            dest = conn.other(zone)
            if dest.zone_type is not ZoneType.BLOCKED:
                moves.append((conn, dest))
        return moves

    def link(self, a: Zone, b: Zone) -> Optional[Connection]:
        """Return the connection between two zones, if any."""
        return self._links.get((a, b))

    def has_route(self) -> bool:
        """Tell whether the end hub can be reached from the start hub."""
        if self.start.zone_type is ZoneType.BLOCKED:
            return False
        seen: Set[Zone] = {self.start}
        queue: Deque[Zone] = deque([self.start])
        while queue:
            zone = queue.popleft()
            if zone is self.end:
                return True
            for _, dest in self.moves_from(zone):
                if dest not in seen:
                    seen.add(dest)
                    queue.append(dest)
        return False
