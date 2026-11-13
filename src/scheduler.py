"""Plan the drones and replay the plans as simulation turns."""

from dataclasses import dataclass

from models import (Connection, FlyInError, Itinerary, Location, Move,
                    Network, Transit, Zone, ZoneType)


@dataclass
class _Node:
    """A search state: a drone on `zone` after `time` turns."""

    zone: Zone
    time: int
    score: tuple[int, int]
    parent: "_Node | None" = None
    transit: bool = False


class Planner:
    """Plan every drone on the network, one after the other."""

    def __init__(self, network: Network) -> None:
        """Keep the network to plan on."""
        self.network = network

    def plan_all(self) -> list[Itinerary]:
        """Return one itinerary per drone, in drone order."""
        zone_use: dict[tuple[int, Zone], int] = {}
        link_use: dict[tuple[int, Connection], int] = {}
        plans: list[Itinerary] = []
        latest = 0
        slack = 2 * len(self.network.zones) + 2
        for _ in range(self.network.nb_drones):
            plan = self._plan_one(zone_use, link_use, latest + slack)
            self._book(plan, zone_use, link_use)
            plans.append(plan)
            latest = max(latest, len(plan) - 1)
        return plans

    def _plan_one(self, zone_use: dict[tuple[int, Zone], int],
                  link_use: dict[tuple[int, Connection], int],
                  horizon: int) -> Itinerary:
        """Find the earliest arrival allowed by the reservations."""
        net = self.network
        layers: list[dict[Zone, _Node]] = [{} for _ in range(horizon + 3)]
        layers[0][net.start] = _Node(net.start, 0, (0, 0))
        for turn in range(horizon + 1):
            if net.end in layers[turn]:
                return self._build(layers[turn][net.end])
            for node in layers[turn].values():
                self._expand(zone_use, link_use, layers, node)
        raise FlyInError("no path connects start_hub to end_hub")

    def _expand(self, zone_use: dict[tuple[int, Zone], int],
                link_use: dict[tuple[int, Connection], int],
                layers: list[dict[Zone, _Node]], node: _Node) -> None:
        """Offer every move a drone can make from `node`."""
        zone, nxt = node.zone, node.time + 1
        prio, waits = node.score
        if zone.can_hold(zone_use.get((nxt, zone), 0) + 1):
            penalty = 0 if zone.is_start else 1
            self._offer(layers[nxt], _Node(
                zone, nxt, (prio, waits - penalty), node))
        for conn, dest in self.network.moves_from(zone):
            if link_use.get((nxt, conn), 0) >= conn.capacity:
                continue
            bonus = 1 if dest.zone_type is ZoneType.PRIORITY else 0
            score = (prio + bonus, waits)
            if dest.cost == 1:
                if dest.can_hold(zone_use.get((nxt, dest), 0) + 1):
                    self._offer(layers[nxt], _Node(dest, nxt, score, node))
            elif dest.can_hold(zone_use.get((nxt + 1, dest), 0) + 1):
                self._offer(layers[nxt + 1], _Node(
                    dest, nxt + 1, score, node, True))

    @staticmethod
    def _offer(layer: dict[Zone, _Node], node: _Node) -> None:
        """Keep the best-scoring node for each zone of a layer."""
        known = layer.get(node.zone)
        if known is None or node.score > known.score:
            layer[node.zone] = node

    def _book(self, plan: Itinerary, zone_use: dict[tuple[int, Zone], int],
              link_use: dict[tuple[int, Connection], int]) -> None:
        """Book every zone stay and connection use of `plan`."""
        for turn, loc in enumerate(plan):
            if isinstance(loc, Zone):
                zone_use[(turn, loc)] = zone_use.get((turn, loc), 0) + 1
        for turn in range(1, len(plan)):
            after = plan[turn]
            if isinstance(after, Transit):
                conn = after.connection
            else:
                before = plan[turn - 1]
                if not isinstance(before, Zone) or before is after:
                    continue
                link = self.network.link(before, after)
                assert link is not None
                conn = link
            link_use[(turn, conn)] = link_use.get((turn, conn), 0) + 1

    def _build(self, last: _Node) -> Itinerary:
        """Rebuild the itinerary that ends on the node `last`."""
        found: dict[int, Location] = {}
        node: _Node | None = last
        while node is not None:
            found[node.time] = node.zone
            if node.transit:
                parent = node.parent
                assert parent is not None
                conn = self.network.link(parent.zone, node.zone)
                assert conn is not None
                found[node.time - 1] = Transit(conn, node.zone)
            node = node.parent
        return [found[turn] for turn in range(last.time + 1)]


class Simulation:
    """Replay the plans and check the capacity rules."""

    def __init__(self, network: Network) -> None:
        """Keep the network whose rules are enforced."""
        self.network = network

    def run(self, plans: list[Itinerary]) -> list[list[Move]]:
        """Replay the plans; raise FlyInError on a capacity violation."""
        total = max((len(plan) - 1 for plan in plans), default=0)
        turns: list[list[Move]] = []
        for turn in range(1, total + 1):
            load: dict[Connection, int] = {}
            occupancy: dict[Zone, int] = {}
            moves: list[Move] = []
            for number, plan in enumerate(plans, 1):
                last = len(plan) - 1
                before = plan[min(turn - 1, last)]
                after = plan[min(turn, last)]
                conn: Connection | None = None
                if isinstance(before, Transit):
                    if after is not before.destination:
                        raise FlyInError(
                            f"turn {turn}: D{number} invalid arrival")
                    moves.append((f"D{number}-{before.destination.name}",
                                  before.destination))
                elif isinstance(after, Transit):
                    conn = after.connection
                    dest = after.destination
                    if (before not in (conn.a, conn.b)
                            or conn.other(before) is not dest
                            or dest.cost != 2):
                        raise FlyInError(
                            f"turn {turn}: D{number} illegal crossing")
                    moves.append((f"D{number}-{conn.name}",
                                  after.destination))
                elif after is not before:
                    conn = self.network.link(before, after)
                    if (conn is None
                            or after.zone_type is ZoneType.BLOCKED
                            or after.cost != 1):
                        raise FlyInError(
                            f"turn {turn}: D{number} invalid move")
                    moves.append((f"D{number}-{after.name}", after))
                if conn is not None:
                    load[conn] = load.get(conn, 0) + 1
                if isinstance(after, Zone):
                    occupancy[after] = occupancy.get(after, 0) + 1
            for conn, count in load.items():
                if count > conn.capacity:
                    raise FlyInError(
                        f"turn {turn}: connection {conn.name} over capacity")
            for zone, count in occupancy.items():
                if not zone.can_hold(count):
                    raise FlyInError(
                        f"turn {turn}: zone {zone.name} over capacity")
            turns.append(moves)
        return turns
