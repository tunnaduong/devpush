# Refactoring Documentation

This document describes the major refactoring performed on the /dev/push codebase to improve code organization, maintainability, and separation of concerns.

## Overview

The refactoring focused on four main areas:

1. **Encryption utilities** - Extracted to a dedicated service
2. **Slug generation** - Consolidated into reusable utilities
3. **Models organization** - Split large models.py file into domain-specific modules
4. **Environment management** - Extracted to a dedicated service

## Changes

### 1. Encryption Utilities (`app/utils/encryption.py`)

**Before:** Encryption logic was duplicated across multiple model classes with `@property` decorators.

**After:** Centralized encryption/decryption functions:

```python
from utils.encryption import encrypt_string, decrypt_string, encrypt_json, decrypt_json

# String encryption
encrypted = encrypt_string("sensitive_data")
decrypted = decrypt_string(encrypted)

# JSON encryption
encrypted = encrypt_json({"key": "value"})
decrypted = decrypt_json(encrypted)
```

**Benefits:**
- Single source of truth for encryption logic
- Easier to update encryption algorithm
- Reduced code duplication
- Better testability

### 2. Slug Generation (`app/utils/slug.py`)

**Before:** Slug generation logic was embedded in SQLAlchemy event listeners with duplicated patterns.

**After:** Reusable utility functions:

```python
from utils.slug import slugify, generate_unique_team_slug, generate_unique_project_slug

# Basic slugification
slug = slugify("My Team Name!")  # Returns: "my-team-name"

# With database uniqueness check
slug = generate_unique_team_slug(connection, team_name, team_id, Team)
```

**Benefits:**
- Reusable across different models
- Easier to test independently
- Consistent slug generation logic
- Clearer separation of concerns

### 3. Models Organization

**Before:** Single `models.py` file with 828 lines containing all models.

**After:** Organized into domain-specific modules:

```
app/
├── models/
│   ├── __init__.py          # Exports all models
│   ├── base.py              # Base utilities (utc_now, Base)
│   ├── user.py              # User and UserIdentity models
│   ├── team.py              # Team, TeamMember, TeamInvite models
│   ├── project.py           # Project model
│   ├── deployment.py        # Deployment and Alias models
│   ├── domain.py            # Domain model
│   └── github.py            # GithubInstallation model
└── models.py                # Backward compatibility wrapper
```

**Backward Compatibility:** The original `models.py` now acts as a compatibility layer:

```python
# Both import styles work identically
from models import User, Team, Project  # Old style (still works)
from models.user import User            # New style (also works)
```

**Benefits:**
- Better code organization by domain
- Easier to find and modify specific models
- Reduced file size makes navigation easier
- Maintains backward compatibility
- Clear ownership of model logic

### 4. Environment Service (`app/services/environment.py`)

**Before:** Complex environment management logic embedded directly in the Project model class.

**After:** Dedicated service class with static methods:

```python
from services.environment import EnvironmentService

# Create environment
env = EnvironmentService.create_environment(project, "Staging", "staging")

# Update environment
EnvironmentService.update_environment(project, env_id, {"name": "New Name"})

# Delete environment
EnvironmentService.delete_environment(project, env_id)

# Query environments
env = EnvironmentService.get_environment_by_slug(project, "production")
```

**Benefits:**
- Separation of concerns (model vs. business logic)
- Easier to test environment operations
- Clearer API for environment management
- Reduced model class complexity
- Better documentation and type hints

## Migration Guide

### For Existing Code

No changes required! The refactoring maintains full backward compatibility. All existing imports will continue to work:

```python
# These still work exactly as before
from models import User, Team, Project, Deployment
from models import utc_now, FORBIDDEN_TEAM_SLUGS
```

### For New Code

We recommend using the new structure for better organization:

```python
# Preferred for new code
from models.user import User, UserIdentity
from models.team import Team, TeamMember
from models.project import Project
from utils.encryption import encrypt_string, decrypt_string
from services.environment import EnvironmentService
```

## Testing

Run the validation test to ensure everything works:

```bash
cd app
python test_refactoring.py
```

This test validates:
- All imports work correctly
- Backward compatibility is maintained
- Services function properly
- Utilities work as expected

## File Changes Summary

### New Files Created

- `app/utils/encryption.py` - Encryption utilities
- `app/utils/slug.py` - Slug generation utilities
- `app/services/environment.py` - Environment management service
- `app/models/__init__.py` - Models package entry point
- `app/models/base.py` - Base utilities
- `app/models/user.py` - User models
- `app/models/team.py` - Team models
- `app/models/project.py` - Project model
- `app/models/deployment.py` - Deployment models
- `app/models/domain.py` - Domain model
- `app/models/github.py` - GitHub integration model
- `app/test_refactoring.py` - Validation test script

### Modified Files

- `app/models.py` - Now a backward compatibility wrapper
- Original `models.py` backed up to `models_backup.py`

### No Changes Required

All other files continue to work without modification due to backward compatibility layer.

## Benefits Summary

1. **Better Organization**: Code is organized by domain and responsibility
2. **Improved Maintainability**: Smaller, focused files are easier to maintain
3. **Enhanced Testability**: Extracted services and utilities are easier to test
4. **Reduced Duplication**: Common logic centralized in utilities
5. **Clearer Architecture**: Separation between models, services, and utilities
6. **Better Documentation**: Each module has clear purpose and documentation
7. **Type Safety**: Improved type hints throughout
8. **Backward Compatible**: No breaking changes for existing code

## Future Improvements

Consider these follow-up refactorings:

1. **Service Layer Expansion**: Extract more business logic from routers to services
2. **Repository Pattern**: Add repository layer for database operations
3. **Validation Layer**: Centralize validation logic
4. **Error Handling**: Standardize error handling patterns
5. **Caching**: Add caching layer for frequently accessed data
6. **Query Optimization**: Review and optimize common database queries
7. **Event System**: Implement a more robust event/message system

## Questions?

If you have questions about the refactoring or need help migrating specific code:

1. Check this documentation first
2. Run the validation test: `python test_refactoring.py`
3. Review the new module structure in `app/models/`
4. Check individual model files for documentation

## Rollback

If you need to rollback the refactoring:

1. Restore original `models.py`: `mv models_backup.py models.py`
2. Remove the `models/` directory
3. Remove new utility files: `utils/encryption.py`, `utils/slug.py`
4. Remove new service: `services/environment.py`

However, we recommend against rollback as the new structure provides significant benefits with zero breaking changes.
