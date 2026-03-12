from __future__ import annotations

from fastapi import APIRouter, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from services.admin_service import (
    add_stop_to_route,
    admin_panel_html,
    get_route_sequence_by_name,
    get_system_counts,
    list_active_delays,
    remove_stop_from_route,
    report_delay,
)

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


class AddStopPayload(BaseModel):
    route_name: str = Field(..., description="Human-friendly route name")
    stop_name: str = Field(..., description="Stop name to insert")
    before_stop_name: str | None = Field(
        None,
        description="Required for start/middle insertion. For start-only insertion, provide only this.",
    )
    after_stop_name: str | None = Field(
        None,
        description="Required for end/middle insertion. For end-only insertion, provide only this.",
    )
    lat: float | None = Field(None, description="Required only if stop does not exist")
    lon: float | None = Field(None, description="Required only if stop does not exist")


class RemoveStopPayload(BaseModel):
    route_name: str
    stop_name: str


class DelayPayload(BaseModel):
    route_name: str
    from_stop_name: str
    to_stop_name: str
    delay_min: float = Field(..., gt=0)
    valid_for_min: int | None = Field(60, gt=0)
    reason: str | None = None


# @router.get("/panel", response_class=HTMLResponse)
# def admin_panel():
#     return HTMLResponse(content=admin_panel_html())


@router.get("/routes/sequence")
def route_sequence(route_name: str):
    return get_route_sequence_by_name(route_name)


@router.post("/routes/stops/insert")
def insert_stop(
    payload: AddStopPayload = Body(
        ...,
        examples={
            "insert_at_start": {
                "summary": "Insert At Start",
                "value": {
                    "route_name": "R1",
                    "stop_name": "New Terminal",
                    "before_stop_name": "Old First Stop",
                    "after_stop_name": None,
                    "lat": 24.90111,
                    "lon": 67.10222,
                },
            },
            "insert_at_end": {
                "summary": "Insert At End",
                "value": {
                    "route_name": "R1",
                    "stop_name": "New Last Stop",
                    "before_stop_name": None,
                    "after_stop_name": "Old Last Stop",
                },
            },
            "insert_in_middle": {
                "summary": "Insert In Middle",
                "value": {
                    "route_name": "R1",
                    "stop_name": "Inserted Mid Stop",
                    "before_stop_name": "Next Existing Stop",
                    "after_stop_name": "Previous Existing Stop",
                },
            },
        },
    )
):
    return add_stop_to_route(
        route_name=payload.route_name,
        stop_name=payload.stop_name,
        before_stop_name=payload.before_stop_name,
        after_stop_name=payload.after_stop_name,
        lat=payload.lat,
        lon=payload.lon,
    )


@router.post("/routes/stops/remove")
def remove_stop(
    payload: RemoveStopPayload = Body(
        ...,
        examples={
            "remove_stop": {
                "summary": "Remove Stop",
                "value": {
                    "route_name": "R1",
                    "stop_name": "Inserted Mid Stop",
                },
            }
        },
    )
):
    return remove_stop_from_route(route_name=payload.route_name, stop_name=payload.stop_name)


@router.post("/delays/report")
def report_delay_endpoint(
    payload: DelayPayload = Body(
        ...,
        examples={
            "report_delay": {
                "summary": "Report Delay Between Two Stops",
                "value": {
                    "route_name": "R1",
                    "from_stop_name": "Stop A",
                    "to_stop_name": "Stop B",
                    "delay_min": 8,
                    "valid_for_min": 60,
                    "reason": "Traffic congestion",
                },
            }
        },
    )
):
    return report_delay(
        route_name=payload.route_name,
        from_stop_name=payload.from_stop_name,
        to_stop_name=payload.to_stop_name,
        delay_min=payload.delay_min,
        valid_for_min=payload.valid_for_min,
        reason=payload.reason,
    )


@router.get("/delays/active")
def active_delays(route_name: str | None = None):
    return list_active_delays(route_name=route_name)


@router.get("/stats/counts")
def system_counts():
    return get_system_counts()
