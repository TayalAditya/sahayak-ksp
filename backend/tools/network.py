"""
Criminal network graph tool.

Queries the associations + fir_persons tables to build a link graph:
  nodes = persons (accused)
  edges = co-accused (shared FIR) | gang membership | known associate | family

Returns a JSON graph ready for vis.js / D3 force layout in the frontend.
"""

import sqlite3
from .. engine import config, db


def get_network(person_id: int = None, gang_name: str = None, crime_head: str = None, max_depth: int = 2):
    """
    Build a network graph around a person, gang, or crime type.
    Returns {"nodes": [...], "edges": [...], "summary": str}.
    """
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- seed nodes
    seed_ids = set()

    if person_id:
        seed_ids.add(person_id)

    if gang_name:
        rows = conn.execute(
            "SELECT DISTINCT person_a_id, person_b_id FROM associations WHERE gang_name = ?",
            (gang_name,)
        ).fetchall()
        for r in rows:
            seed_ids.update([r["person_a_id"], r["person_b_id"]])

    if crime_head:
        rows = conn.execute(
            "SELECT DISTINCT fp.person_id FROM fir_persons fp JOIN firs f ON f.id = fp.fir_id "
            "WHERE f.crime_head = ? AND fp.role = 'Accused' LIMIT 50",
            (crime_head,)
        ).fetchall()
        for r in rows:
            seed_ids.add(r["person_id"])

    if not seed_ids:
        # default: top 20 by case count
        rows = conn.execute(
            "SELECT person_id FROM fir_persons WHERE role='Accused' "
            "GROUP BY person_id ORDER BY COUNT(*) DESC LIMIT 20"
        ).fetchall()
        seed_ids = {r["person_id"] for r in rows}

    # --- expand to neighbours (BFS, depth-limited)
    all_ids = set(seed_ids)
    frontier = set(seed_ids)
    for _ in range(max_depth):
        if not frontier:
            break
        placeholders = ",".join("?" * len(frontier))
        rows = conn.execute(
            f"SELECT DISTINCT person_a_id, person_b_id FROM associations "
            f"WHERE person_a_id IN ({placeholders}) OR person_b_id IN ({placeholders})",
            list(frontier) * 2
        ).fetchall()
        next_frontier = set()
        for r in rows:
            for pid in (r["person_a_id"], r["person_b_id"]):
                if pid not in all_ids:
                    next_frontier.add(pid)
        all_ids.update(next_frontier)
        frontier = next_frontier
        if len(all_ids) > 200:
            break

    # --- fetch person details
    if not all_ids:
        conn.close()
        return {"nodes": [], "edges": [], "summary": "No network found."}

    placeholders = ",".join("?" * len(all_ids))
    persons = conn.execute(
        f"SELECT p.id, p.full_name, p.is_repeat_offender, "
        f"COUNT(DISTINCT fp.fir_id) AS case_count "
        f"FROM persons p LEFT JOIN fir_persons fp ON fp.person_id = p.id AND fp.role='Accused' "
        f"WHERE p.id IN ({placeholders}) GROUP BY p.id",
        list(all_ids)
    ).fetchall()

    nodes = []
    for p in persons:
        nodes.append({
            "id": p["id"],
            "label": p["full_name"],
            "cases": p["case_count"],
            "is_repeat": bool(p["is_repeat_offender"]),
            "is_seed": p["id"] in seed_ids,
            "size": min(30, 8 + p["case_count"] * 2),
        })

    # --- fetch edges between all_ids
    edges_raw = conn.execute(
        f"SELECT person_a_id, person_b_id, association_type, gang_name, strength "
        f"FROM associations "
        f"WHERE person_a_id IN ({placeholders}) AND person_b_id IN ({placeholders})",
        list(all_ids) * 2
    ).fetchall()

    seen_edges = set()
    edges = []
    for e in edges_raw:
        key = (min(e["person_a_id"], e["person_b_id"]), max(e["person_a_id"], e["person_b_id"]))
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append({
            "from": e["person_a_id"],
            "to": e["person_b_id"],
            "type": e["association_type"],
            "gang": e["gang_name"],
            "weight": e["strength"],
        })

    conn.close()

    summary = (
        f"Network: {len(nodes)} persons, {len(edges)} links. "
        f"Seed: {len(seed_ids)} node(s). "
        f"{sum(1 for n in nodes if n['is_repeat'])} repeat offenders."
    )
    return {"nodes": nodes, "edges": edges, "summary": summary}
