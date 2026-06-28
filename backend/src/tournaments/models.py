from datetime import date
from enum import Enum
from typing import Optional, List

import sqlalchemy as sa
from pydantic import ConfigDict, model_validator
from sqlalchemy import event, select, func
from sqlalchemy.orm import Session as SyncSession
from sqlmodel import SQLModel, Field, Relationship

from src.utils import all_optional
from src.teams.models import Team, TeamRead
from src.matches.models import Match  # noqa: F401 — needed for Tournament.matches relationship


# ---------------------------------------------------------------------------
# Link tables (many-to-many)
# ---------------------------------------------------------------------------

class TournamentAdminLink(SQLModel, table=True):
    __tablename__ = "tournament_admin"
    tournament_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )
    user_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )


class TournamentParticipantLink(SQLModel, table=True):
    __tablename__ = "tournament_participant"
    tournament_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("tournament.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )
    user_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )
    stake_paid: bool = Field(default=False, sa_column=sa.Column(sa.Boolean, default=False, nullable=False))


# ---------------------------------------------------------------------------
# Base / DB model
# ---------------------------------------------------------------------------

class PredictionsOpen(str, Enum):
    automatic = "automatic"
    open = "open"
    closed = "closed"


class MatchScoreMethod(str, Enum):
    final = "final"
    no_penalty = "no-penalty"
    regular_time = "regular-time"


class TournamentBase(SQLModel):
    """Shared tournament fields used across create, read, and update schemas."""
    name: str = Field(..., min_length=1, max_length=255)
    stake: Optional[str] = Field(default=None)
    football_data_org_id: Optional[int] = Field(default=None, unique=False)
    first_place_team_id: Optional[int] = Field(default=None)
    second_place_team_id: Optional[int] = Field(default=None)
    third_place_team_id: Optional[int] = Field(default=None)
    first_place_points: Optional[int] = Field(default=25, ge=0)
    second_place_points: Optional[int] = Field(default=15, ge=0)
    third_place_points: Optional[int] = Field(default=0, ge=0)
    match_winner_points: Optional[int] = Field(default=3, ge=0)
    match_score_points: Optional[int] = Field(default=5, ge=0)
    group_winner_points: Optional[int] = Field(default=8, ge=0)
    stage_winner_points: Optional[int] = Field(default=0, ge=0)
    predictions_open: PredictionsOpen = Field(default=PredictionsOpen.automatic)
    match_score_method: MatchScoreMethod = Field(default=MatchScoreMethod.no_penalty)


class Tournament(TournamentBase, table=True):
    __tablename__ = "tournament"

    id: Optional[int] = Field(default=None, primary_key=True)
    join_code: Optional[str] = Field(default=None, unique=True, max_length=16)
    stake: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))
    predictions_open: PredictionsOpen = Field(
        default=PredictionsOpen.automatic,
        sa_column=sa.Column(sa.String(16), nullable=False, default="automatic", server_default="automatic"),
    )
    match_score_method: MatchScoreMethod = Field(
        default=MatchScoreMethod.no_penalty,
        sa_column=sa.Column(sa.String(16), nullable=False, default="no-penalty", server_default="no-penalty"),
    )
    football_data_org_id: Optional[int] = Field(default=None, unique=False)
    first_place_team_id: Optional[int] = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("team.id", use_alter=True, name="fk_tournament_first_place_team_id"), nullable=True))
    second_place_team_id: Optional[int] = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("team.id", use_alter=True, name="fk_tournament_second_place_team_id"), nullable=True))
    third_place_team_id: Optional[int] = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("team.id", use_alter=True, name="fk_tournament_third_place_team_id"), nullable=True))
    admins: List["User"] = Relationship(link_model=TournamentAdminLink, sa_relationship_kwargs={"lazy": "selectin"})  # type: ignore[name-defined]
    participants: List["User"] = Relationship(link_model=TournamentParticipantLink, sa_relationship_kwargs={"lazy": "selectin"})  # type: ignore[name-defined]
    participant_links: List[TournamentParticipantLink] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Tournament.id == TournamentParticipantLink.tournament_id",
            "foreign_keys": "[TournamentParticipantLink.tournament_id]",
            "lazy": "selectin",
            "viewonly": True,
        }
    )
    matches: List[Match] = Relationship(sa_relationship_kwargs={"primaryjoin": "Tournament.id == Match.tournament_id", "foreign_keys": "[Match.tournament_id]", "lazy": "selectin"})
    first_place: Optional[Team] = Relationship(sa_relationship_kwargs={"primaryjoin": "Tournament.first_place_team_id == Team.id", "foreign_keys": "[Tournament.first_place_team_id]", "lazy": "selectin"})
    second_place: Optional[Team] = Relationship(sa_relationship_kwargs={"primaryjoin": "Tournament.second_place_team_id == Team.id", "foreign_keys": "[Tournament.second_place_team_id]", "lazy": "selectin"})
    third_place: Optional[Team] = Relationship(sa_relationship_kwargs={"primaryjoin": "Tournament.third_place_team_id == Team.id", "foreign_keys": "[Tournament.third_place_team_id]", "lazy": "selectin"})


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class TournamentCreate(TournamentBase):
    """Body for POST /tournament."""


@all_optional
class TournamentUpdate(TournamentBase):
    """Body for PATCH /tournament/{id} — all fields optional."""


class MemberRole(str, Enum):
    admin = "admin"
    participant = "participant"


class MemberAction(str, Enum):
    add = "add"
    remove = "remove"


class TournamentAdminAction(str, Enum):
    send_payment_reminder = "send-payment-reminder"
    update_tournament = "update-tournament"
    send_welcome_email = "send-welcome-email"


class TournamentAdminActionRequest(SQLModel):
    """Body for POST /tournament/{id}/action."""
    action: TournamentAdminAction = Field(..., description="Admin action to perform")


class TournamentMemberUpdate(SQLModel):
    """Body for PATCH /tournament/{id}/members."""
    user_id: int = Field(..., description="ID of the user to add or remove", gt=0)
    role: MemberRole = Field(..., description="Role to assign: 'admin' or 'participant'")
    action: MemberAction = Field(..., description="Action to perform: 'add' or 'remove'")


class TournamentStakePaidUpdate(SQLModel):
    """Body for PATCH /tournament/{id}/stake-paid."""
    user_id: int = Field(..., description="ID of the participant", gt=0)
    stake_paid: bool = Field(..., description="Whether the participant has paid the stake")


class TournamentRead(TournamentBase):
    """Response model returned by all tournament endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    join_code: str
    football_data_org_id: Optional[int] = None
    admin_lst: List[dict] = Field(default_factory=list, description="List of admin users with id and user_name")
    participant_lst: List[dict] = Field(default_factory=list, description="List of participant users with id and user_name")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    first_place: Optional[TeamRead] = None
    second_place: Optional[TeamRead] = None
    third_place: Optional[TeamRead] = None

    @model_validator(mode="before")
    @classmethod
    def populate_relation_users(cls, data):
        # Populate admin_lst and participant_lst with dicts {id, user_name}
        if hasattr(data, "admins"):
            data.__dict__.setdefault(
                "admin_lst",
                [
                    {"id": u.id, "user_name": getattr(u, "user_name", None)}
                    for u in data.admins if u.id is not None
                ]
            )
        if hasattr(data, "participants"):
            stake_paid_map: dict[int, bool] = {}
            if hasattr(data, "participant_links"):
                for link in data.participant_links:
                    if link.user_id is not None:
                        stake_paid_map[link.user_id] = link.stake_paid
            data.__dict__.setdefault(
                "participant_lst",
                [
                    {"id": u.id, "user_name": getattr(u, "user_name", None), "stake_paid": stake_paid_map.get(u.id, False)}
                    for u in data.participants if u.id is not None
                ]
            )
        if hasattr(data, "matches"):
            match_dates = [m.start_datetime.date() for m in data.matches if m.start_datetime is not None]
            data.__dict__.setdefault("start_date", min(match_dates) if match_dates else None)
            data.__dict__.setdefault("end_date", max(match_dates) if match_dates else None)
        return data


# ---------------------------------------------------------------------------
# Auto-delete tournament when its last admin is removed
# ---------------------------------------------------------------------------

@event.listens_for(SyncSession, "after_flush")
def _delete_tournament_if_no_admins(session: SyncSession, flush_context) -> None:
    """Delete a tournament automatically when its last admin link is removed."""
    deleted_links = [obj for obj in session.deleted if isinstance(obj, TournamentAdminLink)]
    if not deleted_links:
        return
    tournament_ids = {link.tournament_id for link in deleted_links if link.tournament_id is not None}
    for tournament_id in tournament_ids:
        remaining = session.execute(
            select(func.count()).select_from(TournamentAdminLink).where(
                TournamentAdminLink.tournament_id == tournament_id
            )
        ).scalar_one()
        if remaining == 0:
            tournament = session.get(Tournament, tournament_id)
            if tournament:
                session.delete(tournament)
