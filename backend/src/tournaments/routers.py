"""Tournament management routes: create, read, update, delete operations."""

import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, Response, status, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.exceptions import CustomError
from src.utils import stream_model_results, create_stream_response
from src.tournaments import crud, models
from src.users.routers import verify_access_token
from src.users.crud import get_user_by_id
from src.emails.welcome_email import send_competition_welcome_email
from src.emails.payment_reminder_email import send_payment_reminder_email
from src.api_football_data.football_data_org import update_tournament
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tournament", tags=["tournament"])


@router.post("", response_model=models.TournamentRead, status_code=status.HTTP_201_CREATED)
async def create_tournament_endpoint(
    tournament: models.TournamentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Create a new tournament.

    - **name**: Tournament name (required)
    - **stake**: Optional multi-line text describing the stake or prize for the tournament
    - **football_data_org_id**: Optional football-data.org tournament ID for automatic schedule and score fetching
    - **first_place_team_id**: Optional team ID for the tournament winner
    - **second_place_team_id**: Optional team ID for the runner-up
    - **third_place_team_id**: Optional team ID for third place
    - **first_place_points**: Points for correctly predicting the tournament winner (default: 25)
    - **second_place_points**: Points for correctly predicting the runner-up (default: 15)
    - **third_place_points**: Points for correctly predicting third place (default: null/disabled)
    - **match_winner_points**: Points for correctly predicting the winning team of a match (default: 5)
    - **match_score_points**: Points for correctly predicting the exact score of a match (default: 3)
    - **group_winner_points**: Points for correctly predicting the winner of a group (default: null/disabled)
    - **stage_winner_points**: Points for correctly predicting the winner of a knockout stage (default: null/disabled)
    - **predictions_open**: Control when predictions can be submitted: 'automatic' (default), 'open', or 'closed'
    - **match_score_method**: Which score to use for match predictions: 'final' (regular + extra + penalties), 'no-penalty' (default, regular + extra), 'regular-time' (regular time only)

    Returns the created tournament with its ID.  A welcome email is dispatched to the creator in the background.
    """
    user_id = token_payload["uid"]
    if settings.only_superusers_can_create_tournaments:
        creator = await get_user_by_id(db, user_id)
        if not creator or not creator.is_superuser:
            raise CustomError("Only superusers can create tournaments", status_code=403)
    new_tournament = await crud.create_tournament(db, tournament, user_id=user_id)
    user = await get_user_by_id(db, user_id)
    if user:
        admins = [
            {"first_name": a.first_name, "last_name": a.last_name, "email": a.email}
            for a in new_tournament.admins
        ]
        background_tasks.add_task(
            send_competition_welcome_email,
            to_email=user.email,
            first_name=user.first_name,
            tournament_name=new_tournament.name,
            tournament_id=new_tournament.id,
            stake=new_tournament.stake,
            match_winner_points=new_tournament.match_winner_points,
            match_score_points=new_tournament.match_score_points,
            group_winner_points=new_tournament.group_winner_points,
            stage_winner_points=new_tournament.stage_winner_points,
            first_place_points=new_tournament.first_place_points,
            second_place_points=new_tournament.second_place_points,
            third_place_points=new_tournament.third_place_points,
            match_score_method=new_tournament.match_score_method,
            admins=admins,
            user_id=user_id,
        )
    return new_tournament


@router.get("", response_model=list[models.TournamentRead])
async def get_all_tournaments_endpoint(
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve all tournaments.
    
    Returns a list of all tournaments in the system, ordered by creation date.
    """
    result = await db.execute(crud._query_tournaments(user_id=token_payload["uid"]))
    return result.scalars().all()


@router.get("/stream", response_class=StreamingResponse)
async def stream_all_tournaments_endpoint(
    batch_size: int = Query(1, description="Number of tournaments per batch", ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Stream tournaments as newline-delimited JSON.
    
    Useful for handling large numbers of tournaments without loading all into memory.
    
    - **batch_size**: Number of records to fetch per batch (default: 1, max: 1000)
    
    Returns tournaments as a streaming response in NDJSON format.
    """
    query = crud._query_tournaments(user_id=token_payload["uid"])
    generator = stream_model_results(db, query, batch_size=batch_size)
    return create_stream_response(generator)


@router.get("/{tournament_id}", response_model=models.TournamentRead)
async def get_tournament_endpoint(
    tournament_id: int = Path(..., description="Unique tournament identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Retrieve a specific tournament by ID.
    
    - **tournament_id**: The unique identifier of the tournament
    
    Returns the tournament details or 404 if not found.
    """
    user_id=token_payload["uid"]
    tournament = await crud.get_tournament_by_id(db, tournament_id)
    if not tournament:
        raise CustomError("Tournament not found", status_code=404)
    if not any(i.id == user_id for i in tournament.participants) and not any(i.id == user_id for i in tournament.admins):
        raise CustomError("Forbidden: only participants and admins can view a tournament", status_code=403)
    return tournament


@router.patch("/{tournament_id}", response_model=models.TournamentRead)
async def patch_tournament_endpoint(
    background_tasks: BackgroundTasks,
    tournament_id: int = Path(..., description="Unique tournament identifier", gt=0),
    tournament: models.TournamentUpdate = None,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Update an existing tournament (admins only).

    - **tournament_id**: The unique identifier of the tournament to update
    - **name**: Tournament name
    - **football_data_org_id**: Optional football-data.org tournament ID for automatic schedule and score fetching
    - **first_place_team_id**: Optional team ID for the tournament winner
    - **second_place_team_id**: Optional team ID for the runner-up
    - **third_place_team_id**: Optional team ID for third place
    - **first_place_points**: Points for correctly predicting the tournament winner (default: 25)
    - **second_place_points**: Points for correctly predicting the runner-up (default: 15)
    - **third_place_points**: Points for correctly predicting third place (default: null/disabled)
    - **match_winner_points**: Points for correctly predicting the winning team of a match (default: 5)
    - **match_score_points**: Points for correctly predicting the exact score of a match (default: 3)
    - **group_winner_points**: Points for correctly predicting the winner of a group (default: null/disabled)
    - **stage_winner_points**: Points for correctly predicting the winner of a knockout stage (default: null/disabled)
    - **predictions_open**: Control when predictions can be submitted: 'automatic', 'open', or 'closed'
    - **match_score_method**: Which score to use for match predictions: 'final' (regular + extra + penalties), 'no-penalty' (regular + extra), 'regular-time' (regular time only)

    Returns the updated tournament details or 404 if not found.
    """
    if not await crud.is_admin(db, tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only admins can modify a tournament", status_code=403)
    result = await crud.update_tournament(db, tournament_id, tournament, background_tasks)
    if not result:
        raise CustomError("Tournament not found", status_code=404)
    return result


@router.delete("/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tournament_endpoint(
    tournament_id: int = Path(..., description="Unique tournament identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Delete a tournament (admins only).

    - **tournament_id**: The unique identifier of the tournament to delete

    Returns 204 No Content on success or 404 if not found.
    """
    if not await crud.is_admin(db, tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only admins can delete a tournament", status_code=403)
    result = await crud.delete_tournament(db, tournament_id)
    if not result:
        raise CustomError("Tournament not found", status_code=404)
    return None


@router.patch("/{tournament_id}/members", response_model=models.TournamentRead, responses={204: {"description": "Tournament deleted (last admin removed)"}})
async def manage_tournament_member_endpoint(
    member: models.TournamentMemberUpdate,
    tournament_id: int = Path(..., description="Unique tournament identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Add or remove a user as admin or participant (admins only).

    - **tournament_id**: The unique identifier of the tournament
    - **user_id**: ID of the user to add or remove
    - **role**: `admin` or `participant`
    - **action**: `add` or `remove`

    Removing the last admin deletes the tournament and returns 204 No Content.
    """
    if not await crud.is_admin(db, tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only admins can manage tournament members", status_code=403)
    tournament, error = await crud.manage_tournament_member(
        db, tournament_id, member.user_id, member.role, member.action
    )
    if error:
        raise CustomError(error, status_code=404)
    if tournament is None:
        # Last admin removed — tournament was auto-deleted
        return Response(status_code=204)
    return tournament


@router.patch("/{tournament_id}/stake-paid", response_model=models.TournamentRead)
async def set_stake_paid_endpoint(
    body: models.TournamentStakePaidUpdate,
    tournament_id: int = Path(..., description="Unique tournament identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Mark or unmark a participant's stake as paid (admins only).

    - **tournament_id**: The unique identifier of the tournament
    - **user_id**: ID of the participant
    - **stake_paid**: True to mark as paid, False to mark as unpaid

    Returns the updated tournament or 404 if the participant was not found.
    """
    if not await crud.is_admin(db, tournament_id, token_payload["uid"]):
        raise CustomError("Forbidden: only admins can update stake payment status", status_code=403)
    found = await crud.set_stake_paid(db, tournament_id, body.user_id, body.stake_paid)
    if not found:
        raise CustomError("Participant not found in this tournament", status_code=404)
    return await crud.get_tournament_by_id(db, tournament_id, refetch=True)


@router.post("/join/{join_code}", response_model=models.TournamentRead)
async def join_tournament_endpoint(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    join_code: str = Path(..., description="Unique tournament join code"),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Join a tournament as participant.

    - **join_code**: Join code shared by organiser or member to join an existing competition

    Returns the joined tournament.  A welcome email is dispatched in the background.
    """
    user_id = token_payload["uid"]
    tournament, already_member = await crud.join_tournament(db, tournament_join_code=join_code, user_id=user_id)
    if not tournament:
        raise CustomError("Tournament not found", status_code=404)
    if already_member:
        raise CustomError("You are already a member of this tournament", status_code=409)
    user = await get_user_by_id(db, user_id)
    if user:
        admins = [
            {"first_name": a.first_name, "last_name": a.last_name, "email": a.email}
            for a in tournament.admins
        ]
        background_tasks.add_task(
            send_competition_welcome_email,
            to_email=user.email,
            first_name=user.first_name,
            tournament_name=tournament.name,
            tournament_id=tournament.id,
            stake=tournament.stake,
            match_winner_points=tournament.match_winner_points,
            match_score_points=tournament.match_score_points,
            group_winner_points=tournament.group_winner_points,
            stage_winner_points=tournament.stage_winner_points,
            first_place_points=tournament.first_place_points,
            second_place_points=tournament.second_place_points,
            third_place_points=tournament.third_place_points,
            admins=admins,
            user_id=user_id,
        )
    return tournament


_TIME_BUDGET_EMAILS_MINUTES = 30
_MIN_EMAIL_GAP_SECONDS = 10
_MAX_EMAIL_GAP_SECONDS = 30


def _email_wait(n: int) -> float:
    """Seconds to sleep between emails so n emails spread over the budget window."""
    per_email = _TIME_BUDGET_EMAILS_MINUTES * 60 / max(n, 1)
    return max(_MIN_EMAIL_GAP_SECONDS, min(per_email, _MAX_EMAIL_GAP_SECONDS))


async def _bulk_send_payment_reminders(
    recipients: list[dict],
    stake: str,
    tournament_name: str,
    tournament_id: int,
    requesting_admin: dict,
    all_admins: list[dict],
    wait_seconds: float,
) -> None:
    logger.info(
        "Payment reminder task started | tournament_id=%s tournament=%r recipients=%d gap=%.0fs",
        tournament_id, tournament_name, len(recipients), wait_seconds,
    )
    for r in recipients:
        await send_payment_reminder_email(
            to_email=r["email"],
            first_name=r["first_name"],
            tournament_name=tournament_name,
            tournament_id=tournament_id,
            stake=stake,
            admin=requesting_admin,
            all_admins=all_admins,
            user_id=r["user_id"],
        )
        await asyncio.sleep(wait_seconds)
    logger.info(
        "Payment reminder task finished | tournament_id=%s sent=%d",
        tournament_id, len(recipients),
    )


async def _bulk_send_welcome_emails(
    recipients: list[dict],
    tournament_name: str,
    tournament_id: int,
    stake,
    match_winner_points,
    match_score_points,
    group_winner_points,
    stage_winner_points,
    first_place_points,
    second_place_points,
    third_place_points,
    match_score_method,
    requesting_admin: dict,
    wait_seconds: float,
) -> None:
    logger.info(
        "Welcome email task started | tournament_id=%s tournament=%r recipients=%d gap=%.0fs",
        tournament_id, tournament_name, len(recipients), wait_seconds,
    )
    for r in recipients:
        await send_competition_welcome_email(
            to_email=r["email"],
            first_name=r["first_name"],
            tournament_name=tournament_name,
            tournament_id=tournament_id,
            stake=stake,
            match_winner_points=match_winner_points,
            match_score_points=match_score_points,
            group_winner_points=group_winner_points,
            stage_winner_points=stage_winner_points,
            first_place_points=first_place_points,
            second_place_points=second_place_points,
            third_place_points=third_place_points,
            match_score_method=match_score_method,
            admins=[requesting_admin],
            user_id=r["user_id"],
        )
        await asyncio.sleep(wait_seconds)
    logger.info(
        "Welcome email task finished | tournament_id=%s sent=%d",
        tournament_id, len(recipients),
    )


@router.post("/{tournament_id}/action", status_code=status.HTTP_204_NO_CONTENT)
async def tournament_admin_action_endpoint(
    body: models.TournamentAdminActionRequest,
    background_tasks: BackgroundTasks,
    tournament_id: int = Path(..., description="Unique tournament identifier", gt=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Perform an admin action on a tournament (admins only).

    - **tournament_id**: The unique identifier of the tournament
    - **action**: One of:
      - `send-payment-reminder` — email all participants whose stake is unpaid
      - `update-tournament` — re-import schedule and results from football-data.org (requires `football_data_org_id`)
      - `send-welcome-email` — re-send the welcome email to all participants

    Returns 204 No Content on success.
    """
    user_id = token_payload["uid"]
    if not await crud.is_admin(db, tournament_id, user_id):
        raise CustomError("Forbidden: only admins can perform tournament actions", status_code=403)
    tournament = await crud.get_tournament_by_id(db, tournament_id)
    if not tournament:
        raise CustomError("Tournament not found", status_code=404)

    requesting_user = await get_user_by_id(db, user_id)
    requesting_admin = {
        "first_name": requesting_user.first_name,
        "last_name": requesting_user.last_name,
        "email": requesting_user.email,
    } if requesting_user else {}

    all_admins = [
        {"first_name": a.first_name, "last_name": a.last_name, "email": a.email}
        for a in tournament.admins
    ]

    if body.action == models.TournamentAdminAction.send_payment_reminder:
        if not tournament.stake:
            raise CustomError("This tournament has no stake configured", status_code=400)
        stake_paid_map = {link.user_id: link.stake_paid for link in tournament.participant_links}
        recipients = [
            {"email": u.email, "first_name": u.first_name, "user_id": u.id}
            for u in tournament.participants
            if not stake_paid_map.get(u.id, False)
        ]
        background_tasks.add_task(
            _bulk_send_payment_reminders,
            recipients=recipients,
            stake=tournament.stake,
            tournament_name=tournament.name,
            tournament_id=tournament.id,
            requesting_admin=requesting_admin,
            all_admins=all_admins,
            wait_seconds=_email_wait(len(recipients)),
        )

    elif body.action == models.TournamentAdminAction.update_tournament:
        if not tournament.football_data_org_id:
            raise CustomError("This tournament has no football-data.org ID configured", status_code=400)
        background_tasks.add_task(update_tournament, db, tournament)

    elif body.action == models.TournamentAdminAction.send_welcome_email:
        recipients = [
            {"email": u.email, "first_name": u.first_name, "user_id": u.id}
            for u in tournament.participants
        ]
        background_tasks.add_task(
            _bulk_send_welcome_emails,
            recipients=recipients,
            tournament_name=tournament.name,
            tournament_id=tournament.id,
            stake=tournament.stake,
            match_winner_points=tournament.match_winner_points,
            match_score_points=tournament.match_score_points,
            group_winner_points=tournament.group_winner_points,
            stage_winner_points=tournament.stage_winner_points,
            first_place_points=tournament.first_place_points,
            second_place_points=tournament.second_place_points,
            third_place_points=tournament.third_place_points,
            match_score_method=tournament.match_score_method,
            requesting_admin=requesting_admin,
            wait_seconds=_email_wait(len(recipients)),
        )

    logger.info(
        "Admin action triggered | action=%s tournament_id=%s tournament=%r by user_id=%s",
        body.action, tournament_id, tournament.name, user_id,
    )
    return None


@router.delete("/leave/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
async def leave_tournament_endpoint(
    db: AsyncSession = Depends(get_db),
    tournament_id: int = Path(..., description="Unique tournament identifier", gt=0),
    token_payload: dict = Depends(verify_access_token),
):
    """
    Leave a tournament as participant.

    - **tournament_id**: The unique identifier of the tournament to leave

    Returns 204 No Content on success or 404 if not found.
    """
    result = await crud.leave_tournament(db, tournament_id=tournament_id, user_id=token_payload["uid"])
    if result == 0:
        raise CustomError("Tournament participation not found", status_code=404)
    return None
