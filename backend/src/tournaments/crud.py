import re
import random
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, nullslast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from src.api_football_data.football_data_org import import_tournament
from src.tournaments import models
from src.matches.models import Match
from src.predictions import scoring as predictions_scoring


# ============================================================================
# Tournament CRUD operations
# ============================================================================

def _query_tournament():
    """Base select statement for querying"""
    return (select(models.Tournament)
        .options(selectinload(models.Tournament.admins))
        .options(selectinload(models.Tournament.participants))
        .options(selectinload(models.Tournament.participant_links)))


def _query_tournaments(user_id: int = None):
    """Select statement for querying with filtering on user_id for access filtering"""
    query = _query_tournament()
    if user_id is not None:
        query = query.where(
            or_(
                models.Tournament.id.in_(
                    select(models.TournamentAdminLink.tournament_id).where(models.TournamentAdminLink.user_id == user_id)
                ),
                models.Tournament.id.in_(
                    select(models.TournamentParticipantLink.tournament_id).where(models.TournamentParticipantLink.user_id == user_id)
                ),
            )
        )
    _end_date = (
        select(func.max(Match.start_datetime))
        .where(Match.tournament_id == models.Tournament.id)
        .correlate(models.Tournament)
        .scalar_subquery()
    )
    _start_date = (
        select(func.min(Match.start_datetime))
        .where(Match.tournament_id == models.Tournament.id)
        .correlate(models.Tournament)
        .scalar_subquery()
    )
    return query.order_by(nullslast(_end_date), nullslast(_start_date), models.Tournament.name)


async def is_admin(db: AsyncSession, tournament_id: int, user_id: int) -> bool:
    """Return True if the user is an admin of the tournament."""
    result = await db.execute(
        select(models.TournamentAdminLink).where(
            models.TournamentAdminLink.tournament_id == tournament_id,
            models.TournamentAdminLink.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


def _generate_join_code(name: str, user_id: int) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', name)[:8] + str(user_id).zfill(3) + str(random.randint(10_000, 99_999))


async def create_tournament(db: AsyncSession, tournament: models.TournamentCreate, user_id: int):
    """Create a new tournament and add the creator as an admin."""
    db_tournament = models.Tournament(
        name=tournament.name,
        stake=tournament.stake,
        football_data_org_id=tournament.football_data_org_id,
        first_place_team_id=tournament.first_place_team_id,
        second_place_team_id=tournament.second_place_team_id,
        third_place_team_id=tournament.third_place_team_id,
        first_place_points=tournament.first_place_points,
        second_place_points=tournament.second_place_points,
        third_place_points=tournament.third_place_points,
        match_winner_points=tournament.match_winner_points,
        match_score_points=tournament.match_score_points,
        group_winner_points=tournament.group_winner_points,
        stage_winner_points=tournament.stage_winner_points,
        predictions_open=tournament.predictions_open,
        match_score_method=tournament.match_score_method,
        join_code=_generate_join_code(tournament.name, user_id)
    )
    db.add(db_tournament)
    await db.flush()  # populate db_tournament.id

    # Add creator as admin and participant
    db.add(models.TournamentAdminLink(tournament_id=db_tournament.id, user_id=user_id))
    db.add(models.TournamentParticipantLink(tournament_id=db_tournament.id, user_id=user_id))

    await db.commit()

    # If football_data_org_id is provided, import tournament data from football-data.org
    if tournament.football_data_org_id is not None:
        await import_tournament(db, db_tournament)

    return await get_tournament_by_id(db, db_tournament.id)


async def get_tournament_by_id(db: AsyncSession, tournament_id: int, refetch: bool = False):
    """Get a tournament by ID."""
    query = _query_tournament().where(models.Tournament.id == tournament_id).execution_options(populate_existing=refetch)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def delete_tournament(db: AsyncSession, tournament_id: int):
    """Delete a tournament."""
    db_tournament = await db.get(models.Tournament, tournament_id)
    if db_tournament:
        await db.delete(db_tournament)
        await db.commit()
    return db_tournament


async def update_tournament(
    db: AsyncSession,
    tournament_id: int,
    tournament_update: models.TournamentUpdate,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """Update a tournament."""
    db_tournament = await db.get(models.Tournament, tournament_id)
    if not db_tournament:
        return None

    _TOURNAMENT_SCORING_FIELDS = {
        "first_place_team_id",
        "second_place_team_id",
        "third_place_team_id",
        "first_place_points",
        "second_place_points",
        "third_place_points",
    }
    _MATCH_SCORING_FIELDS = {"match_winner_points", "match_score_points", "match_score_method"}
    _GROUP_SCORING_FIELDS = {"group_winner_points"}
    _STAGE_SCORING_FIELDS = {"stage_winner_points"}

    update_data = tournament_update.model_dump(exclude_unset=True, exclude={"admin_ids"})
    recalculate = bool(_TOURNAMENT_SCORING_FIELDS & update_data.keys())
    recalculate_matches = bool(_MATCH_SCORING_FIELDS & update_data.keys())
    recalculate_groups = bool(_GROUP_SCORING_FIELDS & update_data.keys())
    recalculate_stages = bool(_STAGE_SCORING_FIELDS & update_data.keys())

    for field, value in update_data.items():
        setattr(db_tournament, field, value)

    if "admin_ids" in tournament_update.model_fields_set:
        # Replace admin list (creator always remains an admin)
        await db.execute(
            models.TournamentAdminLink.__table__.delete().where(
                models.TournamentAdminLink.tournament_id == tournament_id
            )
        )
        admin_ids = set(tournament_update.admin_ids)
        for aid in admin_ids:
            db.add(models.TournamentAdminLink(tournament_id=tournament_id, user_id=aid))

    await db.commit()
    if recalculate:
        if background_tasks is not None:
            background_tasks.add_task(predictions_scoring.background_recalculate_tournament_points, tournament_id)
        else:
            await predictions_scoring.background_recalculate_tournament_points(tournament_id)
    if recalculate_matches:
        if background_tasks is not None:
            background_tasks.add_task(predictions_scoring.background_recalculate_all_match_points_for_tournament, tournament_id)
        else:
            await predictions_scoring.background_recalculate_all_match_points_for_tournament(tournament_id)
    if recalculate_groups:
        if background_tasks is not None:
            background_tasks.add_task(predictions_scoring.background_recalculate_all_group_points_for_tournament, tournament_id)
        else:
            await predictions_scoring.background_recalculate_all_group_points_for_tournament(tournament_id)
    if recalculate_stages:
        if background_tasks is not None:
            background_tasks.add_task(predictions_scoring.background_recalculate_all_stage_points_for_tournament, tournament_id)
        else:
            await predictions_scoring.background_recalculate_all_stage_points_for_tournament(tournament_id)
    return await get_tournament_by_id(db, tournament_id, refetch=True)


async def join_tournament(
    db: AsyncSession,
    tournament_join_code: int,
    user_id: int,
) -> tuple:
    """Add user as tournament participant. Returns (tournament, already_member)."""
    result = await db.execute(select(models.Tournament).where(models.Tournament.join_code == tournament_join_code))
    db_tournament = result.scalars().first()
    if not db_tournament:
        return None, False
    tournament_id = db_tournament.id
    existing = await db.execute(
        select(models.TournamentParticipantLink).where(
            models.TournamentParticipantLink.tournament_id == tournament_id,
            models.TournamentParticipantLink.user_id == user_id,
        )
    )
    if existing.scalars().first():
        return await get_tournament_by_id(db, tournament_id, refetch=True), True
    db.add(models.TournamentParticipantLink(tournament_id=tournament_id, user_id=user_id))
    await db.commit()
    return await get_tournament_by_id(db, tournament_id, refetch=True), False


async def leave_tournament(db: AsyncSession, tournament_id: int, user_id: int):
    """Remove user as tournament participant."""
    result = await db.execute(
        models.TournamentParticipantLink.__table__.delete().where(
            models.TournamentParticipantLink.tournament_id == tournament_id,
            models.TournamentParticipantLink.user_id == user_id,
        )
    )
    await db.commit()
    return result.rowcount  # 0 = nothing found, 1 = deleted


async def manage_tournament_member(
    db: AsyncSession,
    tournament_id: int,
    user_id: int,
    role: str,
    action: str,
) -> tuple[models.Tournament | None, str | None]:
    """Add or remove a user as admin/participant of a tournament.

    Returns (tournament, error_message). error_message is None on success.
    """
    link_model = models.TournamentAdminLink if role == "admin" else models.TournamentParticipantLink

    if action == "add":
        db.add(link_model(tournament_id=tournament_id, user_id=user_id))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            # Already exists — treat as success
    else:  # remove
        result = await db.execute(
            link_model.__table__.delete().where(
                link_model.tournament_id == tournament_id,
                link_model.user_id == user_id,
            )
        )
        await db.commit()
        if result.rowcount == 0:
            return None, "User is not a member with that role in this tournament"

    tournament = await get_tournament_by_id(db, tournament_id, refetch=True)
    if tournament is None:
        # Tournament was auto-deleted because the last admin was removed
        return None, None
    return tournament, None


async def set_stake_paid(db: AsyncSession, tournament_id: int, user_id: int, stake_paid: bool) -> bool:
    """Update stake_paid on a participant link. Returns False if the participant was not found."""
    result = await db.execute(
        select(models.TournamentParticipantLink).where(
            models.TournamentParticipantLink.tournament_id == tournament_id,
            models.TournamentParticipantLink.user_id == user_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        return False
    link.stake_paid = stake_paid
    await db.commit()
    return True
