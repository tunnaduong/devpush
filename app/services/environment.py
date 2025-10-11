"""Environment management service for projects."""
from secrets import token_hex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import Project


class EnvironmentService:
    """Service for managing project environments."""

    @staticmethod
    def has_active_environment_with_slug(
        project: "Project",
        slug: str,
        exclude_id: str | None = None,
    ) -> bool:
        """
        Check if an active environment with given slug exists.

        Args:
            project: The project to check
            slug: The slug to check for
            exclude_id: Optional environment ID to exclude from check

        Returns:
            True if environment exists, False otherwise
        """
        return any(
            environment
            for environment in project.active_environments
            if environment.get("slug") == slug
            and (exclude_id is None or environment.get("id") != exclude_id)
        )

    @staticmethod
    def create_environment(
        project: "Project",
        name: str,
        slug: str,
        **kwargs,
    ) -> dict:
        """
        Create a new environment with a unique ID.

        Args:
            project: The project to add environment to
            name: Name of the environment
            slug: Slug for the environment
            **kwargs: Additional environment properties

        Returns:
            The created environment dictionary

        Raises:
            ValueError: If environment with slug already exists
        """
        if EnvironmentService.has_active_environment_with_slug(project, slug):
            raise ValueError(f"An active environment with slug '{slug}' already exists")

        env = {
            "id": token_hex(4),
            "name": name,
            "slug": slug,
            "status": "active",
            **kwargs,
        }
        environments = project.environments.copy()
        environments.append(env)
        project.environments = environments
        return env

    @staticmethod
    def update_environment(
        project: "Project",
        environment_id: str,
        values: dict,
    ) -> dict | None:
        """
        Update environment properties.

        Args:
            project: The project containing the environment
            environment_id: ID of the environment to update
            values: Dictionary of values to update

        Returns:
            Updated environment dictionary or None if not found

        Raises:
            ValueError: If attempting to modify production environment or slug conflict
        """
        env = EnvironmentService.get_environment_by_id(project, environment_id)
        if not env:
            return None

        # Prevent production rename
        if environment_id == "prod" and (
            env.get("name") != values.get("name")
            or env.get("slug") != values.get("slug")
        ):
            raise ValueError("Cannot modify production environment")

        # If changing slug, check it's unique
        new_slug = values.get("slug")
        if (
            new_slug
            and new_slug != env.get("slug")
            and EnvironmentService.has_active_environment_with_slug(
                project, new_slug, exclude_id=environment_id
            )
        ):
            raise ValueError(
                f"An active environment with slug '{new_slug}' already exists"
            )

        # Update the environment
        env_index = next(
            i for i, e in enumerate(project.environments) if e["id"] == environment_id
        )
        old_slug = project.environments[env_index]["slug"]

        environments = project.environments.copy()
        environments[env_index] = {**environments[env_index], **values}
        project.environments = environments

        # Update env vars if slug changed
        if new_slug and new_slug != old_slug:
            env_vars = project.env_vars.copy()
            for var in env_vars:
                if var.get("environment") == old_slug:
                    var["environment"] = new_slug
            project.env_vars = env_vars

        return environments[env_index]

    @staticmethod
    def delete_environment(
        project: "Project",
        environment_id: str | None,
    ) -> bool:
        """
        Soft delete an environment.

        Args:
            project: The project containing the environment
            environment_id: ID of the environment to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If attempting to delete production environment
        """
        if not environment_id:
            return False

        if environment_id == "prod":
            raise ValueError("Cannot delete production environment")

        env = EnvironmentService.get_environment_by_id(project, environment_id)
        if not env:
            return False

        # Remove env vars for this environment
        env_vars = project.env_vars.copy()
        env_vars = [var for var in env_vars if var.get("environment") != env["slug"]]
        project.env_vars = env_vars

        # Mark environment as deleted
        env_index = next(
            i for i, e in enumerate(project.environments) if e["id"] == environment_id
        )
        environments = project.environments.copy()
        environments[env_index] = {**environments[env_index], "status": "deleted"}
        project.environments = environments
        return True

    @staticmethod
    def get_environment_by_id(project: "Project", env_id: str) -> dict | None:
        """
        Get environment by ID.

        Args:
            project: The project containing the environment
            env_id: ID of the environment

        Returns:
            Environment dictionary or None if not found
        """
        return next((env for env in project.environments if env["id"] == env_id), None)

    @staticmethod
    def get_environment_by_slug(
        project: "Project",
        slug: str,
        active_only: bool = True,
    ) -> dict | None:
        """
        Get environment by slug.

        Args:
            project: The project containing the environment
            slug: Slug of the environment
            active_only: If True, only search active environments

        Returns:
            Environment dictionary or None if not found
        """
        environments = project.active_environments if active_only else project.environments
        return next((env for env in environments if env["slug"] == slug), None)

    @staticmethod
    def get_active_environments(project: "Project") -> list[dict]:
        """
        Get only active environments.

        Args:
            project: The project to get environments from

        Returns:
            List of active environment dictionaries
        """
        return [env for env in project.environments if env.get("status") == "active"]

    @staticmethod
    def get_env_vars_for_environment(
        project: "Project",
        environment: str,
    ) -> list[dict[str, str]]:
        """
        Get flattened env vars for a specific environment.

        Args:
            project: The project containing the env vars
            environment: The environment slug

        Returns:
            List of environment variables with environment-specific overrides applied
        """
        env_vars = [var for var in project.env_vars if not var.get("environment")]
        for var in project.env_vars:
            if var.get("environment") == environment:
                env_vars = [v for v in env_vars if v["key"] != var["key"]]
                env_vars.append(var)
        return env_vars
