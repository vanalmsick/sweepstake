import asyncio
import fcntl
from datetime import datetime, timedelta, timezone
from typing import IO
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.api_football_data.football_data_org import update_all_tournaments
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

_SCHEDULER_LOCK_PATH = "/tmp/sweepstake_scheduler.lock"


def try_acquire_scheduler_lock() -> IO | None:
    """
    Non-blocking exclusive flock on a lock file. Returns the open file object
    on success — the caller must keep it open for the lock to remain held.
    Returns None if another worker already holds the lock.

    The OS releases the lock automatically when the process dies (any signal,
    including SIGKILL), so the lock can never be held forever.
    """
    fd = open(_SCHEDULER_LOCK_PATH, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        fd.close()
        return None


def release_scheduler_lock(fd: IO) -> None:
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()


async def _update_all_tournaments() -> None:
    from src.database import AsyncSessionLocal
    from src.api_football_data.football_data_org import update_all_tournaments

    async with AsyncSessionLocal() as db:
        await update_all_tournaments(db)


async def _cleanup_old_sessions() -> None:
    from src.database import AsyncSessionLocal
    from src.users.crud import delete_old_sessions

    async with AsyncSessionLocal() as db:
        deleted = await delete_old_sessions(db)
        logger.info("Session cleanup: deleted %d old session(s)", deleted)


async def _send_upcoming_match_reminders() -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.database import AsyncSessionLocal
    from src.matches.models import Match
    from src.predictions.models import PredictMatch
    from src.tournaments.models import Tournament
    from src.emails.upcoming_matches_email import send_upcoming_matches_email

    local_tz = ZoneInfo(settings.tz)
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=26)

    TIME_BUDGET_ALL_EMAILS_MINUTES = 60
    MIN_TIME_PER_EMAIL_SECONDS = 10
    MAX_TIME_PER_EMAIL_SECONDS = 30

    async with AsyncSessionLocal() as db:
        # Fetch all matches starting within the next 26 hours (with teams pre-loaded)
        matches_result = await db.execute(
            select(Match)
            .where(Match.start_datetime > now)
            .where(Match.start_datetime <= window_end)
            .options(selectinload(Match.home_team))
            .options(selectinload(Match.away_team))
            .order_by(Match.start_datetime)
        )
        upcoming_matches = matches_result.scalars().all()

        if not upcoming_matches:
            logger.info("Upcoming-matches reminder: no matches in next 26 h, skipping")
            return

        tournament_ids = list({m.tournament_id for m in upcoming_matches if m.tournament_id})
        WAIT_TIME_PER_EMAIL = TIME_BUDGET_ALL_EMAILS_MINUTES * 60 / max(len(tournament_ids), 1)

        for tid in tournament_ids:
            t_matches = [m for m in upcoming_matches if m.tournament_id == tid]
            match_ids = [m.id for m in t_matches]

            # Load tournament with admins and participants
            t_result = await db.execute(
                select(Tournament)
                .where(Tournament.id == tid)
                .options(selectinload(Tournament.admins))
                .options(selectinload(Tournament.participants))
                .options(selectinload(Tournament.matches))
            )
            tournament = t_result.scalar_one_or_none()
            if not tournament or not tournament.participants:
                continue

            participant_ids = [u.id for u in tournament.participants if u.id is not None]

            # Remind users to submit winner predictions if the tournament starts tomorrow
            tomorrow = (datetime.now(local_tz) + timedelta(days=1)).date()
            match_dates = [m.start_datetime.date() for m in tournament.matches if m.start_datetime is not None]
            tournament_start_date = min(match_dates) if match_dates else None
            winner_reminder = None
            if tournament_start_date == tomorrow:
                winner_reminder = {
                    "has_tournament": bool(tournament.first_place_points),
                    "has_groups": bool(tournament.group_winner_points),
                    "has_stages": bool(tournament.stage_winner_points),
                }
                if not any(winner_reminder.values()):
                    winner_reminder = None

            # Bulk-fetch all predictions for these matches × participants
            pred_result = await db.execute(
                select(PredictMatch).where(
                    PredictMatch.match_id.in_(match_ids),
                    PredictMatch.user_id.in_(participant_ids),
                )
            )
            predictions = pred_result.scalars().all()
            pred_map = {(p.match_id, p.user_id): p for p in predictions}

            admins_info = [
                {
                    "first_name": a.first_name,
                    "last_name": a.last_name,
                    "email": a.email,
                }
                for a in tournament.admins
            ]

            WAIT_TIME_PER_EMAIL = WAIT_TIME_PER_EMAIL / max(len(tournament.participants), 1)
            WAIT_TIME_PER_EMAIL = max(MIN_TIME_PER_EMAIL_SECONDS, min(WAIT_TIME_PER_EMAIL, MAX_TIME_PER_EMAIL_SECONDS))

            for user in tournament.participants:
                if not user.is_active or not user.email:
                    continue

                match_rows = []
                for m in t_matches:
                    pred = pred_map.get((m.id, user.id))
                    dt_local = m.start_datetime
                    if dt_local.tzinfo is None:
                        dt_local = dt_local.replace(tzinfo=timezone.utc)
                    dt_local = dt_local.astimezone(local_tz)
                    match_rows.append({
                        "date_line": dt_local.strftime("%a"),
                        "time_line": dt_local.strftime("%H:%M"),
                        "home_team_name": m.home_team.name if m.home_team else "—",
                        "home_team_image_url": m.home_team.image_url if m.home_team else None,
                        "away_team_name": m.away_team.name if m.away_team else "—",
                        "away_team_image_url": m.away_team.image_url if m.away_team else None,
                        "pred_home_score": pred.home_score if pred else None,
                        "pred_away_score": pred.away_score if pred else None,
                        "tv_channel": m.tv_channel,
                    })

                await send_upcoming_matches_email(
                    to_email=user.email,
                    first_name=user.first_name,
                    tournament_name=tournament.name,
                    tournament_id=tid,
                    matches=match_rows,
                    admins=admins_info,
                    user_id=user.id,
                    winner_reminder=winner_reminder,
                    match_score_method=tournament.match_score_method,
                )
                logger.info(
                    "Upcoming-matches reminder sent: user_id=%d tournament_id=%d matches=%d",
                    user.id, tid, len(match_rows),
                )

                await asyncio.sleep(WAIT_TIME_PER_EMAIL)


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.tz)
    scheduler.add_job(
        _cleanup_old_sessions,
        CronTrigger(hour=5, minute=0, timezone=settings.tz),
    )
    if settings.email_host:
        scheduler.add_job(
            _send_upcoming_match_reminders,
            CronTrigger(hour=15, minute=0, timezone=settings.tz),
        )
    if settings.football_data_org_api_key:
        scheduler.add_job(
            _update_all_tournaments,
            CronTrigger(minute="*/30", timezone=settings.tz),
        )
    return scheduler
