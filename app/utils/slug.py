"""Slug generation utilities."""
import re
from sqlalchemy import select, func
from sqlalchemy.engine import Connection


FORBIDDEN_TEAM_SLUGS = [
    "auth",
    "api",
    "health",
    "assets",
    "upload",
    "user",
    "deployment-not-found",
    "new-team",
]


def slugify(text: str, max_length: int = 40) -> str:
    """
    Convert text to a URL-safe slug.

    Args:
        text: The text to slugify
        max_length: Maximum length of the slug

    Returns:
        A URL-safe slug
    """
    slug = text.lower()
    slug = slug.replace(" ", "-").replace("_", "-").replace(".", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug[:max_length].strip("-")
    return slug


def generate_unique_team_slug(
    connection: Connection,
    team_name: str,
    team_id: str,
    table_class,
) -> str:
    """
    Generate a unique slug for a team.

    Args:
        connection: Database connection
        team_name: Name of the team
        team_id: ID of the team
        table_class: The Team model class

    Returns:
        A unique slug
    """
    base_slug = slugify(team_name)

    if not base_slug or base_slug in FORBIDDEN_TEAM_SLUGS:
        base_slug = f"team-{team_id}"[:40]

    # Check if slug exists (case-insensitive)
    existing = connection.scalar(
        select(table_class.slug).where(func.lower(table_class.slug) == base_slug.lower())
    )

    if not existing:
        return base_slug

    # Add team ID suffix if slug exists
    return f"{base_slug[:32]}-{str(team_id)[:7]}"


def generate_unique_project_slug(
    connection: Connection,
    project_name: str,
    team_slug: str,
    project_id: str,
    table_class,
) -> str:
    """
    Generate a unique slug for a project.

    Args:
        connection: Database connection
        project_name: Name of the project
        team_slug: Slug of the team
        project_id: ID of the project
        table_class: The Project model class

    Returns:
        A unique slug
    """
    base_slug = slugify(f"{project_name}-{team_slug}")

    if not base_slug:
        base_slug = f"project-{project_id}"[:40]

    # Check if slug exists
    existing = connection.scalar(
        select(table_class.slug).where(table_class.slug == base_slug)
    )

    if not existing:
        return base_slug

    # Add project ID suffix if slug exists
    return f"{base_slug[:32]}-{str(project_id)[:7]}"
