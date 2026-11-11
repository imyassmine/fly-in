import re
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from models import Connection, Network, Zone, ZoneType


class ParseError(Exception):
    """Raised when a map file does not respect the expected format."""


class MapParser:
    """Turn the text of a map file into a validated `Network`."""

    ZONE_KEYS = {"zone", "color", "max_drones"}
    LINK_KEYS = {"max_link_capacity"}
    ZONE_PREFIXES = {"start_hub", "end_hub", "hub"}

    def parse(self, path: str) -> Network:
        """Read the file at `path` and parse it."""
        with open(path, encoding="utf-8") as handle:
            return self.parse_text(handle.read())

    def parse_text(self, text: str) -> Network:
        """Parse the content of a map and return the network."""
        nb_drones: Optional[int] = None
        zones: Dict[str, Zone] = {}
        connections: List[Connection] = []
        seen: Set[FrozenSet[str]] = set()
        start: Optional[Zone] = None
        end: Optional[Zone] = None
        for number, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if nb_drones is None:
                nb_drones = self._parse_drones(line, number)
                continue
            key, sep, rest = line.partition(":")
            key = key.strip()
            if not sep:
                raise self._error(number, "missing ':' after the keyword")
            body, meta = self._split_meta(rest, number)
            if key in self.ZONE_PREFIXES:
                zone = self._parse_zone(key, body, meta, zones, number)
                zones[zone.name] = zone
                if zone.is_start:
                    start = self._unique(start, zone, "start_hub", number)
                if zone.is_end:
                    end = self._unique(end, zone, "end_hub", number)
            elif key == "connection":
                connections.append(
                    self._parse_link(body, meta, zones, seen, number))
            elif key == "nb_drones":
                raise self._error(number, "nb_drones is defined twice")
            else:
                raise self._error(number, f"unknown keyword '{key}'")
        if nb_drones is None:
            raise ParseError("empty map: nb_drones is missing")
        if start is None or end is None:
            raise ParseError("the map needs one start_hub and one end_hub")
        return Network(nb_drones, list(zones.values()), connections,
                       start, end)

    @staticmethod
    def _error(number: int, message: str) -> ParseError:
        """Build a ParseError that mentions the line number."""
        return ParseError(f"line {number}: {message}")

    def _unique(self, current: Optional[Zone], zone: Zone, label: str,
                number: int) -> Zone:
        """Refuse a second start or end hub."""
        if current is not None:
            raise self._error(number, f"more than one {label}")
        return zone

    def _parse_drones(self, line: str, number: int) -> int:
        """Parse the 'nb_drones: <positive_integer>' first line."""
        match = re.fullmatch(r"nb_drones:\s*(\d+)", line)
        if match is None or int(match.group(1)) < 1:
            raise self._error(
                number, "first line must be 'nb_drones: <positive_integer>'")
        return int(match.group(1))

    def _split_meta(self, text: str,
                    number: int) -> Tuple[str, Dict[str, str]]:
        """Split 'body [k=v k=v]' into the body and a metadata dict."""
        text = text.strip()
        if "[" not in text and "]" not in text:
            return text, {}
        if (text.count("[") != 1 or text.count("]") != 1
                or not text.endswith("]")):
            raise self._error(number, "malformed metadata block")
        body, _, inner = text[:-1].partition("[")
        meta: Dict[str, str] = {}
        for token in inner.split():
            name, eq, value = token.partition("=")
            if not eq or not name or not value:
                raise self._error(number, f"invalid metadata '{token}'")
            if name in meta:
                raise self._error(number, f"duplicate metadata '{name}'")
            meta[name] = value
        return body.strip(), meta

    def _positive(self, value: str, name: str, number: int) -> int:
        """Parse a strictly positive integer metadata value."""
        if not re.fullmatch(r"\d+", value) or int(value) < 1:
            raise self._error(number, f"{name} must be a positive integer")
        return int(value)

    def _parse_zone(self, prefix: str, body: str, meta: Dict[str, str],
                    zones: Dict[str, Zone], number: int) -> Zone:
        """Parse one 'hub' / 'start_hub' / 'end_hub' definition."""
        parts = body.split()
        if len(parts) != 3:
            raise self._error(number, "expected '<name> <x> <y> [metadata]'")
        name, x, y = parts
        if "-" in name:
            raise self._error(number, "zone names cannot contain dashes")
        if name in zones:
            raise self._error(number, f"duplicate zone '{name}'")
        if not (re.fullmatch(r"-?\d+", x) and re.fullmatch(r"-?\d+", y)):
            raise self._error(number, "coordinates must be integers")
        for key in meta:
            if key not in self.ZONE_KEYS:
                raise self._error(number, f"unknown zone metadata '{key}'")
        try:
            zone_type = ZoneType(meta.get("zone", "normal"))
        except ValueError:
            raise self._error(
                number, f"invalid zone type '{meta['zone']}'") from None
        capacity = 1
        if "max_drones" in meta:
            capacity = self._positive(meta["max_drones"], "max_drones",
                                      number)
        return Zone(name, int(x), int(y), zone_type, meta.get("color"),
                    capacity, prefix == "start_hub", prefix == "end_hub")

    def _parse_link(self, body: str, meta: Dict[str, str],
                    zones: Dict[str, Zone], seen: Set[FrozenSet[str]],
                    number: int) -> Connection:
        """Parse one 'connection: a-b [max_link_capacity=n]' line."""
        names = body.split("-")
        if len(body.split()) != 1 or len(names) != 2 or not all(names):
            raise self._error(number, "expected '<zone1>-<zone2>'")
        for name in names:
            if name not in zones:
                raise self._error(number, f"unknown zone '{name}'")
        if names[0] == names[1]:
            raise self._error(number, "a zone cannot link to itself")
        pair = frozenset(names)
        if pair in seen:
            raise self._error(number, f"duplicate connection '{body}'")
        seen.add(pair)
        for key in meta:
            if key not in self.LINK_KEYS:
                raise self._error(number, f"unknown link metadata '{key}'")
        capacity = 1
        if "max_link_capacity" in meta:
            capacity = self._positive(meta["max_link_capacity"],
                                      "max_link_capacity", number)
        return Connection(zones[names[0]], zones[names[1]], capacity)
