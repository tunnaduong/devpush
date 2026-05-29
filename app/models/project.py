"""Project models."""
from __future__ import annotations
from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum as SQLAEnum,
    JSON,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
    event,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from secrets import token_hex
from typing import override, TYPE_CHECKING

from models.base import Base, utc_now
from utils.color import get_color
from utils.encryption import encrypt_json, decrypt_json
from utils.slug import generate_unique_project_slug
from config import get_settings

if TYPE_CHECKING:
    from models.user import User
    from models.team import Team
    from models.github import GithubInstallation
    from models.deployment import Deployment, Alias
    from models.domain import Domain
    from models.storage import Storage, StorageProject


class Project(Base):
    """Project model."""

    __tablename__: str = "project"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: token_hex(16)
    )
    name: Mapped[str] = mapped_column(String(100), index=True)
    has_avatar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    repo_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    repo_status: Mapped[str] = mapped_column(
        SQLAEnum(
            "active", "deleted", "removed", "transferred", name="project_github_status"
        ),
        nullable=False,
        default="active",
    )
    github_installation_id: Mapped[int] = mapped_column(
        ForeignKey("github_installation.installation_id"), nullable=False, index=True
    )
    environments: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    _env_vars: Mapped[str] = mapped_column("env_vars", Text, nullable=False, default="")
    slug: Mapped[str] = mapped_column(String(40), nullable=True, unique=True)
    config: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
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
    status: Mapped[str] = mapped_column(
        SQLAEnum("active", "paused", "deleted", name="project_status"),
        nullable=False,
        default="active",
    )
    team_id: Mapped[str] = mapped_column(ForeignKey("team.id"), index=True)

    # Relationships
    github_installation: Mapped["GithubInstallation"] = relationship(
        back_populates="projects"
    )
    deployments: Mapped[list["Deployment"]] = relationship(back_populates="project")
    team: Mapped["Team"] = relationship(back_populates="projects")
    created_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[created_by_user_id]
    )
    domains: Mapped[list["Domain"]] = relationship(back_populates="project")
    storage_links: Mapped[list["StorageProject"]] = relationship(
        back_populates="project"
    )

    __table_args__ = (
        UniqueConstraint("team_id", "name", name="uq_project_team_name"),
        Index(
            "ix_project_team_name_lower",
            "team_id",
            func.lower(name),
            unique=True,
        ),
    )

    @property
    def storages(self) -> list["Storage"]:
        """Get database storages associated with this project."""
        return [
            link.storage
            for link in self.storage_links
            if link.storage and link.storage.type == "database"
        ]

    @property
    def env_vars(self) -> list[dict[str, str]]:
        """Decrypt and return environment variables."""
        if not self._env_vars:
            return []
        return decrypt_json(self._env_vars)

    @env_vars.setter
    def env_vars(self, value: list[dict[str, str]]):
        """Encrypt and store environment variables."""
        self._env_vars = encrypt_json(value)

    @property
    def hostname(self) -> str:
        """Get the primary hostname for this project."""
        settings = get_settings()
        return f"{self.slug}.{settings.deploy_domain}"

    @property
    def url(self) -> str:
        """Get the primary URL for this project."""
        settings = get_settings()
        return f"{settings.url_scheme}://{self.hostname}"

    @property
    def color(self) -> str:
        """Get color for this project based on ID."""
        return get_color(self.id)

    @property
    def active_environments(self) -> list[dict]:
        """Get only active environments."""
        return [env for env in self.environments if env.get("status") == "active"]

    @override
    def __repr__(self):
        return f"<Project {self.name}>"

    # Environment management methods (delegated to EnvironmentService)
    def has_active_environment_with_slug(
        self, slug: str, exclude_id: str | None = None
    ) -> bool:
        """Check if an active environment with given slug exists."""
        from services.environment import EnvironmentService
        return EnvironmentService.has_active_environment_with_slug(
            self, slug, exclude_id
        )

    def create_environment(self, name: str, slug: str, **kwargs) -> dict:
        """Create a new environment with a unique ID."""
        from services.environment import EnvironmentService
        return EnvironmentService.create_environment(self, name, slug, **kwargs)

    def update_environment(self, environment_id: str, values: dict) -> dict | None:
        """Update environment."""
        from services.environment import EnvironmentService
        return EnvironmentService.update_environment(self, environment_id, values)

    def delete_environment(self, environment_id: str | None) -> bool:
        """Soft delete environment."""
        from services.environment import EnvironmentService
        return EnvironmentService.delete_environment(self, environment_id)

    def get_environment_by_id(self, env_id: str) -> dict | None:
        """Get environment by ID."""
        from services.environment import EnvironmentService
        return EnvironmentService.get_environment_by_id(self, env_id)

    def get_environment_by_slug(
        self, slug: str, active_only: bool = True
    ) -> dict | None:
        """Get environment by slug."""
        from services.environment import EnvironmentService
        return EnvironmentService.get_environment_by_slug(self, slug, active_only)

    def get_env_vars(self, environment: str) -> list[dict[str, str]]:
        """Flattened env vars for a specific environment."""
        from services.environment import EnvironmentService
        return EnvironmentService.get_env_vars_for_environment(self, environment)

    # Domain methods
    async def get_domain_by_id(
        self, db: AsyncSession, domain_id: int
    ) -> "Domain | None":
        """Get domain by ID."""
        from models.domain import Domain
        result = await db.execute(
            select(Domain).where(
                Domain.id == domain_id,
                Domain.project_id == self.id,
            )
        )
        return result.scalar_one_or_none()

    async def get_domain_by_hostname(
        self, db: AsyncSession, hostname: str
    ) -> "Domain | None":
        """Get domain by hostname."""
        from models.domain import Domain
        result = await db.execute(
            select(Domain).where(
                Domain.hostname == hostname,
                Domain.project_id == self.id,
            )
        )
        return result.scalar_one_or_none()

    async def get_environment_aliases(
        self, db: AsyncSession
    ) -> dict[str, "Alias"]:
        """Get environment aliases for this project."""
        from models.deployment import Alias, Deployment
        result = await db.execute(
            select(Alias)
            .join(Deployment, Alias.deployment_id == Deployment.id)
            .where(Deployment.project_id == self.id, Alias.type == "environment")
        )
        aliases = result.scalars().all()
        return {alias.value: alias for alias in aliases}

    def get_environment_hostname(self, environment_slug: str) -> str:
        """Get environment hostname."""
        settings = get_settings()
        if environment_slug == "production":
            return self.hostname
        return f"{self.slug}-env-{environment_slug}.{settings.deploy_domain}"

    def get_environment_url(self, environment_slug: str) -> str:
        """Get environment URL."""
        settings = get_settings()
        return (
            f"{settings.url_scheme}://{self.get_environment_hostname(environment_slug)}"
        )

    def get_branch_hostname(self, branch: str) -> str:
        """Get branch hostname."""
        settings = get_settings()
        return f"{self.slug}-branch-{branch}.{settings.deploy_domain}"

    def get_branch_url(self, branch: str) -> str:
        """Get branch URL."""
        settings = get_settings()
        return f"{settings.url_scheme}://{self.get_branch_hostname(branch)}"


@event.listens_for(Project, "after_insert")
def set_project_slug(mapper, connection, project):
    """Generate and set slug after project is inserted (and has an ID)."""
    if not project.slug:
        from models.team import Team
        team_slug = connection.scalar(
            select(Team.slug).where(Team.id == project.team_id)
        )
        new_slug = generate_unique_project_slug(
            connection=connection,
            project_name=project.name,
            team_slug=team_slug,
            project_id=project.id,
            table_class=Project,
        )
        connection.execute(
            update(Project).where(Project.id == project.id).values(slug=new_slug)
        )
        project.slug = new_slug
