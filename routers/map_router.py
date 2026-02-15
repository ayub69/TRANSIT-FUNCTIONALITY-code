# routers/map_router.py

from fastapi import APIRouter, HTTPException
from services.map_service import (
    get_routes_geojson,
    get_stops_geojson,
    get_stop_details,
)

router = APIRouter(prefix="/fr2-4")

@router.get("/routes")
def all_routes_geojson():
    """
    FR2.4.1 - Returns all BRT route polylines as GeoJSON FeatureCollection.
    Each feature contains line_name, route_id, and color.
    """
    return get_routes_geojson()


@router.get("/routes/{line_name}")
def routes_for_line(line_name: str):
    """
    FR2.4.1 - Returns only the polylines for a specific line_name (e.g. Red).
    """
    data = get_routes_geojson()
    feats = [f for f in data.get("features", []) if str(f.get("properties", {}).get("line_name", "")).lower() == line_name.lower()]
    return {"type": "FeatureCollection", "features": feats}


@router.get("/stops")
def all_stops_geojson():
    """
    FR2.4.2 - Returns all bus stops as GeoJSON markers (Points),
    including stop_name, stop_code, connected_lines, and services placeholders.
    """
    return get_stops_geojson()


@router.get("/stops/{stop_id}")
def stop_details(stop_id: int):
    """
    FR2.4.2 - Returns details for a stop that frontend can show when user taps marker.
    """
    try:
        return get_stop_details(stop_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
