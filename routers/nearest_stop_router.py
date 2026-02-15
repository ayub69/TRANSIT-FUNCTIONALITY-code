# routers/nearest_stop_router.py

from fastapi import APIRouter
from pydantic import BaseModel, Field
from services.nearest_stop_service import walk_to_nearest_stop
from services.nearest_stop_service import walk_from_stop_to_pin

router = APIRouter(prefix="/fr:walking steps+transfer points")


class WalkToNearestIn(BaseModel):
    lat: float = Field(..., example=24.9004187, description="Device GPS latitude OR map-tap latitude")
    lon: float = Field(..., example=67.1963745, description="Device GPS longitude OR map-tap longitude")


class StopToPinIn(BaseModel):
    stop_id: int = Field(..., example=5)
    pin_lat: float = Field(..., example=24.8844268)
    pin_lon: float = Field(..., example=67.1745528)


@router.post("/walk-to-nearest")
def walk_to_nearest(payload: WalkToNearestIn):
    """
    One API for FR:
    - Detect user location (frontend device provides GPS coords)
    - Identify nearest stop
    - OSRM walking directions from user -> nearest stop
    """
    return walk_to_nearest_stop(payload.lat, payload.lon)

@router.post("/walk-from-stop-to-pin")
def api_walk_from_stop_to_pin(payload: StopToPinIn):
    return walk_from_stop_to_pin(payload.stop_id, payload.pin_lat, payload.pin_lon)