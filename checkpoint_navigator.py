import heapq
import math

# ─────────────────────────────────────────────
# TOGGLE — set False for demo, True for campus
# ─────────────────────────────────────────────
CHECKPOINT_MODE = True

# ─────────────────────────────────────────────
# PRE-MAPPED CAMPUS CHECKPOINTS
# Replace coordinates with your actual campus GPS values
# type: "major" | "turn" | "crossing_up" | "crossing_down"
# ─────────────────────────────────────────────
CHECKPOINTS = {
    "H4":       {"lat": 23.0100, "lon": 72.5100, "type": "major",        "label": "Hostel 4"},
    "H5":       {"lat": 23.0110, "lon": 72.5105, "type": "major",        "label": "Hostel 5"},
    "H6":       {"lat": 23.0115, "lon": 72.5110, "type": "major",        "label": "Hostel 6"},
    "H7":       {"lat": 23.0120, "lon": 72.5115, "type": "major",        "label": "Hostel 7"},
    "LT":       {"lat": 23.0130, "lon": 72.5120, "type": "major",        "label": "Lecture Theatre"},
    "CANTEEN":  {"lat": 23.0125, "lon": 72.5130, "type": "major",        "label": "Canteen"},
    "LIBRARY":  {"lat": 23.0140, "lon": 72.5125, "type": "major",        "label": "Library"},
    "GATE":     {"lat": 23.0090, "lon": 72.5095, "type": "major",        "label": "Main Gate"},
    "T1":       {"lat": 23.0105, "lon": 72.5107, "type": "turn",         "label": "Turn Point 1"},
    "C1_UP":    {"lat": 23.0118, "lon": 72.5112, "type": "crossing_up",  "label": "Crossing 1 Arriving"},
    "C1_DOWN":  {"lat": 23.0119, "lon": 72.5113, "type": "crossing_down","label": "Crossing 1 Other Side"},
}

# ─────────────────────────────────────────────
# GRAPH — connections between checkpoints
# Each edge: (from, to, distance_in_metres)
# ─────────────────────────────────────────────
EDGES = [
    ("H4",      "T1",      30),
    ("T1",      "H5",      20),
    ("T1",      "C1_UP",   25),
    ("C1_UP",   "C1_DOWN", 10),
    ("C1_DOWN", "H7",      20),
    ("H5",      "H6",      15),
    ("H6",      "LT",      40),
    ("LT",      "LIBRARY", 30),
    ("LIBRARY", "CANTEEN", 35),
    ("H4",      "GATE",    50),
]

def buildGraph():
    graph = {}
    for cp in CHECKPOINTS:
        graph[cp] = []
    for a, b, dist in EDGES:
        graph[a].append((b, dist))
        graph[b].append((a, dist))  # bidirectional
    return graph

def dijkstra(start, end):
    """Find shortest path from start to end checkpoint."""
    graph = buildGraph()
    queue = [(0, start, [start])]
    visited = set()

    while queue:
        cost, node, path = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        if node == end:
            return path, cost
        for neighbour, weight in graph[node]:
            if neighbour not in visited:
                heapq.heappush(queue, (cost + weight, neighbour, path + [neighbour]))

    return [], float("inf")  # no path found

def getDistance(lat1, lon1, lat2, lon2):
    """Haversine formula — straight line distance in metres between two GPS points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def getNearestCheckpoint(lat, lon):
    """Find the closest major checkpoint to the user's current GPS position."""
    nearest = None
    minDist = float("inf")
    for cp_id, cp in CHECKPOINTS.items():
        if cp["type"] == "major":
            d = getDistance(lat, lon, cp["lat"], cp["lon"])
            if d < minDist:
                minDist = d
                nearest = cp_id
    return nearest

# ─────────────────────────────────────────────
# NAVIGATION STATE
# ─────────────────────────────────────────────
navState = {
    "active":       False,
    "route":        [],    # ordered list of checkpoint IDs
    "current_idx":  0,     # which checkpoint user is heading to
    "destination":  None,
}

def startNavigation(destination, current_lat, current_lon):
    if not CHECKPOINT_MODE:
        return {"error": "Checkpoint mode is disabled for demo"}

    start = getNearestCheckpoint(current_lat, current_lon)
    route, cost = dijkstra(start, destination)

    if not route:
        return {"error": f"No route found from {start} to {destination}"}

    navState["active"]      = True
    navState["route"]       = route
    navState["current_idx"] = 0
    navState["destination"] = destination

    return {
        "route": route,
        "route_labels": [CHECKPOINTS[cp]["label"] for cp in route],
        "total_distance": cost,
        "first_instruction": f"Head towards {CHECKPOINTS[route[0]]['label']}"
    }

def updateLocation(current_lat, current_lon):
    """Called every second with new GPS coordinates."""
    if not CHECKPOINT_MODE or not navState["active"]:
        return {"active": False}

    route = navState["route"]
    idx   = navState["current_idx"]

    if idx >= len(route):
        return {"active": False, "message": "You have reached your destination"}

    next_cp_id = route[idx]
    next_cp    = CHECKPOINTS[next_cp_id]
    dist       = getDistance(current_lat, current_lon, next_cp["lat"], next_cp["lon"])

    # Checkpoint reached if within 5 metres
    if dist < 5:
        navState["current_idx"] += 1
        cp_type = next_cp["type"]

        if navState["current_idx"] >= len(route):
            navState["active"] = False
            return {
                "active":      False,
                "cp_reached":  next_cp_id,
                "cp_type":     cp_type,
                "message":     f"You have reached {next_cp['label']}",
                "destination_reached": True
            }

        next_next = CHECKPOINTS[route[navState["current_idx"]]]
        return {
            "active":     True,
            "cp_reached": next_cp_id,
            "cp_type":    cp_type,
            "message":    f"Checkpoint reached. Head towards {next_next['label']}",
            "next_cp":    route[navState["current_idx"]],
            "destination_reached": False
        }

    return {
        "active":       True,
        "next_cp":      next_cp_id,
        "next_label":   next_cp["label"],
        "distance_m":   round(dist),
        "message":      "",
        "destination_reached": False
    }

def getRouteState():
    """Returns current route for frontend checkpoint strip display."""
    return {
        "route":       navState["route"],
        "current_idx": navState["current_idx"],
        "checkpoints": {
            cp_id: {
                "label": CHECKPOINTS[cp_id]["label"],
                "type":  CHECKPOINTS[cp_id]["type"]
            }
            for cp_id in navState["route"]
        }
    }
