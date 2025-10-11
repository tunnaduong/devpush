"""User models."""
from __future__ import annotations
from sqlalchemy import Boolean, Enum as SQLAEnum, String, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import override, TYPE_CHECKING

from models.base import Base, utc_now
from utils.encryption import encrypt_string, decrypt_string

if TYPE_CHECKING:
    from models.team import Team


class User(Base):
    """User account model."""

    __tablename__: str = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(320), index=True, unique=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), index=True, unique=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(256), index=True, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    has_avatar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        SQLAEnum("active", "deleted", name="team_status"),
        nullable=False,
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        index=True, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        index=True, nullable=False, default=utc_now, onupdate=utc_now
    )
    default_team_id: Mapped[str] = mapped_column(ForeignKey("team.id"), nullable=True)

    # Relationships
    default_team: Mapped["Team"] = relationship(foreign_keys=[default_team_id])
    identities: Mapped[list["UserIdentity"]] = relationship(back_populates="user")

    @override
    def __repr__(self):
        return f"<User {self.email}>"


class UserIdentity(Base):
    """User authentication identity (OAuth providers)."""

    __tablename__: str = "user_identity"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    provider: Mapped[str] = mapped_column(
        SQLAEnum("github", "google", name="identity_provider"),
        nullable=False,
        index=True,
    )
    provider_user_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    _access_token: Mapped[str | None] = mapped_column(
        "access_token", String(2048), nullable=True
    )
    _refresh_token: Mapped[str | None] = mapped_column(
        "refresh_token", String(2048), nullable=True
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # Relationships
    user: Mapped[User] = relationship(back_populates="identities")

    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_identity_provider_user"
        ),
    )

    @property
    def access_token(self) -> str | None:
        """Decrypt and return access token."""
        return decrypt_string(self._access_token)

    @access_token.setter
    def access_token(self, value: str | None):
        """Encrypt and store access token."""
        self._access_token = encrypt_string(value)

    @property
    def refresh_token(self) -> str | None:
        """Decrypt and return refresh token."""
        return decrypt_string(self._refresh_token)

    @refresh_token.setter
    def refresh_token(self, value: str | None):
        """Encrypt and store refresh token."""
        self._refresh_token = encrypt_string(value)

    @override
    def __repr__(self):
        return f"<UserIdentity {self.provider}:{self.provider_user_id}>"
