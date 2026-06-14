"""
Crime hotspot & trend analysis tool.

Hotspot detection: group FIRs by lat/lng grid cells, find high-density clusters.
Trend analysis: FIRs over time by crime_head, district, or statewide.
No geospatial types needed — all computed in Python from plain lat/lng floats.
"""

import sqlite3
import math
from collections import defaultdict
from .. engine import config


def _grid_key(lat, lng, cell_deg=0.05):
    """Snap a coordinate to the nearest grid cell (~5km at India's latitude)."""
    return (round(lat / cell_deg) * cell_deg, round(lng / cell_deg) * cell_deg)


def get_hotspots(crime_head: str = None, district_id: int = None, top_n: int = 20):
    """
    Return hotspot clusters: each cluster has a centroid, count, and top crime types.
    """
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    sql = "SELECT f.id, f.latitude, f.longitude, f.crime_head, d.name AS district FROM firs f JOIN districts d ON d.id = f.district_id WHERE f.latitude IS NOT NULL"
    params = []
    if crime_head:
        sql += " AND f.crime_head = ?"
        params.append(crime_head)
    if district_id:
        sql += " AND f.district_id = ?"
        params.append(district_id)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    # Grid clustering
    cells = defaultdict(lambda: {"count": 0, "crimes": defaultdict(int), "lats": [], "lngs": [], "district": ""})
    for r in rows:
        key = _grid_key(r["latitude"], r["longitude"])
        cells[key]["count"] += 1
        cells[key]["crimes"][r["crime_head"]] += 1
        cells[key]["lats"].append(r["latitude"])
        cells[key]["lngs"].append(r["longitude"])
        cells[key]["district"] = r["district"]

    hotspots = []
    for (lat, lng), cell in sorted(cells.items(), key=lambda x: -x[1]["count"])[:top_n]:
        top_crime = max(cell["crimes"], key=cell["crimes"].get)
        hotspots.append({
            "lat": sum(cell["lats"]) / len(cell["lats"]),
            "lng": sum(cell["lngs"]) / len(cell["lngs"]),
            "count": cell["count"],
            "top_crime": top_crime,
            "district": cell["district"],
            "radius": min(2000, 500 + cell["count"] * 50),  # for map circle radius (metres)
        })

    return {
        "hotspots": hotspots,
        "total_firs": len(rows),
        "summary": f"{len(hotspots)} hotspot clusters from {len(rows)} FIRs.",
    }


def get_trends(crime_head: str = None, district_id: int = None, group_by: str = "month"):
    """
    Time-series trend: FIRs grouped by month/year, optionally filtered by crime_head or district.
    Returns list of {"period": "YYYY-MM", "count": N} suitable for a chart.
    """
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    if group_by == "month":
        period_expr = "substr(occurrence_date,1,7)"
    else:
        period_expr = "substr(occurrence_date,1,4)"

    sql = f"SELECT {period_expr} AS period, COUNT(*) AS count FROM firs WHERE 1=1"
    params = []
    if crime_head:
        sql += " AND crime_head = ?"
        params.append(crime_head)
    if district_id:
        sql += " AND district_id = ?"
        params.append(district_id)
    sql += " GROUP BY period ORDER BY period"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    trend = [{"period": r["period"], "count": r["count"]} for r in rows]
    total = sum(r["count"] for r in rows)

    # Simple moving average (3-period) for smoothing
    for i, item in enumerate(trend):
        window = trend[max(0, i-1):i+2]
        item["sma"] = round(sum(w["count"] for w in window) / len(window), 1)

    return {
        "trend": trend,
        "total": total,
        "group_by": group_by,
        "filter": {"crime_head": crime_head, "district_id": district_id},
        "summary": f"{total} FIRs across {len(trend)} {group_by}s.",
    }
