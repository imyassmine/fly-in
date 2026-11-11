from typing import Dict, List, Optional, Tuple

from models import Connection, Location, Network, Transit, Zone, ZoneType


class PlanningError(Exception):
    """Raised when no itinerary can be found for a drone."""


class Plan:
    """The itinerary of one drone.

    `states[t]` is where the drone is after turn `t` (index 0 is the start).
    `crossings` lists the (turn, connection) pairs where it starts to use a
    connection.
    """

    def __init__(self, states: List[Location],
                 crossings: List[Tuple[int, Connection]]) -> None:
        """Store the states and the crossings."""
        self.states = states
        self.crossings = crossings

    @property
    def arrival(self) -> int:
        """Turn at which the drone reaches the end zone."""
        return len(self.states) - 1

    def location(self, turn: int) -> Location:
        """Where the drone is after `turn` (it stays on the end zone)."""
        return self.states[min(turn, len(self.states) - 1)]


class Reservations:
    """Zone occupancy and connection load already booked, per turn."""

    def __init__(self) -> None:
        """Start with nothing booked."""
        self._zones: Dict[Tuple[int, Zone], int] = {}
        self._links: Dict[Tuple[int, Connection], int] = {}

    def zone_has_room(self, turn: int, zone: Zone) -> bool:
        """Tell whether `zone` can take one more drone after `turn`."""
        return zone.has_room(self._zones.get((turn, zone), 0))

    def link_has_room(self, turn: int, conn: Connection) -> bool:
        """Tell whether `conn` can carry one more drone during `turn`."""
        return self._links.get((turn, conn), 0) < conn.capacity

    def add(self, plan: Plan) -> None:
        """Book everything a plan uses."""
        for turn, loc in enumerate(plan.states):
            if isinstance(loc, Zone):
                key = (turn, loc)
                self._zones[key] = self._zones.get(key, 0) + 1
        for turn, conn in plan.crossings:
            link = (turn, conn)
            self._links[link] = self._links.get(link, 0) + 1


class _Node:
    """A search state: a drone on `zone` after `time` turns."""

    def __init__(self, zone: Zone, time: int, score: Tuple[int, int],
                 parent: Optional["_Node"], conn: Optional[Connection],
                 transit: bool) -> None:
        """Store the state; `transit` marks a restricted 2-turn crossing."""
        self.zone = zone
        self.time = time
        self.score = score
        self.parent = parent
        self.conn = conn
        self.transit = transit


class Planner:
    """Plan every drone on the network, one after the other."""

    def __init__(self, network: Network) -> None:
        """Keep the network to plan on."""
        self.network = network

    def plan_all(self) -> List[Plan]:
        """Return one plan per drone, in drone order."""
        booked = Reservations()
        plans: List[Plan] = []
        latest = 0
        slack = 2 * len(self.network.zones) + 2
        for _ in range(self.network.nb_drones):
            plan = self._plan_one(booked, latest + slack)
            booked.add(plan)
            plans.append(plan)
            latest = max(latest, plan.arrival)
        return plans

    def _plan_one(self, booked: Reservations, horizon: int) -> Plan:
        """Find the earliest arrival given what is already booked.

        Turns are explored one layer at a time, so the first layer holding
        the end zone is the earliest arrival. Ties are broken in favour of
        priority zones, then of waiting on the start zone rather than on
        a zone that other drones may need.
        """
        net = self.network
        layers: List[Dict[Zone, _Node]] = [{} for _ in range(horizon + 3)]
        layers[0][net.start] = _Node(net.start, 0, (0, 0), None, None, False)
        for turn in range(horizon + 1):
            if net.end in layers[turn]:
                return self._build(layers[turn][net.end])
            for node in list(layers[turn].values()):
                self._expand(booked, layers, node)
        raise PlanningError("no itinerary found within the horizon")

    def _expand(self, booked: Reservations,
                layers: List[Dict[Zone, _Node]], node: _Node) -> None:
        """Offer every move a drone can make from `node`."""
        zone, nxt = node.zone, node.time + 1
        prio, waits = node.score
        if booked.zone_has_room(nxt, zone):
            penalty = 0 if zone.is_start else 1
            self._offer(layers[nxt], _Node(
                zone, nxt, (prio, waits - penalty), node, None, False))
        for conn, dest in self.network.moves_from(zone):
            if not booked.link_has_room(nxt, conn):
                continue
            bonus = 1 if dest.zone_type is ZoneType.PRIORITY else 0
            score = (prio + bonus, waits)
            if dest.cost == 1:
                if booked.zone_has_room(nxt, dest):
                    self._offer(layers[nxt], _Node(
                        dest, nxt, score, node, conn, False))
            elif booked.zone_has_room(nxt + 1, dest):
                self._offer(layers[nxt + 1], _Node(
                    dest, nxt + 1, score, node, conn, True))

    @staticmethod
    def _offer(layer: Dict[Zone, _Node], node: _Node) -> None:
        """Keep the best-scoring node for each zone of a layer."""
        known = layer.get(node.zone)
        if known is None or node.score > known.score:
            layer[node.zone] = node

    @staticmethod
    def _build(last: _Node) -> Plan:
        """Rebuild the plan that ends on the node `last`."""
        found: Dict[int, Location] = {}
        crossings: List[Tuple[int, Connection]] = []
        node: Optional[_Node] = last
        while node is not None:
            found[node.time] = node.zone
            if node.conn is not None:
                if node.transit:
                    found[node.time - 1] = Transit(node.conn, node.zone)
                    crossings.append((node.time - 1, node.conn))
                else:
                    crossings.append((node.time, node.conn))
            node = node.parent
        crossings.reverse()
        states = [found[turn] for turn in range(last.time + 1)]
        return Plan(states, crossings)
