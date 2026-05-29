"""
Test script to validate the refactoring.
This script checks that all imports work correctly and services are functional.
"""
import sys
import traceback

def test_imports():
    """Test that all model imports work correctly."""
    print("Testing model imports...")

    try:
        # Test backward compatibility layer
        from models import (
            Base, utc_now,
            User, UserIdentity,
            Team, TeamMember, TeamInvite,
            GithubInstallation,
            Project,
            Deployment, Alias,
            Domain,
            FORBIDDEN_TEAM_SLUGS
        )
        print("✓ All model imports successful")

        # Test new package structure
        from models.base import Base as Base2, utc_now as utc_now2
        from models.user import User as User2, UserIdentity as UserIdentity2
        from models.team import Team as Team2, TeamMember as TeamMember2
        from models.project import Project as Project2
        from models.deployment import Deployment as Deployment2, Alias as Alias2
        from models.domain import Domain as Domain2
        from models.github import GithubInstallation as GithubInstallation2
        print("✓ Direct package imports successful")

        # Verify they're the same classes
        assert User is User2
        assert Team is Team2
        assert Project is Project2
        assert Deployment is Deployment2
        print("✓ Backward compatibility verified")

        return True
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        traceback.print_exc()
        return False

def test_utilities():
    """Test utility functions."""
    print("\nTesting utility functions...")

    try:
        # Test encryption utilities
        from utils.encryption import encrypt_string, decrypt_string, encrypt_json, decrypt_json

        test_string = "test_value"
        encrypted = encrypt_string(test_string)
        decrypted = decrypt_string(encrypted)
        assert decrypted == test_string
        print("✓ Encryption utilities work")

        test_data = {"key": "value", "list": [1, 2, 3]}
        encrypted_json = encrypt_json(test_data)
        decrypted_json = decrypt_json(encrypted_json)
        assert decrypted_json == test_data
        print("✓ JSON encryption works")

        # Test slug utilities
        from utils.slug import slugify, FORBIDDEN_TEAM_SLUGS

        slug = slugify("My Team Name!")
        assert slug == "my-team-name"
        print("✓ Slug generation works")

        # Test environment service
        from services.environment import EnvironmentService
        print("✓ Environment service import works")

        return True
    except Exception as e:
        print(f"✗ Utility test failed: {e}")
        traceback.print_exc()
        return False

def test_service_imports():
    """Test that services can still import models."""
    print("\nTesting service imports...")

    try:
        from services.deployment import DeploymentService
        from services.github_installation import GitHubInstallationService
        from services.loki import LokiService
        from services.domain import DomainService
        print("✓ All service imports successful")
        return True
    except Exception as e:
        print(f"✗ Service import test failed: {e}")
        traceback.print_exc()
        return False

def test_router_imports():
    """Test that routers can still import models."""
    print("\nTesting router imports...")

    try:
        from routers import auth, project, github, google, team, user, event
        print("✓ All router imports successful")
        return True
    except Exception as e:
        print(f"✗ Router import test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("REFACTORING VALIDATION TEST")
    print("=" * 60)

    results = []
    results.append(("Model Imports", test_imports()))
    results.append(("Utilities", test_utilities()))
    results.append(("Services", test_service_imports()))
    results.append(("Routers", test_router_imports()))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name}: {status}")

    all_passed = all(result[1] for result in results)

    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
