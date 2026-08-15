import asyncio
import requests
import datetime
import hashlib
from pathlib import Path
from aiocache import cached
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import AsyncSessionLocal

from src.config import settings
from src.logging_config import get_logger
from src.predictions import scoring as predictions_scoring
from src.tournaments.models import Tournament
from src.matches.models import Match
from src.teams.models import Team
from src.groups_stages.models import Group, Stage

logger = get_logger(__name__)
_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

# Only tournaments with a match that kicked off within this window are refreshed by
# update_all_tournaments() — keeps the scheduled job off the API for dormant tournaments.
UPDATE_LOOKBACK = datetime.timedelta(hours=48)


async def _get_with_retries(url: str, *, headers: dict | None = None, params: dict | None = None, timeout: int = 30):
    """Perform a football-data.org request with short retries for transient SSL/connection issues."""
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            return await asyncio.to_thread(requests.get, url, headers=headers, params=params, timeout=timeout)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_error = exc
            if attempt == 2:
                logger.exception("Failed to reach football-data.org after 3 attempts: %s", exc)
                raise
            logger.warning(
                "Transient football-data.org request error on attempt %s/3: %s",
                attempt + 1,
                exc,
            )
            await asyncio.sleep(2**attempt)

    if last_error is not None:
        raise last_error

    raise RuntimeError("football-data.org request failed without a captured error")


@cached(ttl=10*60)  # Cache for 10 minutes
async def api_request(endpoint: str, fd_competition_id: int) -> dict:
    """Make a cached API request to the football-data.org API for a specific endpoint (matches, standings).
    Args:
        endpoint (str): The endpoint to request (e.g., "matches", "standings").
        fd_competition_id (int): The football-data.org competition ID.
    Returns:
        dict: The JSON response from the API.
    """
    url = f"https://api.football-data.org/v4/competitions/{fd_competition_id}/{endpoint}"
    headers = {"X-Auth-Token": settings.football_data_org_api_key}

    logger.info(f"Making API request to football-data.org: {url}")

    response = await _get_with_retries(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    return data


@cached(ttl=60*60)  # Cache for 1 hour
async def list_tournaments() -> list:
    url = "https://api.football-data.org/v4/competitions"
    headers = {"X-Auth-Token": settings.football_data_org_api_key}
    tier = settings.football_data_org_api_tier

    response = await _get_with_retries(url, headers=headers, params={"plan": tier}, timeout=30)
    response.raise_for_status()
    data = response.json()

    today = datetime.datetime.now(ZoneInfo(settings.tz)).strftime("%Y-%m-%d")

    tournament_lst_formatted = [
        {
            "id": tournament["id"],
            "name": f'{tournament["name"]} ({tournament["currentSeason"]["startDate"][:4] if tournament["currentSeason"] else "N/A"}-{tournament["currentSeason"]["endDate"][:4] if tournament["currentSeason"] else "N/A"}, {tournament["area"]["name"]})',
            "area": tournament["area"]["name"],
            "current_season_start": tournament["currentSeason"]["startDate"] if tournament["currentSeason"] else None,
            "current_season_end": tournament["currentSeason"]["endDate"] if tournament["currentSeason"] else None,
            "emblem_url": tournament["emblem"],
        }
        for tournament in data["competitions"]
        if (tournament["currentSeason"]["endDate"] >= today if tournament["currentSeason"] else True)
    ]

    tournament_lst_formatted.sort(key=lambda x: x["name"])
    tournament_lst_formatted.sort(key=lambda x: x["current_season_end"] or "", reverse=True)

    logger.info(f"Pulled {len(tournament_lst_formatted)} tournaments from football-data.org with API key level={tier}")

    return tournament_lst_formatted


@cached(ttl=10*60)  # Cache for 10 minutes
async def _get_all_x_from_db(db: AsyncSession, model, tournament_id: int) -> dict:
    """Get all records cached of a specific model from the database for a given tournament id.
    Args:
        db: The database session.
        model: The SQLAlchemy model to query.
        tournament_id (int): The tournament ID to filter by.
    Returns:
        dict: A dictionary of all records keyed by their football_data_org_id.
    """
    result = await db.execute(
        select(model)
        .where(model.tournament_id == tournament_id)
    )
    all_items = result.scalars().all()

    return {item.football_data_org_id if hasattr(item, "football_data_org_id") else item.name: item for item in all_items}


transform_name = lambda name: name.replace("_", " ").title()


async def _get_or_create_group(db: AsyncSession, tournament: Tournament, group_name: str) -> int:
    transformed_name = transform_name(group_name)
    all_groups_dict = await _get_all_x_from_db(db, Group, tournament.id)

    # group already exists
    if transformed_name in all_groups_dict:
        return all_groups_dict[transformed_name].id
    
    # group does not exist, create it
    else:
        new_group = Group(name=transformed_name, tournament_id=tournament.id)
        db.add(new_group)
        await db.flush()
        all_groups_dict[transformed_name] = new_group
        logger.info(f"Created new group '{transformed_name}' ({new_group.id}) for tournament '{tournament.name}' ({tournament.id})")
        return new_group.id


async def _get_or_create_stage(db: AsyncSession, tournament: Tournament, stage_name: str) -> int:
    transformed_name = transform_name(stage_name)
    all_stages_dict = await _get_all_x_from_db(db, Stage, tournament.id)

    # stage already exists
    if transformed_name in all_stages_dict:
        return all_stages_dict[transformed_name].id
    
    # stage does not exist, create it
    else:
        new_stage = Stage(name=transformed_name, tournament_id=tournament.id)
        db.add(new_stage)
        await db.flush()
        all_stages_dict[transformed_name] = new_stage
        logger.info(f"Created new stage '{transformed_name}' ({new_stage.id}) for tournament '{tournament.name}' ({tournament.id})")
        return new_stage.id


async def _get_or_create_team(db: AsyncSession, tournament: Tournament, team_data: dict) -> int:
    all_teams_dict = await _get_all_x_from_db(db, Team, tournament.id)
    team_fd_id = team_data["id"]

    # team already exists
    if team_fd_id in all_teams_dict:
        return all_teams_dict[team_fd_id].id
    
    # team does not exist, create it
    else:
        new_team = Team(
            name=team_data["name"],
            football_data_org_id=team_fd_id,
            iso_code=team_data.get("tla"),
            image_url=team_data.get("crest"),
            tournament_id=tournament.id,
            group_id=await _get_or_create_group(db, tournament, team_data["group"]) if team_data.get("group") else None,
        )
        db.add(new_team)
        await db.flush()
        all_teams_dict[team_fd_id] = new_team
        logger.info(f"Created new team '{new_team.name}' ({new_team.id}) for tournament '{tournament.name}' ({tournament.id})")
        return new_team.id
    

async def update_matches(db: AsyncSession, tournament: Tournament, force_refresh: bool = False) -> dict:

    fd_data = await api_request("matches", tournament.football_data_org_id)

    # check if no changes in match data since last update
    data_hash = hashlib.md5(str(fd_data).encode()).hexdigest()
    hash_file = _DATA_DIR / f"football_data_hash_{tournament.id}_matches.txt"
    if not force_refresh and hash_file.is_file() and hash_file.read_text().strip() == data_hash:
        logger.info(f"No match changes detected for tournament {tournament.id} — skipping update.")
        return

    result = await db.execute(
        select(Match)
        .where(Match.tournament_id == tournament.id)
    )
    all_matches = result.scalars().all()
    all_matches_dict = {match.football_data_org_id: match for match in all_matches}

    matches_recalculate_points = []

    for fd_match in fd_data["matches"]:
        fd_match_id = fd_match["id"]
        fd_start_datetime = datetime.datetime.fromisoformat(fd_match["utcDate"].replace("Z", "+00:00"))

        fd_status = fd_match["status"]
        fd_home_goals = None
        fd_away_goals = None
        if fd_status in ["FINISHED", "AWARDED"]:
            # final score - regular time + extra time + penalties
            if tournament.match_score_method == "final":
                fd_home_goals = max(0, fd_match["score"]["fullTime"]["home"])
                fd_away_goals = max(0, fd_match["score"]["fullTime"]["away"])
            # excluding penalties from the score - regular time + extra time (no penalties)
            elif tournament.match_score_method == "no-penalty":
                fd_home_goals = max(0, fd_match["score"]["fullTime"]["home"] - fd_match.get("score", {}).get("penalties", {}).get("home", 0))
                fd_away_goals = max(0, fd_match["score"]["fullTime"]["away"] - fd_match.get("score", {}).get("penalties", {}).get("away", 0))
            # only regular time - regular time (no extra time, no penalties)
            elif tournament.match_score_method == "regular-time":
                fd_home_goals = max(0, fd_match["score"]["fullTime"]["home"] - fd_match.get("score", {}).get("extraTime", {}).get("home", 0) - fd_match.get("score", {}).get("penalties", {}).get("home", 0))
                fd_away_goals = max(0, fd_match["score"]["fullTime"]["away"] - fd_match.get("score", {}).get("extraTime", {}).get("away", 0) - fd_match.get("score", {}).get("penalties", {}).get("away", 0))
        
        stage_id = await _get_or_create_stage(db, tournament, fd_match["stage"]) if fd_match["stage"] else None
        home_team_id = await _get_or_create_team(db, tournament, {**fd_match["homeTeam"], "group": fd_match.get("group")}) if fd_match["homeTeam"]["id"] else None
        away_team_id = await _get_or_create_team(db, tournament, {**fd_match["awayTeam"], "group": fd_match.get("group")}) if fd_match["awayTeam"]["id"] else None
        
        # new match
        if fd_match_id not in all_matches_dict:
            new_match = Match(
                football_data_org_id=fd_match_id,
                tournament_id=tournament.id,
                start_datetime=fd_start_datetime,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                stage_id=stage_id,
                home_goals=fd_home_goals,
                away_goals=fd_away_goals,
            )
            db.add(new_match)
            logger.info(f"Created new match {fd_start_datetime} ({new_match.football_data_org_id}) for tournament '{tournament.name}' ({tournament.id})")
        
        # existing match
        else:
            existing_match = all_matches_dict[fd_match_id]
            if (existing_match.home_goals != fd_home_goals) or (existing_match.away_goals != fd_away_goals):
                matches_recalculate_points.append(existing_match.id)
            existing_match.start_datetime = fd_start_datetime
            existing_match.home_team_id = home_team_id
            existing_match.away_team_id = away_team_id
            existing_match.stage_id = stage_id
            existing_match.home_goals = fd_home_goals
            existing_match.away_goals = fd_away_goals
            logger.info(f"Updated existing match {fd_start_datetime} ({existing_match.football_data_org_id}) for tournament '{tournament.name}' ({tournament.id})")
    
    await db.commit()

    for match_id in matches_recalculate_points:
        await predictions_scoring.recalculate_match_points(db, match_id)
    
    hash_file.write_text(data_hash)


async def update_ranking(db: AsyncSession, tournament: Tournament, force_refresh: bool = False):

    fd_data = await api_request("standings", tournament.football_data_org_id)
    fd_standings = [s for s in fd_data.get("standings", []) if s["type"] == "TOTAL" and s["stage"] == "ALL"]

    # check if no changes in ranking data since last update
    data_hash = hashlib.md5(str(fd_data).encode()).hexdigest()
    hash_file = _DATA_DIR / f"football_data_hash_{tournament.id}_rankings.txt"
    if not force_refresh and hash_file.is_file() and hash_file.read_text().strip() == data_hash:
        logger.info(f"No ranking changes detected for tournament {tournament.id} — skipping update.")
        return
    
    groups_recalculate_points = []

    for fd_standing in fd_standings:
        group_name = transform_name(fd_standing["group"])

        if "group" not in group_name.lower():
            logger.info(f"Skipping adding winner of non-group stage '{group_name}' for tournament '{tournament.name}' ({tournament.id}) as not implemented.")
            continue  # skip if not a group stage

        matched_group = await db.execute(
            select(Group)
            .where(Group.tournament_id == tournament.id)
            .where(Group.winner_team_id.is_(None))
            .where(Group.name == group_name)
        )
        matched_group = matched_group.scalars().first()

        if not matched_group:
            continue

        # Check if all group_stage matches have been played before assigning a winner
        max_group_match_datetime = await db.execute(
            select(func.max(Match.start_datetime))
            .where(Match.tournament_id == tournament.id)
            .where(Match.stage_id == select(Stage.id).where(Stage.tournament_id == tournament.id).where(Stage.name.ilike("%group%")).limit(1).scalar_subquery())
            .where(Match.home_team_id.in_(select(Team.id).where(Team.group_id == matched_group.id)))
            .where(Match.away_team_id.in_(select(Team.id).where(Team.group_id == matched_group.id)))
        )
        max_group_match_datetime = max_group_match_datetime.scalar()
        if max_group_match_datetime is None or max_group_match_datetime > datetime.datetime.now(ZoneInfo(settings.tz)):
            logger.info(f"Skipping adding winner of group '{group_name}' for tournament '{tournament.name}' ({tournament.id}) as not all matches have been played.")
            continue  # skip if not all matches have been played
        
        fd_winning_team = next((item["team"] for item in fd_standing["table"] if item["position"] == 1), None)
        winning_team_id = await _get_or_create_team(db, tournament, fd_winning_team)

        matched_group.winner_team_id = winning_team_id
        logger.info(f"Set winner of group '{group_name}' for tournament '{tournament.name}' ({tournament.id}) to team ID {winning_team_id}.")
        groups_recalculate_points.append(matched_group.id)
    
    await db.commit()

    for group_id in groups_recalculate_points:
        await predictions_scoring.recalculate_group_points(db, group_id)

    hash_file.write_text(data_hash)


async def update_tournament(db: AsyncSession, tournament: Tournament, force_refresh: bool = False):
    await update_matches(db, tournament, force_refresh=force_refresh)
    await update_ranking(db, tournament, force_refresh=force_refresh)


async def update_all_tournaments(
    db: AsyncSession,
    force_refresh: bool = False,
    lookback: datetime.timedelta | None = UPDATE_LOOKBACK,
):
    """Update tournaments linked to football-data.org.

    Args:
        db: The database session.
        force_refresh: Ignore the stored data hash and rewrite records even if unchanged.
        lookback: Only update tournaments with at least one match that kicked off within
            this window before now (default 48h). Pass ``None`` to update every tournament.
            Tournaments without any matches in the window — including ones with no matches
            at all — are skipped.
    """
    stmt = (
        select(Tournament)
        .where(Tournament.football_data_org_id.is_not(None))
    )

    if lookback is not None:
        now = datetime.datetime.now(datetime.timezone.utc)
        stmt = stmt.where(
            select(Match.id)
            .where(Match.tournament_id == Tournament.id)
            .where(Match.start_datetime >= now - lookback)
            .where(Match.start_datetime <= now)
            .exists()
        )

    result = await db.execute(stmt)
    tournament_lst = result.scalars().all()

    if lookback is not None:
        logger.info(
            f"Updating {len(tournament_lst)} tournament(s) with matches in the last "
            f"{lookback.total_seconds() / 3600:g}h"
        )

    for tournament in tournament_lst:
        try:
            await update_tournament(db, tournament, force_refresh=force_refresh)
        except Exception:
            logger.exception(f"Failed to update tournament {tournament.id}")


async def import_tournament(db: AsyncSession, tournament: Tournament):
    await update_matches(db, tournament)


if __name__ == "__main__":
    import sys
    from src.main import run_alembic_startup_workflow
    from src.scripts.load_test_data import load_test_data

    run_alembic_startup_workflow()

    async def _main():
        await load_test_data()
        async with AsyncSessionLocal() as db:
            await update_all_tournaments(db, force_refresh=True, lookback=None)

    asyncio.run(_main())