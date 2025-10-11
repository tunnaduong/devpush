"""Team models."""
from __future__ import annotations
from sqlalchemy import (
    Boolean,
    Enum as SQLAEnum,
    String,
    ForeignKey,
    event,
    update,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timedelta
from secrets import token_hex
from typing import override, TYPE_CHECKING

from models.base import Base, utc_now
from utils.color import get_color
from utils.slug import generate_unique_team_slug

if TYPE_CHECKING:
    from models.user import User
    from models.project import Project


class Team(Base):
    """Team model."""

    __tablename__: str = "team"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: token_hex(16)
    )
    name: Mapped[str] = mapped_column(String(100), index=True)
    slug: Mapped[str] = mapped_column(String(40), nullable=True, unique=True)
    has_avatar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        SQLAEnum("active", "deleted", name="team_status"),
        nullable=False,
        default="active",
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", use_alter=True, ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        index=True, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        index=True, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(back_populates="team")
    created_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[created_by_user_id]
    )

    @property
    def color(self) -> str:
        """Get color for this team based on ID."""
        return get_color(self.id)

    @override
    def __repr__(self):
        return f"<Team {self.name}>"


@event.listens_for(Team, "after_insert")
def set_team_slug(mapper, connection, team):
    """Generate and set slug after team is inserted (and has an ID)."""
    if not team.slug:
        new_slug = generate_unique_team_slug(
            connection=connection,
            team_name=team.name,
            team_id=team.id,
            table_class=Team,
        )
        connection.execute(update(Team).where(Team.id == team.id).values(slug=new_slug))
        team.slug = new_slug


class TeamMember(Base):
    """Team membership model."""

    __tablename__ = "team_member"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("team.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    role: Mapped[str] = mapped_column(
        SQLAEnum("owner", "admin", "member", name="team_member_role"),
        nullable=False,
        default="member",
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    # Relationships
    team: Mapped[Team] = relationship()
    user: Mapped["User"] = relationship()

    @override
    def __repr__(self):
        return f"<TeamMember team_id={self.team_id} user_id={self.user_id} role={self.role}>"


class TeamInvite(Base):
    """Team invitation model."""

    __tablename__ = "team_invite"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: token_hex(16)
    )
    team_id: Mapped[str] = mapped_column(ForeignKey("team.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[str] = mapped_column(
        SQLAEnum("owner", "admin", "member", name="team_invite_role"),
        nullable=False,
        default="member",
    )
    status: Mapped[str] = mapped_column(
        SQLAEnum("pending", "accepted", "revoked", name="team_invite_status"),
        nullable=False,
        default="pending",
    )
    inviter_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(
        default=lambda: utc_now() + timedelta(days=30)
    )

    # Relationships
    team: Mapped[Team] = relationship()
    inviter: Mapped["User"] = relationship()

    @override
    def __repr__(self):
        return f"<TeamInvite {self.email} to team_id={self.team_id}>"
