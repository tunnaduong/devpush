"""
Backward compatibility wrapper for refactored models.

This module maintains backward compatibility by re-exporting all models
from the new models package structure.
"""
# Import everything from the new models package
from models import *

# For any code that imports from this module, everything should work the same
__all__ = [
    "Base",
    "utc_now",
    "User",
    "UserIdentity",
    "Team",
    "TeamMember",
    "TeamInvite",
    "GithubInstallation",
    "Project",
    "Deployment",
    "Alias",
    "Domain",
    "Storage",
    "StorageProject",
    "Allowlist",
    "FORBIDDEN_TEAM_SLUGS",
]

# Re-export FORBIDDEN_TEAM_SLUGS for backward compatibility
from utils.slug import FORBIDDEN_TEAM_SLUGS
