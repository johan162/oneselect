# Database Management with Alembic & SQLAlchemy

## Overview

This project uses **SQLAlchemy** as the ORM (Object-Relational Mapper) and **Alembic** for database migrations. This setup solves several critical problems:

### Problems Solved

1. **Schema Version Control** - Track all database structure changes in Git alongside code changes
2. **Team Collaboration** - Multiple developers can safely evolve the schema without conflicts
3. **Deployment Safety** - Apply the exact same schema changes across dev, staging, and production environments
4. **Rollback Capability** - Revert problematic schema changes without data loss
5. **Code-First Development** - Define your schema in Python models, generate SQL migrations automatically
6. **Migration History** - Complete audit trail of how your database evolved over time

### Current Status

**Pre-Production Clean Slate**: Since this project hasn't been released yet, we maintain a single baseline migration that represents the current schema. This includes:
- User authentication with roles (is_active, is_superuser)
- Projects with sharing capabilities
- Features and pairwise comparisons
- Soft delete support for audit trails (user_id, deleted_at, deleted_by on comparisons)
- AHP algorithm configuration

The baseline migration (`6311ddae9299_initial_schema_with_soft_delete_support.py`) represents the complete current state. Future schema changes will be added as new migrations.

### Architecture

```
app/models/          → SQLAlchemy models (Python classes defining tables)
alembic/versions/    → Migration files (auto-generated SQL schema changes)
alembic/env.py       → Alembic configuration (connects to your models)
alembic.ini          → Database connection settings
app.db               → SQLite database file (development)
```

## Database Schema Location

The **authoritative schema** is defined in Python code:

- **`app/models/`** - SQLAlchemy model classes define tables, columns, relationships, and constraints
  - `app/models/user.py` - User accounts and authentication
  - `app/models/project.py` - Projects and sharing
  - `app/models/feature.py` - Features for comparison
  - `app/models/comparison.py` - Pairwise comparisons
  - `app/models/result.py` - Aggregated comparison results
  - `app/models/model_config.py` - AHP algorithm configuration

**Never edit the database directly!** Always modify the SQLAlchemy models and generate migrations.

## Initial Setup

### 1. Install Dependencies

```bash
poetry install
```

### 2. Create the Database

Apply all existing migrations to create the schema:

```bash
poetry run alembic upgrade head
```

This creates `app.db` (SQLite) and applies all migration files in `alembic/versions/` in order.

### 3. Create Initial Data

Generate the default superuser account:

```bash
poetry run python app/initial_data.py
```

Default credentials:
- **Username:** `admin`
- **Password:** `admin`
- **Email:** `admin@example.com`

### 4. Verify Setup

Check the current migration version:

```bash
poetry run alembic current
```

You should see the latest revision ID (e.g., `1936f930f13f (head)`).

## Making Schema Changes

### Workflow

1. **Modify SQLAlchemy models** in `app/models/`
2. **Generate migration** with Alembic
3. **Review generated SQL**
4. **Apply migration** to database
5. **Commit migration file** to Git

### Step-by-Step Example

#### 1. Modify Your Model

Edit a model file, e.g., `app/models/user.py`:

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    # NEW FIELD:
    phone_number = Column(String, nullable=True)  # Add this line
```

#### 2. Generate Migration

Alembic will detect the changes and create a migration file:

```bash
poetry run alembic revision --autogenerate -m "Add phone_number to users"
```

This creates a new file: `alembic/versions/<revision_id>_add_phone_number_to_users.py`

#### 3. Review Generated Migration

**Always review** the generated file before applying it:

```bash
ls -lt alembic/versions/  # Find newest file
cat alembic/versions/<newest_file>.py
```

Check that the `upgrade()` and `downgrade()` functions are correct:

```python
def upgrade() -> None:
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'phone_number')
```

#### 4. Apply Migration

```bash
poetry run alembic upgrade head
```

Alembic applies all pending migrations to reach the latest version.

#### 5. Commit to Git

```bash
git add alembic/versions/<new_migration_file>.py
git add app/models/user.py
git commit -m "Add phone_number field to User model"
```

## Common Alembic Commands

### Check Current Version

```bash
poetry run alembic current
```

Shows the current migration revision applied to your database.

### Show Migration History

```bash
poetry run alembic history --verbose
```

Lists all migrations with revision IDs, descriptions, and dates.

### Upgrade Database

```bash
# Upgrade to latest version
poetry run alembic upgrade head

# Upgrade by N steps
poetry run alembic upgrade +2

# Upgrade to specific revision
poetry run alembic upgrade 1936f930f13f
```

### Downgrade Database

```bash
# Downgrade by 1 migration
poetry run alembic downgrade -1

# Downgrade by N steps
poetry run alembic downgrade -2

# Downgrade to specific revision
poetry run alembic downgrade d201285aaa84

# Downgrade to initial state (empty database)
poetry run alembic downgrade base
```

### Show Pending Migrations

```bash
poetry run alembic heads
```

Shows the latest migration(s) in your codebase.

### Generate Empty Migration (Manual)

For complex changes that can't be auto-detected:

```bash
poetry run alembic revision -m "custom complex migration"
```

Then manually edit the generated file to add your SQL operations.

## Migration File Structure

Example migration file:

```python
"""Add is_active and is_superuser to User

Revision ID: 1936f930f13f
Revises: d201285aaa84
Create Date: 2025-11-30 22:56:21.271030
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '1936f930f13f'
down_revision = 'd201285aaa84'  # Points to previous migration

def upgrade() -> None:
    """Apply schema changes (forward migration)."""
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=True))

def downgrade() -> None:
    """Revert schema changes (rollback)."""
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'is_active')
```

### Key Components

- **`revision`** - Unique ID for this migration (random hash)
- **`down_revision`** - Parent migration (forms a linked list)
- **`upgrade()`** - SQL operations to apply changes
- **`downgrade()`** - SQL operations to revert changes

## Best Practices

### ✅ Do

- **Always review auto-generated migrations** before applying them
- **Test migrations on a copy of production data** before deploying
- **Write reversible migrations** with proper `downgrade()` functions
- **Commit migration files to Git** immediately after creation
- **Run migrations as part of deployment** (automated CI/CD)
- **Keep migrations small and focused** (one logical change per migration)
- **Add data migrations when needed** (use `op.execute()` for SQL)

### ❌ Don't

- **Never edit applied migrations** - Create a new migration instead
- **Never edit the database directly** - Always use Alembic
- **Don't delete migration files** - They're part of your version history
- **Don't skip migrations** - Apply them in order
- **Avoid non-reversible operations** in `upgrade()` if possible (e.g., dropping columns with data)

## Troubleshooting

### "Can't locate revision identified by 'xyz'"

Your database has a revision that doesn't exist in your codebase. Pull latest migrations:

```bash
git pull
poetry run alembic upgrade head
```

### "Target database is not up to date"

Apply pending migrations:

```bash
poetry run alembic upgrade head
```

### "FAILED: Can't proceed with --autogenerate"

Ensure your models are imported in `alembic/env.py`:

```python
from app.db.base import Base  # Imports all models
target_metadata = Base.metadata
```

### Reset Database Completely

**WARNING: Destroys all data!**

```bash
rm app.db  # Delete SQLite file
poetry run alembic upgrade head  # Recreate from migrations
poetry run python app/initial_data.py  # Recreate superuser
```

### Merge Conflicts in Migration Files

If two developers create migrations simultaneously:

```bash
# Merge both migration files into your branch
# Then create a merge migration:
poetry run alembic merge heads -m "merge migrations"
poetry run alembic upgrade head
```

## Production Deployment

### Automated Deployment

Include migrations in your deployment pipeline:

```bash
# In your CI/CD script or Dockerfile entrypoint:
poetry run alembic upgrade head  # Apply pending migrations
poetry run uvicorn app.main:app  # Start application
```

### Manual Deployment

```bash
# 1. Backup database
cp app.db app.db.backup

# 2. Pull latest code
git pull

# 3. Apply migrations
poetry run alembic upgrade head

# 4. Restart application
systemctl restart oneselect  # or your process manager
```

### Rollback in Production

If a migration causes issues:

```bash
# 1. Stop application
systemctl stop oneselect

# 2. Rollback migration
poetry run alembic downgrade -1

# 3. Restart application
systemctl start oneselect

# 4. Fix the issue, create new migration
```

## Additional Resources

- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **FastAPI + SQLAlchemy Tutorial**: https://fastapi.tiangolo.com/tutorial/sql-databases/

## Summary

- **SQLAlchemy models** (`app/models/`) define your schema in Python
- **Alembic migrations** (`alembic/versions/`) track schema changes over time
- **Always generate migrations** after changing models: `alembic revision --autogenerate`
- **Apply migrations** to database: `alembic upgrade head`
- **Commit migration files** to Git for team collaboration and deployment