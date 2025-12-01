# Baseline Database Schema

**Migration**: `6311ddae9299_initial_schema_with_soft_delete_support.py`  
**Date**: December 1, 2025

This baseline represents the complete initial schema for the OneSelect application before first production release.

## Tables

### users
- `id` (UUID, primary key)
- `email` (String, unique, indexed)
- `username` (String, unique, indexed)
- `hashed_password` (String)
- `is_active` (Boolean, default=True)
- `is_superuser` (Boolean, default=False)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### projects
- `id` (UUID, primary key)
- `name` (String)
- `description` (String, nullable)
- `owner_id` (UUID, foreign key → users.id)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### features
- `id` (UUID, primary key)
- `project_id` (UUID, foreign key → projects.id)
- `name` (String)
- `description` (String, nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### comparisons
- `id` (UUID, primary key)
- `project_id` (UUID, foreign key → projects.id)
- `feature_a_id` (UUID, foreign key → features.id)
- `feature_b_id` (UUID, foreign key → features.id)
- `choice` (String: "feature_a", "feature_b", "tie")
- `dimension` (String: "complexity", "value")
- `user_id` (UUID, foreign key → users.id, nullable) - Who created the comparison
- `created_at` (DateTime)
- `deleted_at` (DateTime, nullable) - Soft delete timestamp
- `deleted_by` (UUID, foreign key → users.id, nullable) - Who deleted the comparison

### results
- `id` (UUID, primary key)
- `project_id` (UUID, foreign key → projects.id)
- `feature_id` (UUID, foreign key → features.id)
- `priority_score` (Float)
- `complexity_score` (Float)
- `value_score` (Float)
- `calculation_metadata` (JSON)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### model_config
- `id` (UUID, primary key)
- `project_id` (UUID, foreign key → projects.id)
- `consistency_threshold` (Float)
- `max_comparisons` (Integer)
- `algorithm_version` (String)
- `created_at` (DateTime)
- `updated_at` (DateTime)

## Key Features

### Soft Delete Support
The `comparisons` table includes soft delete functionality for audit trail:
- `deleted_at`: Timestamp when comparison was deleted (NULL for active comparisons)
- `deleted_by`: User who performed the deletion
- `user_id`: User who created the comparison

All queries automatically filter `deleted_at IS NULL` except when explicitly requesting audit history.

### User Management
- Support for active/inactive users (`is_active`)
- Superuser privileges (`is_superuser`)
- Email and username must be unique
- Timestamps track account creation and updates

### Relationship Integrity
- Cascade deletes protect data integrity
- Foreign keys enforce referential integrity (when supported by database)
- Projects own features, comparisons, results, and configuration
- Users own projects and track their comparison activities

## Migration Strategy

Since this is a pre-production application:
- This baseline represents the complete current schema
- No historical migrations are maintained
- Future schema changes will be tracked as new migrations building on this baseline
- After production release, all migrations will be preserved for upgrade paths
