"""Deployment models."""
from __future__ import annotations
from sqlalchemy import (
    BigInteger,
    Enum as SQLAEnum,
    JSON,
    String,
    Text,
    ForeignKey,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from secrets import token_hex
from typing import override, TYPE_CHECKING

from models.base import Base, utc_now
from utils.encryption import encrypt_json, decrypt_json
from utils.log import parse_log
from config import get_settings

if TYPE_CHECKING:
    from models.user import User
    from models.project import Project


class Deployment(Base):
    """Deployment model."""

    __tablename__: str = "deployment"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: token_hex(16)
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id"), index=True)
    repo_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    environment_id: Mapped[str] = mapped_column(String(8), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), index=True)
    commit_sha: Mapped[str] = mapped_column(String(40), index=True)
    commit_meta: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    config: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    _env_vars: Mapped[str] = mapped_column("env_vars", Text, nullable=False, default="")
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    container_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    container_status: Mapped[str | None] = mapped_column(
        SQLAEnum("running", "stopped", "removed", name="deployment_container_status"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        SQLAEnum("queued", "in_progress", "completed", name="deployment_status"),
        nullable=False,
        default="queued",
    )
    conclusion: Mapped[str] = mapped_column(
        SQLAEnum(
            "succeeded", "failed", "canceled", "skipped", name="deployment_conclusion"
        ),
        nullable=True,
    )
    trigger: Mapped[str] = mapped_column(
        SQLAEnum("webhook", "user", "api", name="deployment_trigger"),
        nullable=False,
        default="user",
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", use_alter=True, ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        index=True, nullable=False, default=utc_now
    )
    concluded_at: Mapped[datetime | None] = mapped_column(index=True, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="deployments")
    aliases: Mapped[list["Alias"]] = relationship(
        back_populates="deployment", foreign_keys="Alias.deployment_id"
    )
    created_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[created_by_user_id]
    )

    def __init__(self, *args, project: "Project", environment_id: str, **kwargs):
        """
        Initialize deployment with snapshot of project configuration.

        Args:
            project: The project this deployment belongs to
            environment_id: The environment ID to deploy to
            **kwargs: Additional deployment parameters
        """
        super().__init__(project=project, environment_id=environment_id, **kwargs)
        # Snapshot repo, config, environments and env_vars from project at time of creation
        self.repo_id = project.repo_id
        self.repo_full_name = project.repo_full_name
        self.config = project.config
        environment = project.get_environment_by_id(environment_id)
        self.env_vars = project.get_env_vars(environment["slug"]) if environment else []

    @property
    def environment(self) -> dict | None:
        """Get environment configuration."""
        return self.project.get_environment_by_id(self.environment_id)

    @property
    def env_vars(self) -> list[dict[str, str]]:
        """Decrypt and return environment variables."""
        if not self._env_vars:
            return []
        return decrypt_json(self._env_vars)

    @env_vars.setter
    def env_vars(self, value: list[dict[str, str]] | None):
        """Encrypt and store environment variables."""
        self._env_vars = encrypt_json(value)

    @property
    def slug(self) -> str:
        """Get deployment slug."""
        return f"{self.project.slug}-id-{self.id[:7]}"

    @property
    def hostname(self) -> str:
        """Get deployment hostname."""
        settings = get_settings()
        return f"{self.slug}.{settings.deploy_domain}"

    @property
    def url(self) -> str:
        """Get deployment URL."""
        settings = get_settings()
        return f"{settings.url_scheme}://{self.hostname}"

    def parse_logs(self):
        """Parse raw build logs into structured format."""
        if not hasattr(self, 'build_logs') or not self.build_logs:
            return []
        return [parse_log(log) for log in self.build_logs.splitlines()]

    @property
    def parsed_logs(self):
        """Get parsed logs."""
        return self.parse_logs()

    @override
    def __repr__(self):
        return f"<Deployment {self.id}>"


class Alias(Base):
    """Deployment alias model (for branches, environments, etc.)."""

    __tablename__: str = "alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    subdomain: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    deployment_id: Mapped[str] = mapped_column(ForeignKey("deployment.id"), index=True)
    previous_deployment_id: Mapped[str | None] = mapped_column(
        ForeignKey("deployment.id"), index=True, nullable=True
    )
    type: Mapped[str] = mapped_column(
        SQLAEnum("branch", "environment", "environment_id", name="alias_type"),
        nullable=False,
    )
    value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        index=True, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    deployment: Mapped[Deployment] = relationship(
        foreign_keys=[deployment_id], back_populates="aliases"
    )
    previous_deployment: Mapped[Deployment] = relationship(
        foreign_keys=[previous_deployment_id]
    )

    @property
    def hostname(self) -> str:
        """Get alias hostname."""
        settings = get_settings()
        return f"{self.subdomain}.{settings.deploy_domain}"

    @property
    def url(self) -> str:
        """Get alias URL."""
        settings = get_settings()
        return f"{settings.url_scheme}://{self.hostname}"

    @classmethod
    async def update_or_create(
        cls,
        db: AsyncSession,
        subdomain: str,
        deployment_id: str,
        type: str,
        value: str | None = None,
        environment_id: str | None = None,
    ) -> dict[str, object]:
        """
        Update or create alias.

        Args:
            db: Database session
            subdomain: The subdomain for the alias
            deployment_id: The deployment ID to point to
            type: Type of alias (branch, environment, environment_id)
            value: Optional value for the alias
            environment_id: Optional environment ID

        Returns:
            Dictionary with 'alias' key containing the Alias instance
        """
        result_query = await db.execute(select(cls).where(cls.subdomain == subdomain))
        alias = result_query.scalar_one_or_none()

        result = {"alias": None}

        if alias:
            if alias.deployment_id == deployment_id:
                result["alias"] = alias
                return result

            # Store previous deployment for production rollback capability
            if type == "environment" and environment_id == "prod":
                alias.previous_deployment_id = alias.deployment_id
            else:
                alias.previous_deployment_id = None
            alias.deployment_id = deployment_id
        else:
            alias = cls(
                subdomain=subdomain,
                deployment_id=deployment_id,
                type=type,
                value=value,
            )
            db.add(alias)

        result["alias"] = alias
        return result

    @override
    def __repr__(self):
        return f"<Alias {self.subdomain}>"
