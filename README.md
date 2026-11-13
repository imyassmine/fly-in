*This activity has been created as part of the 42 curriculum by yassabda.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a start hub to an end hub through a
network of zones, in as few simulation turns as possible. Zones have a type
(`normal`, `restricted`, `priority`, `blocked`) and a capacity
(`max_drones`), connections have a capacity (`max_link_capacity`). The
program parses a map file, plans every drone, replays the plans in a
simulation engine that enforces all movement and capacity rules, and prints
one line per turn.

Files: `models.py` (zones, connections, network, plans and movements),
`parser.py` (map parser), `scheduler.py` (path planning and turn output),
`main.py` (entry point and colored terminal output).

## Instructions

Python 3.10 or later is required.

```
make install                                  # flake8 and mypy
make run MAP=maps/easy/01_linear_path.txt     # or: python3 src/main.py <map_file>
make debug MAP=maps/easy/01_linear_path.txt   # run under pdb
make lint                                     # flake8 + mypy
make clean
```

The movements are printed on stdout, the total number of turns and any error
on stderr. A parsing error stops the program with the line and the cause. A
valid map with no path from start to end is reported as an error.

## Algorithm and implementation strategy

**Cooperative planning on a time-expanded network.** Drones are planned one
after the other. For each drone the planner explores the network turn by
turn: a search state is "zone Z after turn T". From a state a drone can wait,
move to a neighbouring zone (1 turn), or start crossing a connection toward a
restricted zone (arrival 2 turns later, no waiting on the connection). A move
is only offered if the zone occupancy (`max_drones`) at the arrival turn and
the connection load (`max_link_capacity`) during the departure turn are still
free in the reservation table. Layers are explored in order of turn, so the
first layer containing the end zone gives the earliest arrival for that
drone. The chosen itinerary is then booked in the reservation table, which
makes the next drones route around it: this distributes the drones over
several paths and makes them wait when needed. Deadlocks cannot happen since
every drone is planned against fixed reservations and can always wait on the
start zone, which has no capacity limit.

**Tie-breaking.** Among itineraries with the same arrival turn, the one that
crosses the most `priority` zones wins, then the one that waits on the start
zone rather than on a zone other drones may need. `blocked` zones are never
entered.

**Simulation engine.** `Planner` only builds legal moves and books every
zone stay and connection use, so movement and capacity rules are enforced
during planning. `Simulation` replays the itineraries and produces the
movements printed for each turn.

**Complexity.** One search costs O(H * (V + E)) with H the number of turns
explored, V the zones and E the connections, so planning N drones costs
O(N * H * (V + E)). Each search uses O(H * V) memory; the reservation table
grows with the total number of drone-turns booked. Paths are computed once
per drone and are not cached or recalculated.

## Visual representation

When stdout is a terminal, each movement is colored with the `color` of the
zone it goes to (for a drone in flight toward a restricted zone, the color of
that zone), so the flow of drones along colored areas can be followed turn by
turn. Colors are disabled when the output is piped or when `NO_COLOR` is set.

## Example

Input (`01_linear_path.txt`):

```
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

Output (4 turns):

```
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

A drone in flight toward a restricted zone is printed with the name of the
connection (`D1-hub-roof1`), then with the zone on the next turn.

## Resources

- Cooperative A* / windowed hierarchical cooperative A*, D. Silver, "Cooperative Pathfinding".
- Breadth-first search and shortest paths: https://en.wikipedia.org/wiki/Breadth-first_search
- Time-expanded networks: https://en.wikipedia.org/wiki/Flow_network

AI usage: Claude was used to review and debug the code, and to write this README.
