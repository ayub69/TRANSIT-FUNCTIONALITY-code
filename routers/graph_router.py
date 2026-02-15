
# routers/graph_router.py

from fastapi import APIRouter, Query, HTTPException
from services.graph_service import get_graph

router = APIRouter()


@router.get("/graph")
def graph_endpoint(
    gender: str = Query(..., description="female | male"),
    objective: str = Query(..., description="shortest | fastest | least_transfers"),
):
    G = get_graph(gender, objective)

    if G is None:
        raise HTTPException(status_code=400, detail="Invalid graph selection")

    return {
        "gender": gender,
        "objective": objective,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
    }


@router.get("/graph/summary")
def graph_summary():
    from services.graph_service import GRAPH_CACHE
    return {
        k: {"nodes": g.number_of_nodes(), "edges": g.number_of_edges()}
        for k, g in GRAPH_CACHE.items()
    }
