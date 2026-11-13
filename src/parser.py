"""Parse a map file into a validated Network."""

from typing import NoReturn

from models import Connection, FlyInError, Network, Zone, ZoneType


class MapParser:
    """Turn a map file into a validated `Network`."""

    ZONE_KEYS = {"zone", "color", "max_drones"}
    LINK_KEYS = {"max_link_capacity"}

    def parse(self, path: str) -> Network:
        """Read and parse the map at `path`."""
        with open(path, encoding="utf-8") as handle:
            return self._parse(handle.read())

    def _parse(self, text: str) -> Network:
        """Parse the map and validate its rules."""
        lines = [(n, line.split("#", 1)[0].strip())
                 for n, line in enumerate(text.splitlines(), 1)]
        lines = [(n, line) for n, line in lines if line]
        if not lines:
            raise FlyInError("empty map: nb_drones is missing")
        number, first = lines[0]
        key, sep, rest = first.partition(":")
        if not sep or key != "nb_drones":
            self._fail(number, "expected 'nb_drones: <positive_integer>'")
        nb_drones = self._int(rest, number)
        if nb_drones < 1:
            self._fail(number, "nb_drones must be a positive integer")
        zones: dict[str, Zone] = {}
        links: list[Connection] = []
        seen: set[frozenset[str]] = set()
        start: Zone | None = None
        end: Zone | None = None
        for number, line in lines[1:]:
            key, sep, rest = line.partition(":")
            if not sep:
                self._fail(number, "missing ':'")
            key = key.strip()
            body, meta = self._meta(rest, number)
            if key == "connection":
                names = body.split("-")
                if len(body.split()) != 1 or len(names) != 2 or not all(names):
                    self._fail(number, "expected '<zone1>-<zone2>'")
                for name in names:
                    if name not in zones:
                        self._fail(number, f"unknown zone '{name}'")
                if names[0] == names[1]:
                    self._fail(number, "self connection")
                pair = frozenset(names)
                if pair in seen:
                    self._fail(number, f"duplicate connection '{body}'")
                seen.add(pair)
                for name in meta.keys() - self.LINK_KEYS:
                    self._fail(number, f"unknown link metadata '{name}'")
                links.append(Connection(
                    zones[names[0]], zones[names[1]],
                    self._positive(meta, "max_link_capacity", number)))
                continue
            if key not in ("start_hub", "end_hub", "hub"):
                self._fail(number, f"unknown keyword '{key}'")
            parts = body.split()
            if len(parts) != 3:
                self._fail(number, "expected '<name> <x> <y> [metadata]'")
            name, x, y = parts
            if "-" in name or name in zones:
                self._fail(number, f"invalid zone '{name}'")
            for tag in meta.keys() - self.ZONE_KEYS:
                self._fail(number, f"unknown zone metadata '{tag}'")
            try:
                zone_type = ZoneType(meta.get("zone", "normal"))
            except ValueError:
                self._fail(number, f"invalid zone type '{meta['zone']}'")
            zone = Zone(name, self._int(x, number), self._int(y, number),
                        zone_type, meta.get("color"),
                        self._positive(meta, "max_drones", number),
                        key == "start_hub", key == "end_hub")
            zones[name] = zone
            if key == "start_hub":
                if start is not None:
                    self._fail(number, "duplicate start_hub")
                start = zone
            elif key == "end_hub":
                if end is not None:
                    self._fail(number, "duplicate end_hub")
                end = zone
        if start is None or end is None:
            raise FlyInError("the map needs one start_hub and one end_hub")
        return Network(nb_drones, list(zones.values()), links, start, end)

    def _meta(self, text: str,
              number: int) -> tuple[str, dict[str, str]]:
        """Split `body [k=v ...]` into the body and its metadata."""
        text = text.strip()
        if "[" not in text:
            if "]" in text:
                self._fail(number, "malformed metadata block")
            return text, {}
        if (text.count("[") != 1 or text.count("]") != 1
                or not text.endswith("]")):
            self._fail(number, "malformed metadata block")
        body, _, inner = text[:-1].partition("[")
        meta: dict[str, str] = {}
        for token in inner.split():
            name, sep, value = token.partition("=")
            if not sep or not name or not value or name in meta:
                self._fail(number, f"invalid metadata '{token}'")
            meta[name] = value
        return body.strip(), meta

    def _int(self, value: str, number: int) -> int:
        """Parse an integer."""
        value = value.strip()
        if value.startswith("+") or "_" in value:
            self._fail(number, "invalid integer")
        try:
            return int(value)
        except ValueError:
            self._fail(number, "invalid integer")

    def _positive(self, meta: dict[str, str], name: str,
                  number: int) -> int:
        """Read a positive metadata value, defaulting to 1."""
        value = self._int(meta[name], number) if name in meta else 1
        if value < 1:
            self._fail(number, f"{name} must be a positive integer")
        return value

    @staticmethod
    def _fail(number: int, message: str) -> NoReturn:
        """Raise an error prefixed with the line number."""
        raise FlyInError(f"line {number}: {message}")
