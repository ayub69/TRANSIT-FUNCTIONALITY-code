# routers/bus_fr22_router.py

from fastapi import APIRouter, HTTPException, Query
from services.bus_fr22_service import get_arrival_predictions, get_live_bus_positions,get_live_buses_within_radius
from typing import Optional

router = APIRouter(prefix="/fr2-2")

@router.get("/arrivals")
def arrivals(
    stop_id: int = Query(...),
    gender: str = Query("male"),
    minutes_ahead: int = Query(60, ge=1, le=240),
    line_name: Optional[str] = Query(None),
):
    """
    FR2.2.1: Bus Arrival Predictions (timetable + avg travel durations)
    """
    try:
        return get_arrival_predictions(stop_id, gender, minutes_ahead, line_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#@router.get("/live-buses")
def live_buses(
    line_name: str = Query(...),
    gender: str = Query("male"),
    max_buses: int = Query(100, ge=1, le=500),
    user_lat: float | None = Query(None),
    user_lon: float | None = Query(None),
    nearest_k: int = Query(10, ge=1, le=100),
):
    """
    FR2.2.2: Live buses by line.
    """
    try:
        return get_live_bus_positions(
            gender=gender,
            line_name=line_name,
            max_buses=max_buses,
            user_lat=user_lat,
            user_lon=user_lon,
            nearest_k=nearest_k,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from services.bus_fr22_service import get_live_buses_within_radius  # NEW import

@router.get("/live-buses-nearby")
def live_buses_nearby(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(5, ge=0.1, le=10.0),
    gender: str = Query("male"),
    nearest_k: int = Query(15, ge=1, le=50),
    max_buses: int = Query(200, ge=1, le=500),
):
    """
    FR2.2.2: Live buses near user location within radius_km
    """
    try:
        return get_live_buses_within_radius(
            gender=gender,
            user_lat=lat,
            user_lon=lon,
            radius_km=radius_km,
            nearest_k=nearest_k,
            max_buses=max_buses
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



