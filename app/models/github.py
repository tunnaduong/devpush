"""GitHub integration models."""
from __future__ import annotations
from sqlalchemy import Enum as SQLAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import override, TYPE_CHECKING

from models.base import Base
from utils.encryption import encrypt_string, decrypt_string

if TYPE_CHECKING:
    from models.project import Project


class GithubInstallation(Base):
    """GitHub App installation model."""

    __tablename__: str = "github_installation"

    installation_id: Mapped[int] = mapped_column(primary_key=True)
    _token: Mapped[str | None] = mapped_column("token", String(2048), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        SQLAEnum("active", "deleted", "suspended", name="github_installation_status"),
        nullable=False,
        default="active",
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        back_populates="github_installation"
    )

    @property
    def token(self) -> str | None:
        """Decrypt and return GitHub installation token."""
        return decrypt_string(self._token)

    @token.setter
    def token(self, value: str | None):
        """Encrypt and store GitHub installation token."""
        self._token = encrypt_string(value)

    @override
    def __repr__(self):
        return f"<GithubInstallation {self.installation_id}>"
