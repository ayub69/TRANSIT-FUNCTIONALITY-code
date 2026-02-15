# run_route_validity_suite.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import csv
import os
import random

import networkx as nx


# ============================================================
# CONFIG (you only change this if your folder name differs)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EDGES_CSV = os.path.join(BASE_DIR, "graphdata", "graph_edges.csv")  # <- your real export


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class EdgeMeta:
    route_id: int
    line_name: str
    distance_km: float
    time_min: float
    female_only: bool


Adjacency = Dict[int, Dict[int, List[EdgeMeta]]]


def _to_bool(x) -> bool:
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    s = str(x).strip().lower()
    return s in ("1", "true", "t", "yes", "y")


# ============================================================
# LOAD EDGES (FROM YOUR REAL CSV EXPORT)
# ============================================================

def load_edges_from_csv(edges_csv_path: str) -> Adjacency:
    """
    Expected columns:
      u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only
    """
    if not os.path.exists(edges_csv_path):
        raise FileNotFoundError(f"Edges CSV not found: {edges_csv_path}")

    adj: Adjacency = {}

    with open(edges_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"u_stop_id", "v_stop_id", "route_id", "line_name", "distance_km", "time_min", "female_only"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        for row in reader:
            u = int(row["u_stop_id"])
            v = int(row["v_stop_id"])
            route_id = int(row["route_id"])
            line_name = row.get("line_name", "") or "UNKNOWN"
            dist = float(row.get("distance_km", 0.0) or 0.0)
            time = float(row.get("time_min", 0.0) or 0.0)
            female_only = _to_bool(row.get("female_only", False))

            meta = EdgeMeta(
                route_id=route_id,
                line_name=line_name,
                distance_km=dist,
                time_min=time,
                female_only=female_only,
            )

            adj.setdefault(u, {}).setdefault(v, []).append(meta)

    return adj


# ============================================================
# BIDIRECTIONAL LOOKUP (REVERSE EDGE SUPPORT)
# ============================================================

def _get_metas_bidirectional(adj: Adjacency, u: int, v: int) -> List[EdgeMeta]:
    metas = adj.get(u, {}).get(v, [])
    if metas:
        return metas
    return adj.get(v, {}).get(u, [])


def edge_exists(adj: Adjacency, u: int, v: int) -> bool:
    return len(_get_metas_bidirectional(adj, u, v)) > 0


def any_edge_allowed_by_gender(adj: Adjacency, u: int, v: int, gender: str) -> bool:
    gender = (gender or "").strip().lower()
    metas = _get_metas_bidirectional(adj, u, v)
    if not metas:
        return False
    if gender == "male":
        return any(not m.female_only for m in metas)
    return True


def pick_best_edge_meta(adj: Adjacency, u: int, v: int, gender: str, mode: str) -> Optional[EdgeMeta]:
    """
    Pick the best edge between u and v based on:
      - gender constraints
      - mode weight (shortest=distance, fastest=time)
    """
    metas = _get_metas_bidirectional(adj, u, v)
    if not metas:
        return None

    gender = (gender or "").strip().lower()
    mode = (mode or "shortest").strip().lower()

    if gender == "male":
        metas = [m for m in metas if not m.female_only]
        if not metas:
            return None

    if mode == "fastest":
        return min(metas, key=lambda m: m.time_min)
    return min(metas, key=lambda m: m.distance_km)


# ============================================================
# ROUTING (REAL PATHS GENERATED FROM YOUR GRAPH)
# ============================================================

def build_stop_graph(adj: Adjacency, gender: str, mode: str) -> nx.DiGraph:
    """
    Stop-level directed graph with Option-B reverse behavior handled by edge lookup.
    We add both directions here so NetworkX can route both ways even if CSV is one-way.
    """
    G = nx.DiGraph()
    mode = (mode or "shortest").lower().strip()
    gender = (gender or "").lower().strip()

    # Add nodes from edges
    stop_ids = set(adj.keys())
    for u, nbrs in adj.items():
        stop_ids.add(u)
        for v in nbrs.keys():
            stop_ids.add(v)
    for sid in stop_ids:
        G.add_node(int(sid))

    # Add edges (both directions) with best weight for each direction
    # We iterate all u->v in CSV then also add v->u (reverse) with same meta
    for u, nbrs in adj.items():
        for v, metas in nbrs.items():
            u = int(u)
            v = int(v)

            # forward edge: u->v
            best_fwd = pick_best_edge_meta(adj, u, v, gender, mode)
            if best_fwd:
                w = best_fwd.distance_km if mode == "shortest" else best_fwd.time_min
                # keep best if already exists
                if not G.has_edge(u, v) or float(w) < float(G[u][v]["weight"]):
                    G.add_edge(u, v, weight=float(w), female_only=best_fwd.female_only)

            # reverse edge: v->u (Option B)
            best_rev = pick_best_edge_meta(adj, v, u, gender, mode)
            if best_rev:
                w = best_rev.distance_km if mode == "shortest" else best_rev.time_min
                if not G.has_edge(v, u) or float(w) < float(G[v][u]["weight"]):
                    G.add_edge(v, u, weight=float(w), female_only=best_rev.female_only)

    return G


def compute_shortest_or_fastest_path(adj: Adjacency, origin: int, dest: int, gender: str, mode: str) -> Optional[List[int]]:
    G = build_stop_graph(adj, gender, mode)
    try:
        path = nx.shortest_path(G, source=int(origin), target=int(dest), weight="weight")
        return [int(x) for x in path]
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def build_least_transfer_state_graph(adj: Adjacency, gender: str) -> nx.DiGraph:
    """
    State graph:
      Node = (stop_id, route_id)
      Ride along same route -> weight 0
      Transfer at same stop -> weight 1
    Includes Option B reverse movement too.
    """
    gender = (gender or "").strip().lower()
    G = nx.DiGraph()

    stop_routes: Dict[int, set] = {}

    # Collect all available (u,v,route_id) edges respecting gender for "ride" edges
    # But movement should be possible both directions (Option B), so add both u->v and v->u as ride edges
    for u, nbrs in adj.items():
        for v in nbrs.keys():
            u = int(u)
            v = int(v)

            # get all metas for u<->v bidirectional, but we need ride metas specifically per direction
            metas = _get_metas_bidirectional(adj, u, v)
            if not metas:
                continue

            # apply gender restriction
            if gender == "male":
                metas = [m for m in metas if not m.female_only]
                if not metas:
                    continue

            for m in metas:
                rid = int(m.route_id)

                stop_routes.setdefault(u, set()).add(rid)
                stop_routes.setdefault(v, set()).add(rid)

                # ride edges both directions on same route_id
                G.add_edge((u, rid), (v, rid), weight=0, edge_type="ride")
                G.add_edge((v, rid), (u, rid), weight=0, edge_type="ride")

    # transfer edges at same stop
    for stop, routes in stop_routes.items():
        routes = list(routes)
        if len(routes) < 2:
            continue
        for r1 in routes:
            for r2 in routes:
                if r1 != r2:
                    G.add_edge((stop, r1), (stop, r2), weight=1, edge_type="transfer")

    return G


def compute_least_transfer_state_path(adj: Adjacency, origin: int, dest: int, gender: str) -> Optional[Tuple[List[Tuple[int, int]], int, List[int]]]:
    """
    Returns:
      state_path: [(stop_id, route_id), ...] including transfers
      transfers: int
      stop_path: [stop_id,...] (derived)
    """
    G = build_least_transfer_state_graph(adj, gender)
    origin = int(origin)
    dest = int(dest)

    # start states = all routes available at origin
    origin_states = [n for n in G.nodes if n[0] == origin]
    dest_states = [n for n in G.nodes if n[0] == dest]
    if not origin_states or not dest_states:
        return None

    best_path = None
    best_cost = None

    # Multi-source multi-target: brute small (fine for demo/testing)
    # Choose minimum transfer cost.
    for s in origin_states:
        for t in dest_states:
            try:
                p = nx.shortest_path(G, source=s, target=t, weight="weight")
                cost = nx.path_weight(G, p, weight="weight")
                if best_cost is None or cost < best_cost:
                    best_cost = cost
                    best_path = p
            except nx.NetworkXNoPath:
                continue

    if best_path is None:
        return None

    state_path = [(int(s), int(r)) for (s, r) in best_path]
    transfers = int(best_cost or 0)

    stop_path = [state_path[0][0]]
    for (s, r) in state_path[1:]:
        if s != stop_path[-1]:
            stop_path.append(s)

    return state_path, transfers, stop_path


# ============================================================
# VALIDATOR (YOUR METRIC)
# ============================================================

@dataclass
class RouteTestCase:
    name: str
    gender: str
    mode: str  # shortest|fastest|least_transfers
    origin_stop_id: int
    dest_stop_id: int
    stop_path: Optional[List[int]] = None
    state_path: Optional[List[Tuple[int, int]]] = None
    expected_transfers: Optional[int] = None


def count_transfers_from_state_path(state_path: List[Tuple[int, int]]) -> int:
    if not state_path:
        return 0
    transfers = 0
    prev_route = int(state_path[0][1])
    for _, r in state_path[1:]:
        r = int(r)
        if r != prev_route:
            transfers += 1
            prev_route = r
    return transfers


def validate_route(adj: Adjacency, tc: RouteTestCase) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    gender = (tc.gender or "").strip().lower()
    mode = (tc.mode or "").strip().lower()

    # Build stop_path
    stop_path: Optional[List[int]] = None
    if tc.stop_path:
        stop_path = [int(x) for x in tc.stop_path]
    elif tc.state_path:
        stop_path = [int(s) for s, _ in tc.state_path]
    else:
        return False, ["No path provided (stop_path or state_path required)."]

    if not stop_path:
        return False, ["Empty path."]

    # Rule 4
    if stop_path[0] != int(tc.origin_stop_id):
        reasons.append(f"Path does not start at origin {tc.origin_stop_id} (starts at {stop_path[0]}).")
    if stop_path[-1] != int(tc.dest_stop_id):
        reasons.append(f"Path does not end at destination {tc.dest_stop_id} (ends at {stop_path[-1]}).")

    # Rule 1 + 2
    # If least_transfers and state_path given: validate ride transitions only (ignore transfer same-stop edges)
    if mode == "least_transfers" and tc.state_path:
        sp = [(int(s), int(r)) for s, r in tc.state_path]
        for i in range(len(sp) - 1):
            (s1, r1) = sp[i]
            (s2, r2) = sp[i + 1]

            # transfer step: same stop, route changes -> not a DB edge
            if s1 == s2 and r1 != r2:
                continue

            # ride step: stop changes -> must exist (forward OR reverse) and respect gender
            if s1 != s2:
                if not edge_exists(adj, s1, s2):
                    reasons.append(f"Missing edge in DB (ride): {s1} -> {s2}")
                    continue
                if not any_edge_allowed_by_gender(adj, s1, s2, gender):
                    reasons.append(f"Gender constraint violated on edge: {s1} -> {s2} (gender={gender})")
    else:
        # shortest/fastest: validate each stop hop exists (forward OR reverse)
        for i in range(len(stop_path) - 1):
            u = int(stop_path[i])
            v = int(stop_path[i + 1])
            if not edge_exists(adj, u, v):
                reasons.append(f"Missing edge in DB: {u} -> {v}")
                continue
            if not any_edge_allowed_by_gender(adj, u, v, gender):
                reasons.append(f"Gender constraint violated on edge: {u} -> {v} (gender={gender})")

    # Rule 3 (least transfers)
    if mode == "least_transfers":
        if tc.expected_transfers is None:
            reasons.append("Least-transfer mode requires expected_transfers.")
        elif tc.state_path:
            actual = count_transfers_from_state_path(tc.state_path)
            if int(actual) != int(tc.expected_transfers):
                reasons.append(f"Transfer count mismatch: expected={tc.expected_transfers}, actual={actual}")

    return (len(reasons) == 0), reasons


def route_validity_accuracy(adj: Adjacency, test_cases: List[RouteTestCase]) -> Dict[str, Any]:
    results = []
    valid_count = 0
    for tc in test_cases:
        ok, reasons = validate_route(adj, tc)
        if ok:
            valid_count += 1
        results.append({
            "name": tc.name,
            "gender": tc.gender,
            "mode": tc.mode,
            "origin": tc.origin_stop_id,
            "destination": tc.dest_stop_id,
            "valid": ok,
            "reasons": reasons,
        })

    total = len(test_cases)
    acc = (valid_count / total * 100.0) if total else 0.0
    return {
        "total_tested": total,
        "valid_routes": valid_count,
        "accuracy_percent": round(acc, 2),
        "results": results,
    }


# ============================================================
# GENERATE 40 REAL TESTS (NO FAKE PATHS)
# ============================================================

def _all_stop_ids_from_adj(adj: Adjacency) -> List[int]:
    s = set()
    for u, nbrs in adj.items():
        s.add(int(u))
        for v in nbrs.keys():
            s.add(int(v))
    return sorted(s)


def generate_40_real_tests(adj: Adjacency, seed: int = 42) -> List[RouteTestCase]:
    """
    Creates 40 tests by computing REAL routes from your graph:
      - male/female shortest/fastest/least_transfers
    Skips OD pairs that don't have a route for the requested mode.
    """
    random.seed(seed)
    stop_ids = _all_stop_ids_from_adj(adj)

    # We'll cycle through these modes/genders to ensure coverage
    combos = [
        ("male", "shortest"),
        ("male", "fastest"),
        ("male", "least_transfers"),
        ("female", "shortest"),
        ("female", "fastest"),
        ("female", "least_transfers"),
    ]

    tests: List[RouteTestCase] = []
    attempts = 0
    max_attempts = 5000  # safety to avoid infinite loop

    combo_idx = 0
    while len(tests) < 40 and attempts < max_attempts:
        attempts += 1
        gender, mode = combos[combo_idx]
        combo_idx = (combo_idx + 1) % len(combos)

        o = random.choice(stop_ids)
        d = random.choice(stop_ids)
        if o == d:
            continue

        if mode in ("shortest", "fastest"):
            path = compute_shortest_or_fastest_path(adj, o, d, gender, mode)
            if not path:
                continue
            tc = RouteTestCase(
                name=f"TC{len(tests)+1:02d} {gender} {mode} {o}->{d}",
                gender=gender,
                mode=mode,
                origin_stop_id=o,
                dest_stop_id=d,
                stop_path=path,
            )
            tests.append(tc)

        else:  # least_transfers
            res = compute_least_transfer_state_path(adj, o, d, gender)
            if not res:
                continue
            state_path, transfers, stop_path = res
            tc = RouteTestCase(
                name=f"TC{len(tests)+1:02d} {gender} least_transfers {o}->{d}",
                gender=gender,
                mode="least_transfers",
                origin_stop_id=o,
                dest_stop_id=d,
                state_path=state_path,
                expected_transfers=transfers,
            )
            tests.append(tc)

    if len(tests) < 40:
        raise RuntimeError(
            f"Could only generate {len(tests)} valid tests after {attempts} attempts. "
            f"This usually means the graph is highly disconnected or gender constraints remove many edges."
        )

    return tests


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("Loading edges from:", EDGES_CSV)
    adj = load_edges_from_csv(EDGES_CSV)

    print("Generating 40 REAL tests (computed from your graph)...")
    tests = generate_40_real_tests(adj, seed=42)

    print("Running validator...")
    report = route_validity_accuracy(adj, tests)

    print("\n=== ROUTE VALIDITY REPORT ===")
    print(f"Total tested: {report['total_tested']}")
    print(f"Valid routes: {report['valid_routes']}")
    print(f"Route Validity Accuracy (%): {report['accuracy_percent']}\n")

    # print per-test results
    for r in report["results"]:
        status = "✅ VALID" if r["valid"] else "❌ INVALID"
        print(f"{status} | {r['name']} | {r['gender']} | {r['mode']} | {r['origin']} -> {r['destination']}")
        if r["reasons"]:
            for reason in r["reasons"]:
                print("   -", reason)
