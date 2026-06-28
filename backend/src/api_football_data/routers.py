"""Routes for football-data.org integration."""

from fastapi import APIRouter, Depends

from src.users.routers import verify_access_token
from src.api_football_data.football_data_org import list_tournaments

router = APIRouter(prefix="/football-data-org", tags=["football-data-org"])


@router.get("/tournaments")
async def list_football_data_org_tournaments(
    token_payload: dict = Depends(verify_access_token),
):
    """
    List available tournaments from football-data.org.

    Returns all TIER_ONE competitions that have a current or future season,
    formatted with name, area, season dates, and emblem URL.
    """
    return await list_tournaments()
