# Database Schema

OneSelect uses SQLite as its database backend. The schema is managed through Alembic migrations and consists of four main tables for managing users, projects, features, and comparisons.

## Overview

The database schema supports:
- User authentication (local and OAuth)
- Multi-project organization
- Bayesian scoring for features in two dimensions (complexity and value)
- Binary and graded comparison modes
- Soft deletion for comparisons (audit trail)

### Database Initialization Process

OneSelect uses a **manual initialization approach** that requires explicit setup before first use. The database is **not** automatically created when the application starts - this provides better control over schema management and prevents accidental database creation in production environments.

**How It Works:**

1. **Schema Creation (Alembic Migrations)**
   - The database schema is defined in SQLAlchemy models (`app/models/`)
   - Alembic migrations in `alembic/versions/` contain the SQL operations to create tables
   - Running `poetry run alembic upgrade head` executes all migrations and creates the database file
   - If the database file doesn't exist, Alembic creates it and applies all migrations from scratch
   - If the database exists, Alembic only applies new migrations that haven't been run yet

2. **Initial Data Population**
   - After schema creation, `app/initial_data.py` creates the default admin user
   - The script checks if an admin user already exists to avoid duplicates
   - This is a separate step because schema and seed data have different lifecycles

3. **First-Time Setup Workflow**

   **Local Development:**
   ```bash
   # 1. Install dependencies
   poetry install
   
   # 2. Create database schema (creates oneselect.db if it doesn't exist)
   poetry run alembic upgrade head
   
   # 3. Create admin user
   poetry run python app/initial_data.py
   
   # 4. Start the application
   poetry run uvicorn app.main:app --reload
   ```

   **Docker/Container Deployment:**
   ```bash
   # 1. Build container image
   make container-build
   
   # 2. Start services (database is created in /app/data/oneselect.db volume)
   make container-up
   
   # 3. Run migrations inside container
   podman exec oneselect-backend poetry run alembic upgrade head
   
   # 4. Create admin user inside container
   podman exec oneselect-backend poetry run python app/initial_data.py
   ```

   **Note**: Container deployments may use an entrypoint script to automate steps 3-4 on first launch.

4. **Application Behavior Without Database**
   - If you start the application (`uvicorn app.main:app`) without creating the database first, API requests will fail with database connection errors
   - The application does **not** automatically run migrations on startup
   - This design prevents accidental schema changes in production

5. **Detecting Database State**
   - **No database file**: Alembic will create a new SQLite file when running `upgrade head`
   - **Database exists, no schema**: Alembic creates the `alembic_version` table and applies all migrations
   - **Database exists with old schema**: Alembic reads `alembic_version`, determines which migrations are pending, and applies only those
   - **Database fully up-to-date**: Alembic reports "No migrations to apply"

6. **Zero-Downtime Updates**
   ```bash
   # Check current version
   poetry run alembic current
   
   # View pending migrations
   poetry run alembic history --indicate-current
   
   # Apply new migrations (application can stay running with SQLite)
   poetry run alembic upgrade head
   ```

**Why Manual Initialization?**

- **Safety**: Prevents accidental database creation or schema changes in production
- **Control**: Explicit migration step makes schema changes visible in deployment pipelines
- **Flexibility**: Allows dry-run testing with `alembic upgrade head --sql`
- **Audit Trail**: Clear record of when and how the database was initialized
- **Zero-Trust**: Application never assumes database structure - migrations must be run explicitly

**Default Credentials** (created by `app/initial_data.py`):
- **Username**: `admin`
- **Password**: `admin` (configurable via `FIRST_SUPERUSER_PASSWORD` environment variable)
- **Email**: `admin@example.com` (configurable via `FIRST_SUPERUSER` environment variable)

## Entity Relationship Diagram

```
┌─────────────┐
│    users    │
└──────┬──────┘
       │
       │ owner_id
       │
       ▼
┌─────────────┐         ┌──────────────┐
│  projects   │◄────────┤  features    │
└──────┬──────┘         └──────┬───────┘
       │                       │
       │                       │
       │ project_id            │ feature_a_id
       │                       │ feature_b_id
       ▼                       ▼
┌──────────────────────────────┐
│       comparisons            │
└──────────────────────────────┘
```

## Tables

### users

Stores user accounts with support for local authentication and Google OAuth.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | STRING (UUID) | NO | - | Primary key |
| `username` | STRING | NO | - | Unique username (used for login) |
| `email` | STRING | YES | - | User email (unique) |
| `hashed_password` | STRING | YES | - | Bcrypt hashed password (NULL for OAuth users) |
| `is_active` | BOOLEAN | YES | `1` | Account active status |
| `is_superuser` | BOOLEAN | YES | `0` | Admin privileges flag |
| `role` | STRING | YES | `'user'` | User role (`'user'` or `'root'`) |
| `display_name` | STRING | YES | - | Optional display name |
| `avatar_url` | STRING | YES | - | URL to user avatar image |
| `google_id` | STRING | YES | - | Google OAuth user ID (unique) |
| `auth_provider` | STRING | YES | `'local'` | Authentication provider (`'local'` or `'google'`) |

**Indexes:**
- Primary key on `id`
- Unique index on `username`
- Unique index on `email`
- Unique index on `google_id`

**Notes:**
- OAuth users have `auth_provider='google'`, `google_id` set, and `hashed_password` NULL
- Local users have `auth_provider='local'` and `hashed_password` set

### projects

Stores projects that contain features to be compared.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | STRING (UUID) | NO | - | Primary key |
| `name` | STRING | NO | - | Project name |
| `description` | STRING | YES | - | Project description |
| `created_at` | DATETIME(TZ) | YES | `CURRENT_TIMESTAMP` | Creation timestamp |
| `owner_id` | STRING (UUID) | NO | - | Foreign key to `users.id` |
| `total_comparisons` | INTEGER | NO | `0` | Total number of comparisons made |
| `complexity_avg_variance` | FLOAT | NO | `1.0` | Average variance across complexity scores |
| `value_avg_variance` | FLOAT | NO | `1.0` | Average variance across value scores |
| `comparison_mode` | STRING | NO | `'binary'` | Comparison mode (`'binary'` or `'graded'`) |

**Indexes:**
- Primary key on `id`
- Index on `name`

**Constraints:**
- Foreign key: `owner_id` → `users.id`
- Check constraint: `comparison_mode IN ('binary', 'graded')`

**Notes:**
- `comparison_mode='binary'`: Simple A vs B vs Tie comparisons
- `comparison_mode='graded'`: 5-point scale (a_much_better, a_better, equal, b_better, b_much_better)

### features

Stores features/requirements to be compared within a project.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | STRING (UUID) | NO | - | Primary key |
| `name` | STRING | NO | - | Feature name |
| `description` | STRING | YES | - | Feature description |
| `project_id` | STRING (UUID) | NO | - | Foreign key to `projects.id` |
| `tags` | JSON | YES | - | Array of tag strings |
| `complexity_mu` | FLOAT | NO | `0.0` | Bayesian mean score for complexity dimension |
| `complexity_sigma` | FLOAT | NO | `1.0` | Bayesian standard deviation for complexity |
| `value_mu` | FLOAT | NO | `0.0` | Bayesian mean score for value dimension |
| `value_sigma` | FLOAT | NO | `1.0` | Bayesian standard deviation for value |
| `created_at` | DATETIME(TZ) | YES | `CURRENT_TIMESTAMP` | Creation timestamp |
| `updated_at` | DATETIME(TZ) | YES | - | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Index on `name`

**Constraints:**
- Foreign key: `project_id` → `projects.id`

**Notes:**
- Bayesian scores: `mu` represents the estimated score, `sigma` represents uncertainty
- Lower `sigma` = higher confidence in the score
- Scores are updated after each comparison using Bradley-Terry model

### comparisons

Stores pairwise comparison results between features.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | STRING (UUID) | NO | - | Primary key |
| `project_id` | STRING (UUID) | NO | - | Foreign key to `projects.id` |
| `feature_a_id` | STRING (UUID) | NO | - | Foreign key to `features.id` (first feature) |
| `feature_b_id` | STRING (UUID) | NO | - | Foreign key to `features.id` (second feature) |
| `choice` | STRING | NO | - | Comparison result (`'feature_a'`, `'feature_b'`, or `'tie'`) |
| `dimension` | STRING | NO | - | Comparison dimension (`'complexity'` or `'value'`) |
| `strength` | STRING | YES | - | Graded comparison strength (NULL for binary) |
| `user_id` | STRING (UUID) | YES | - | Foreign key to `users.id` (who made comparison) |
| `created_at` | DATETIME(TZ) | YES | `CURRENT_TIMESTAMP` | Creation timestamp |
| `deleted_at` | DATETIME(TZ) | YES | - | Soft deletion timestamp (NULL if active) |
| `deleted_by` | STRING (UUID) | YES | - | Foreign key to `users.id` (who deleted) |

**Indexes:**
- Primary key on `id`
- Composite index on `(project_id, dimension, deleted_at)` for efficient querying

**Constraints:**
- Foreign key: `project_id` → `projects.id`
- Foreign key: `feature_a_id` → `features.id`
- Foreign key: `feature_b_id` → `features.id`
- Foreign key: `user_id` → `users.id`
- Foreign key: `deleted_by` → `users.id`
- Check constraint: `strength IS NULL OR strength IN ('a_much_better', 'a_better', 'equal', 'b_better', 'b_much_better')`

**Notes:**
- **Binary mode**: `strength` is NULL, only `choice` is used
- **Graded mode**: `strength` indicates comparison intensity, `choice` is derived from strength
- **Soft deletion**: Comparisons are not physically deleted; `deleted_at` is set for audit trail
- **Strength values**:
  - `a_much_better`: Feature A is significantly better (2.0x Bayesian update multiplier)
  - `a_better`: Feature A is better (1.0x multiplier)
  - `equal`: Features are roughly equal (configurable multiplier, default 0.8x)
  - `b_better`: Feature B is better (1.0x multiplier)
  - `b_much_better`: Feature B is significantly better (2.0x multiplier)

## Alembic Migrations

The schema is version-controlled using Alembic. The current migration is:

- **`001_init`**: Initial schema creation with all tables

### Running Migrations

```bash
# Upgrade to latest schema
poetry run alembic upgrade head

# View migration history
poetry run alembic history

# Rollback one version
poetry run alembic downgrade -1
```

## Common Queries

### Get all features with scores for a project

```sql
SELECT 
    f.id,
    f.name,
    f.description,
    ROUND(f.complexity_mu, 3) AS complexity_score,
    ROUND(f.complexity_sigma, 3) AS complexity_confidence,
    ROUND(f.value_mu, 3) AS value_score,
    ROUND(f.value_sigma, 3) AS value_confidence
FROM 
    features f
WHERE 
    f.project_id = 'YOUR-PROJECT-ID'
ORDER BY 
    f.complexity_mu DESC;
```

### Count active comparisons by dimension

```sql
SELECT 
    dimension,
    COUNT(*) as comparison_count
FROM 
    comparisons
WHERE 
    project_id = 'YOUR-PROJECT-ID'
    AND deleted_at IS NULL
GROUP BY 
    dimension;
```

### Find users with most comparisons

```sql
SELECT 
    u.username,
    COUNT(c.id) as comparison_count
FROM 
    users u
    INNER JOIN comparisons c ON u.id = c.user_id
WHERE 
    c.deleted_at IS NULL
GROUP BY 
    u.id, u.username
ORDER BY 
    comparison_count DESC;
```

### Get comparison history with feature names

```sql
SELECT 
    c.created_at,
    fa.name as feature_a,
    fb.name as feature_b,
    c.choice,
    c.dimension,
    c.strength,
    u.username
FROM 
    comparisons c
    INNER JOIN features fa ON c.feature_a_id = fa.id
    INNER JOIN features fb ON c.feature_b_id = fb.id
    LEFT JOIN users u ON c.user_id = u.id
WHERE 
    c.project_id = 'YOUR-PROJECT-ID'
    AND c.deleted_at IS NULL
ORDER BY 
    c.created_at DESC
LIMIT 50;
```

## Database File Location

The SQLite database file is located at:
- Development: `./oneselect.db` (project root)
- Docker: `/app/data/oneselect.db` (persisted in volume)

## Backup and Maintenance

### Manual Backup

```bash
# Create backup
sqlite3 oneselect.db ".backup oneselect_backup_$(date +%Y%m%d).db"

# Or use cp
cp oneselect.db oneselect_backup_$(date +%Y%m%d).db
```

### Database Size and Integrity

```bash
# Check database size
ls -lh oneselect.db

# Run integrity check
sqlite3 oneselect.db "PRAGMA integrity_check;"

# Optimize database (vacuum)
sqlite3 oneselect.db "VACUUM;"
```

## Performance Considerations

- **Indexes**: All foreign keys and frequently queried columns are indexed
- **Composite Index**: `(project_id, dimension, deleted_at)` on comparisons table optimizes progress queries
- **Soft Deletion**: `deleted_at IS NULL` filters are fast due to index
- **JSON Tags**: SQLite's JSON1 extension is used for feature tags (available by default in Python's sqlite3)

## Future Schema Changes

Alembic supports two approaches for creating migrations: **manual** and **automatic (autogenerate)**.

### Manual Migrations

Manual migrations require you to explicitly specify all schema changes in Python code. This is the default when you create a new migration:

```bash
# Generate an empty migration template
poetry run alembic revision -m "add_new_column"
```

This creates a new file in `alembic/versions/` with empty `upgrade()` and `downgrade()` functions. You must manually write the schema changes:

```python
def upgrade() -> None:
    # Add your schema changes here
    op.add_column('features', sa.Column('priority', sa.Integer(), nullable=True))
    op.create_index('ix_features_priority', 'features', ['priority'])

def downgrade() -> None:
    # Add reverse operations here
    op.drop_index('ix_features_priority', table_name='features')
    op.drop_column('features', 'priority')
```

**Pros:**
- Full control over migration operations
- Can include data migrations and complex transformations
- Explicit and clear what changes are being made

**Cons:**
- Tedious and error-prone for large schema changes
- Easy to forget constraints or indexes
- Must manually write both upgrade and downgrade operations

### Automatic Migrations (Autogenerate)

Alembic can automatically detect schema changes by comparing your SQLAlchemy models against the current database schema:

```bash
# Generate migration with automatic change detection
poetry run alembic revision --autogenerate -m "add_priority_field"
```

**How Autogenerate Works:**

1. **Model Inspection**: Reads your SQLAlchemy model definitions from `app/models/`
2. **Database Inspection**: Connects to the database and reads the current schema using SQLAlchemy's reflection capabilities
3. **Diff Generation**: Compares the two schemas and generates migration operations for detected differences
4. **Code Generation**: Creates a migration file with `upgrade()` and `downgrade()` functions

**What Autogenerate Can Detect:**

✅ **Detected automatically:**
- New tables
- Removed tables
- New columns
- Removed columns (if configured)
- Column type changes
- Column nullable changes
- New indexes
- Removed indexes

⚠️ **Requires manual intervention:**
- Column renames (appears as drop + add)
- Table renames (appears as drop + add)
- Changes to check constraints
- Changes to column defaults in some cases
- Data migrations or transformations
- Complex multi-step operations

**Important Limitations:**

Autogenerate is **not perfect** and you should **always review** the generated migration file:

```bash
# After running autogenerate, review the file
cat alembic/versions/XXXX_add_priority_field.py

# Edit if needed, then apply
poetry run alembic upgrade head
```

**Example Workflow:**

```python
# 1. Update your model in app/models/feature.py
class Feature(Base):
    # ... existing fields ...
    priority = Column(Integer, nullable=True, index=True)  # NEW FIELD

# 2. Generate migration automatically
poetry run alembic revision --autogenerate -m "add_feature_priority"

# 3. Review generated file (alembic/versions/XXXX_add_feature_priority.py)
# The file will contain something like:
def upgrade() -> None:
    op.add_column('features', sa.Column('priority', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_features_priority'), 'features', ['priority'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_features_priority'), table_name='features')
    op.drop_column('features', 'priority')

# 4. If it looks correct, apply it
poetry run alembic upgrade head
```

### Best Practices

1. **Always Review Autogenerated Migrations**: Even with autogenerate, check the generated code before applying
2. **Use Autogenerate for Simple Changes**: Column additions, type changes, new indexes
3. **Use Manual for Complex Changes**: Data migrations, multi-step transformations, renames
4. **Test Migrations**: Run `upgrade` and `downgrade` in a test environment before production
5. **One Logical Change Per Migration**: Don't combine unrelated schema changes
6. **Meaningful Messages**: Use descriptive migration messages: `alembic revision -m "add_user_avatar_support"`

### Common Migration Operations

```python
# Add a column
op.add_column('table_name', sa.Column('column_name', sa.String(), nullable=True))

# Remove a column
op.drop_column('table_name', 'column_name')

# Change column type
op.alter_column('table_name', 'column_name', type_=sa.Integer())

# Make column non-nullable (with default for existing rows)
op.execute("UPDATE table_name SET column_name = 'default' WHERE column_name IS NULL")
op.alter_column('table_name', 'column_name', nullable=False)

# Add an index
op.create_index('ix_table_column', 'table_name', ['column_name'])

# Add a foreign key
op.create_foreign_key('fk_table_other', 'table_name', 'other_table', ['other_id'], ['id'])

# Rename a column (SQLite requires table recreation)
# For SQLite, this is complex - see Alembic docs for batch operations

# Data migration example
op.execute("UPDATE features SET priority = 0 WHERE priority IS NULL")
```

### Configuration for Autogenerate

In `alembic/env.py`, you can configure what autogenerate detects:

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    compare_type=True,           # Detect column type changes
    compare_server_default=True, # Detect default value changes
    include_schemas=True,        # Include schema names
)
```

### Viewing Migration Status

```bash
# Show current version
poetry run alembic current

# Show migration history
poetry run alembic history --verbose

# Show pending migrations
poetry run alembic history --indicate-current

# Show SQL without executing
poetry run alembic upgrade head --sql
```
