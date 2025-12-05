# Appendix: API Endpoint List

**Quick Reference Summary of All OneSelect API Endpoints**

This document provides a comprehensive list of all REST API endpoints in the OneSelect system. For detailed documentation with examples, see the [API Reference](api.md).

## Base URL
`https://api.oneselect.example.com/v1`

## Common Data Types
*   **UUID**: String format uuid (e.g., `550e8400-e29b-41d4-a716-446655440000`).
*   **Dimension**: Enum `["complexity", "value"]`.
*   **ComparisonChoice**: Enum `["feature_a", "feature_b", "tie"]`.

## 1. Authentication & Authorization

OneSelect supports two authentication methods: **Username/Password** (traditional) and **Google OAuth** (optional).

### 1.1 Username/Password Authentication

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AUTH-01** | Login | Authenticate a user and return a session token (JWT). | `POST` | `/auth/login` | **Body**: `{ "username": "string", "password": "string" }` | **200 OK**: `{ "access_token": "string", "token_type": "bearer" }`<br>**401 Unauthorized** |
| **AUTH-02** | Register | Register a new user (self-service sign-up). | `POST` | `/auth/register` | **Body**: `{ "username": "string", "password": "string", "email": "string" }` | **201 Created**: `{ "id": "uuid", "username": "string", "email": "string", "auth_provider": "local" }`<br>**400 Bad Request** |
| **AUTH-03** | Refresh Token | Refresh an expired JWT token using a refresh token. | `POST` | `/auth/refresh` | **Body**: `{ "refresh_token": "string" }` | **200 OK**: `{ "token": "string", "refresh_token": "string" }`<br>**401 Unauthorized** |
| **AUTH-04** | Logout | Invalidate the current session/token. | `POST` | `/auth/logout` | None | **204 No Content** |
| **AUTH-05** | Get Current User | Get the profile of the currently authenticated user. | `GET` | `/auth/me` | None | **200 OK**: `{ "id": "uuid", "username": "string", "email": "string", "role": "string", "auth_provider": "local" \| "google" }` |
| **AUTH-06** | Change Password | Update the current user's password (local accounts only). | `POST` | `/auth/change-password` | **Body**: `{ "current_password": "string", "new_password": "string" }` | **204 No Content**<br>**400 Bad Request** (weak password or OAuth user)<br>**401 Unauthorized** (wrong current password) |
| **AUTH-07** | Update Profile | Update mutable profile attributes for the current user. | `PATCH` | `/auth/me` | **Body**: `{ "email": "string", "display_name": "string", "avatar_url": "string" }` | **200 OK**: `{ "id": "uuid", "username": "string", "email": "string", "display_name": "string", "avatar_url": "string" }` |
| **AUTH-08** | Test Token | Validate and test the current JWT token. | `POST` | `/auth/login/test-token` | None | **200 OK**: `{ "id": "uuid", "username": "string", "email": "string", "role": "string" }` |

### 1.2 Google OAuth Authentication

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AUTH-GOOGLE-01** | Google Login | Initiate Google OAuth flow. Redirects to Google's consent screen. | `GET` | `/auth/google/login` | None | **302 Redirect**: To Google OAuth consent screen |
| **AUTH-GOOGLE-02** | Google Callback | Handle Google OAuth callback. Creates/links user account and redirects to frontend with JWT token. | `GET` | `/auth/google/callback` | **Query**: `code` (OAuth code from Google), `state` (CSRF protection) | **302 Redirect**: `{FRONTEND_URL}/auth/callback?token=<jwt_token>` or `{FRONTEND_URL}/auth/error?message=<error>` |
| **AUTH-GOOGLE-03** | OAuth Status | Check if Google OAuth is configured and enabled. | `GET` | `/auth/google/status` | None | **200 OK**: `{ "google_oauth_enabled": bool, "google_client_id_set": bool, "google_client_secret_set": bool }` |

## 2. User Management (Root/Admin Only)
*Note: Regular users can only see their own profile (implementation detail).*

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **USER-01** | List Users | Get a list of all users. Root access required. | `GET` | `/users` | None | **200 OK**: `[ { "id": "uuid", "username": "string", "role": "string" } ]`<br>**403 Forbidden** |
| **USER-02** | Assign Project | Assign a project to a specific user. Root access required. | `POST` | `/users/{userId}/assignments` | **Path**: `userId`<br>**Body**: `{ "projectId": "uuid" }` | **200 OK**: `{ "message": "Project assigned" }`<br>**404 Not Found** |
| **USER-03** | Delete User | Delete a user. Optionally transfer their projects to another user. Root access required. | `DELETE` | `/users/{userId}` | **Path**: `userId`<br>**Query**: `transfer_to` (optional uuid) | **204 No Content**<br>**404 Not Found** |
| **USER-04** | Update User Role | Grant or revoke root access for a user. Root access required. | `PATCH` | `/users/{userId}/role` | **Path**: `userId`<br>**Body**: `{ "role": "root" \| "user" }` | **200 OK**: `{ "id": "uuid", "username": "string", "role": "string" }`<br>**403 Forbidden** |
| **USER-05** | Get User | Get details of a specific user. Root access required. | `GET` | `/users/{userId}` | **Path**: `userId` | **200 OK**: `{ "id": "uuid", "username": "string", "email": "string", "role": "string", "is_active": bool }`<br>**404 Not Found** |
| **USER-06** | Update User | Update user details. Root access required. | `PUT` | `/users/{userId}` | **Path**: `userId`<br>**Body**: `{ "email": "string", "is_active": bool }` | **200 OK**: `{ "id": "uuid", "username": "string", "email": "string", "is_active": bool }`<br>**404 Not Found** |
| **USER-07** | Update Own Profile | Update the current user's own profile. | `PUT` | `/users/me` | **Body**: `{ "email": "string", "display_name": "string" }` | **200 OK**: `{ "id": "uuid", "username": "string", "email": "string", "display_name": "string" }` |

## 3. Project Management
*Note: Users can only access projects they created or are assigned to.*

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PROJ-01** | List Projects | Get all projects visible to the current user. Supports `include_stats` for dashboard efficiency. | `GET` | `/projects` | **Query**: `include_stats` (bool, optional, default false) - includes feature count, comparison counts, progress % per project | **200 OK**: `[ { "id": "uuid", "name": "string", "description": "string", "created_at": "datetime", "stats": { ... } (if include_stats=true) } ]` |
| **PROJ-02** | Create Project | Create a new project. | `POST` | `/projects` | **Body**: `{ "name": "string", "description": "string" }` | **201 Created**: `{ "id": "uuid", "name": "string", "description": "string", "created_at": "datetime" }` |
| **PROJ-03** | Get Project | Get details of a specific project. | `GET` | `/projects/{projectId}` | **Path**: `projectId` | **200 OK**: `{ "id": "uuid", "name": "string", "description": "string", "created_at": "datetime" }`<br>**404 Not Found** |
| **PROJ-04** | Update Project | Update project metadata. | `PUT` | `/projects/{projectId}` | **Path**: `projectId`<br>**Body**: `{ "name": "string", "description": "string" }` | **200 OK**: `{ "id": "uuid", "name": "string", ... }` |
| **PROJ-05** | Delete Project | Delete a project and all associated data. | `DELETE` | `/projects/{projectId}` | **Path**: `projectId` | **204 No Content** |
| **PROJ-06** | List User Projects | Get all projects for a specific user. Root access required. | `GET` | `/users/{userId}/projects` | **Path**: `userId` | **200 OK**: `[ { "id": "uuid", "name": "string", "description": "string", "created_at": "datetime" } ]`<br>**403 Forbidden** |
| **PROJ-07** | Get Project Summary | Get a comprehensive project summary including stats, progress, and alerts in a single call. | `GET` | `/projects/{projectId}/summary` | **Path**: `projectId` | **200 OK**: `{ "project": { "id": "uuid", "name": "string", "description": "string" }, "feature_count": int, "comparisons": { "complexity": { "done": int, "remaining_for_95": int }, "value": { "done": int, "remaining_for_95": int } }, "average_variance": { "complexity": float, "value": float }, "inconsistency_count": { "complexity": int, "value": int } }` |
| **PROJ-08** | List Collaborators | Get all users who have access to a project. | `GET` | `/projects/{projectId}/collaborators` | **Path**: `projectId` | **200 OK**: `[ { "user_id": "uuid", "username": "string", "role": "owner" \| "collaborator", "assigned_at": "datetime" } ]` |
| **PROJ-09** | Get Activity Log | Get paginated activity/audit log for a project. | `GET` | `/projects/{projectId}/activity` | **Path**: `projectId`<br>**Query**: `page` (int), `per_page` (int), `action_type` (optional) | **200 OK**: `{ "items": [ { "id": "uuid", "user": { "id": "uuid", "username": "string" }, "action": "string", "entity_type": "string", "entity_id": "uuid", "timestamp": "datetime", "details": {} } ], "total": int }` |
| **PROJ-10** | Get Last Modified | Get the last modification timestamp for cache invalidation. | `GET` | `/projects/{projectId}/last-modified` | **Path**: `projectId` | **200 OK**: `{ "last_modified": "datetime", "modified_by": "uuid" }` |
| **PROJ-11** | Get Comparison History | Get complete audit trail of all comparisons made in a project, including active and deleted comparisons. | `GET` | `/projects/{projectId}/history` | **Path**: `projectId` | **200 OK**: `{ "project": { "id": "uuid", "name": "string", "description": "string" }, "comparisons": [ { "id": "uuid", "feature_a": { "id": "uuid", "name": "string" }, "feature_b": { "id": "uuid", "name": "string" }, "choice": "feature_a" \| "feature_b" \| "tie", "dimension": "complexity" \| "value", "user": { "id": "uuid", "username": "string" }, "created_at": "datetime" } ], "deleted_comparisons": [ { "id": "uuid", "feature_a": { "id": "uuid", "name": "string" }, "feature_b": { "id": "uuid", "name": "string" }, "choice": "string", "dimension": "string", "user": { "id": "uuid", "username": "string" }, "created_at": "datetime", "deleted_at": "datetime", "deleted_by": { "id": "uuid", "username": "string" } } ] }` |

## 4. Feature (Requirement) Management

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FEAT-01** | List Features | Get all features/requirements for a project. Supports `include_scores` for combined feature+score views. | `GET` | `/projects/{projectId}/features` | **Path**: `projectId`<br>**Query**: `page` (int, default 1), `per_page` (int, default 50), `search` (optional), `include_scores` (bool, optional, default false) - includes Bayesian mu/sigma scores | **200 OK**: `[ { "id": "uuid", "name": "string", "description": "string", "scores": { "complexity": { "mu": float, "sigma": float }, "value": { ... } } (if include_scores=true) } ]` |
| **FEAT-02** | Add Feature | Add a new feature to the project. Triggers recalculation of variance. | `POST` | `/projects/{projectId}/features` | **Path**: `projectId`<br>**Body**: `{ "name": "string", "description": "string" }` | **201 Created**: `{ "id": "uuid", "name": "string", "description": "string" }` |
| **FEAT-03** | Bulk Add Features | Add multiple features at once. | `POST` | `/projects/{projectId}/features/bulk` | **Path**: `projectId`<br>**Body**: `{ "features": [ { "name": "string", "description": "string" } ] }` | **201 Created**: `{ "count": int, "ids": ["uuid"] }` |
| **FEAT-04** | Update Feature | Update a feature's details. | `PUT` | `/projects/{projectId}/features/{featureId}` | **Path**: `projectId`, `featureId`<br>**Body**: `{ "name": "string", "description": "string" }` | **200 OK**: `{ "id": "uuid", ... }` |
| **FEAT-05** | Delete Feature | Remove a feature from the project. | `DELETE` | `/projects/{projectId}/features/{featureId}` | **Path**: `projectId`, `featureId` | **204 No Content** |
| **FEAT-06** | Bulk Delete Features | Delete multiple features at once. | `POST` | `/projects/{projectId}/features/bulk-delete` | **Path**: `projectId`<br>**Body**: `{ "feature_ids": ["uuid"] }` | **200 OK**: `{ "deleted_count": int }` |
| **FEAT-07** | Get Feature | Get a single feature's details. | `GET` | `/projects/{projectId}/features/{featureId}` | **Path**: `projectId`, `featureId` | **200 OK**: `{ "id": "uuid", "name": "string", "description": "string", "tags": ["string"], "created_at": "datetime", "updated_at": "datetime" }` |

## 5. Comparison Handling

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **COMP-01** | Get Next Pair | Get the next pair of features to compare based on highest information gain using transitive closure optimization. Returns 204 when target certainty is reached or no useful comparisons remain. | `GET` | `/projects/{projectId}/comparisons/next` | **Path**: `projectId`<br>**Query**: `dimension` (enum: complexity, value), `target_certainty` (float, optional, default 0.0), `include_progress` (bool, optional) - When true, includes progress metrics in response | **200 OK**: `{ "comparison_id": null, "feature_a": { "id": "uuid", "name": "string", "description": "string" }, "feature_b": { "id": "uuid", "name": "string", "description": "string" }, "dimension": "string", "progress": { ... } (if include_progress=true) }`<br>**204 No Content** (if target certainty reached or no useful comparisons left) |
| **COMP-02** | Submit Result | Submit the result of a pairwise comparison. Returns the comparison along with updated inconsistency statistics for immediate UI feedback. | `POST` | `/projects/{projectId}/comparisons` | **Path**: `projectId`<br>**Body**: `{ "feature_a_id": "uuid", "feature_b_id": "uuid", "choice": "feature_a" \| "feature_b" \| "tie", "dimension": "complexity" \| "value" }` | **201 Created**: `{ "id": "uuid", "project_id": "uuid", "feature_a": { "id": "uuid", "name": "string" }, "feature_b": { "id": "uuid", "name": "string" }, "choice": "string", "dimension": "string", "created_at": "datetime", "inconsistency_stats": { "cycle_count": int, "total_comparisons": int, "inconsistency_percentage": float, "dimension": "string" } }` |
| **COMP-03** | Get Estimates | Get estimated number of comparisons needed to reach certainty thresholds. | `GET` | `/projects/{projectId}/comparisons/estimates` | **Path**: `projectId`<br>**Query**: `dimension` | **200 OK**: `{ "dimension": "string", "estimates": { "70%": int, "80%": int, "90%": int, "95%": int } }` |
| **COMP-04** | Get Inconsistency Stats | Get inconsistency statistics summary without full cycle details. Useful for dashboard widgets and health checks. | `GET` | `/projects/{projectId}/comparisons/inconsistency-stats` | **Path**: `projectId`<br>**Query**: `dimension` (optional) | **200 OK**: `{ "cycle_count": int, "total_comparisons": int, "inconsistency_percentage": float, "dimension": "string" }` |
| **COMP-04b** | Get Inconsistencies | Get detailed graph cycles representing logical inconsistencies. Returns list of cycles with feature IDs and names. | `GET` | `/projects/{projectId}/comparisons/inconsistencies` | **Path**: `projectId`<br>**Query**: `dimension` (optional) | **200 OK**: `{ "cycles": [ { "feature_ids": ["uuid"], "feature_names": ["string"], "length": int, "dimension": "string" } ], "count": int, "message": "string" }` |
| **COMP-05** | Delete Comparison | Delete a specific comparison result (e.g., to resolve an inconsistency). | `DELETE` | `/projects/{projectId}/comparisons/{comparisonId}` | **Path**: `projectId`, `comparisonId` | **204 No Content** |
| **COMP-06** | Reset Comparisons | Remove all comparisons for a project (or specific dimension) to start over. | `POST` | `/projects/{projectId}/comparisons/reset` | **Path**: `projectId`<br>**Body**: `{ "dimension": "string" (optional) }` | **200 OK**: `{ "message": "Comparisons reset", "count": int }` |
| **COMP-07** | Get Resolution Pair | Get a specific pair of features to compare to resolve a detected inconsistency. Identifies the "weakest link" in cycles (highest combined uncertainty). Includes cycle context with count and affected features. | `GET` | `/projects/{projectId}/comparisons/resolve-inconsistency` | **Path**: `projectId`<br>**Query**: `dimension` (required) | **200 OK**: `{ "comparison_id": null, "feature_a": { "id": "uuid", "name": "string", ... }, "feature_b": { "id": "uuid", "name": "string", ... }, "dimension": "string", "reason": "string", "combined_uncertainty": float, "cycle_context": { "cycle_count": int, "features_in_cycles": ["string", ...] } }`<br>**204 No Content** (no inconsistencies detected) |
| **COMP-08** | List Comparisons | Get paginated history of past comparisons for audit/review. Supports batch fetch by IDs. | `GET` | `/projects/{projectId}/comparisons` | **Path**: `projectId`<br>**Query**: `dimension`, `page` (int), `per_page` (int), `ids` (comma-separated UUIDs, optional) - When provided, fetches specific comparisons by ID (ignores pagination) | **200 OK**: `{ "items": [ { "id": "uuid", "feature_a": { "id": "uuid", "name": "string" }, "feature_b": { "id": "uuid", "name": "string" }, "choice": "string", "dimension": "string", "created_at": "datetime" } ], "total": int, "page": int }` |
| **COMP-09** | Get Comparison Progress | Get current comparison progress as percentage toward target certainty using a hybrid confidence model (transitive coverage, Bayesian confidence, consistency). | `GET` | `/projects/{projectId}/comparisons/progress` | **Path**: `projectId`<br>**Query**: `dimension`, `target_certainty` (float, default 0.90) | **200 OK**: `{ "dimension": "string", "target_certainty": float, "transitive_coverage": float, "effective_confidence": float, "progress_percent": float, "comparisons_done": int, "comparisons_remaining": int, "cycle_count": int, ... }` (see api.md for full schema) |
| **COMP-10** | Undo Last Comparison | Undo the most recent comparison for a dimension. Returns updated progress for immediate UI feedback. | `POST` | `/projects/{projectId}/comparisons/undo` | **Path**: `projectId`<br>**Body**: `{ "dimension": "string" }` | **200 OK**: `{ "undone_comparison_id": "uuid", "message": "Comparison undone", "updated_progress": { "comparisons_done": int, "progress_percent": float } }`<br>**404 Not Found** (if no comparisons to undo) |
| **COMP-11** | Skip Comparison | Skip a comparison pair if the user is unsure. The pair may be presented again later. | `POST` | `/projects/{projectId}/comparisons/skip` | **Path**: `projectId`<br>**Body**: `{ "comparison_id": "uuid" }` | **200 OK**: `{ "status": "skipped" }` |
| **COMP-12** | Get Comparison | Get details of a specific comparison. | `GET` | `/projects/{projectId}/comparisons/{comparisonId}` | **Path**: `projectId`, `comparisonId` | **200 OK**: `{ "id": "uuid", "feature_a": { "id": "uuid", "name": "string" }, "feature_b": { "id": "uuid", "name": "string" }, "choice": "string", "dimension": "string", "created_at": "datetime" }`<br>**404 Not Found** |
| **COMP-13** | Update Comparison | Update an existing comparison result. | `PUT` | `/projects/{projectId}/comparisons/{comparisonId}` | **Path**: `projectId`, `comparisonId`<br>**Body**: `{ "choice": "feature_a" \| "feature_b" \| "tie" }` | **200 OK**: `{ "id": "uuid", "choice": "string", "updated_at": "datetime" }`<br>**404 Not Found** |

## 6. Statistics & Analysis

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **STAT-01** | Get Project Stats | Get current state statistics including total comparisons, average variance, etc. | `GET` | `/projects/{projectId}/statistics` | **Path**: `projectId` | **200 OK**: `{ "total_features": int, "comparisons_count": { "complexity": int, "value": int }, "average_variance": { "complexity": float, "value": float } }` |
| **STAT-02** | Get Feature Scores | Get raw scores and variance for all features. | `GET` | `/projects/{projectId}/statistics/scores` | **Path**: `projectId` | **200 OK**: `[ { "feature_id": "uuid", "name": "string", "complexity": { "mu": float, "sigma_sq": float }, "value": { "mu": float, "sigma_sq": float } } ]` |

## 7. Results

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RES-01** | Get Ranked Results | Get the final ranked list of features. Optionally includes quadrant analysis. | `GET` | `/projects/{projectId}/results` | **Path**: `projectId`<br>**Query**: `sort_by` (complexity, value, ratio), `include_quadrants` (bool, optional) - When true, includes quadrant categorization in response | **200 OK**: `[ { "rank": int, "feature": { "id": "uuid", "name": "string", "description": "string" }, "score": float, "variance": float, "confidence_interval": [float, float] } ]` or `{ "results": [...], "quadrants": { "quick_wins": [...], "strategic": [...], "fill_ins": [...], "avoid": [...] } }` (if include_quadrants=true) |
| **RES-02** | Get Quadrant Analysis | Get features categorized into four quadrants (Quick-Wins, Strategic, Fill-Ins, Avoid) based on complexity and value splits. | `GET` | `/projects/{projectId}/results/quadrants` | **Path**: `projectId` | **200 OK**: `{ "quick_wins": [ { "id": "uuid", "name": "string" } ], "strategic": [...], "fill_ins": [...], "avoid": [...] }` |
| **RES-03** | Export Results | Export ranked results in various formats for reporting. | `GET` | `/projects/{projectId}/results/export` | **Path**: `projectId`<br>**Query**: `format` (enum: json, csv), `sort_by` (complexity, value, ratio) | **200 OK**: File download (CSV) or JSON array |

## 8. Model Configuration & Controls

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MODEL-01** | Get Model Config | Retrieve the Bayesian/Thurstone-Mosteller configuration for a project, split per dimension. | `GET` | `/projects/{projectId}/model-config` | **Path**: `projectId` | **200 OK**: `{ "dimensions": { "complexity": { "prior_mean": float, "prior_variance": float, "logistic_scale": float, "tie_tolerance": float, "target_variance": float }, "value": { ... } }, "selection_strategy": "entropy" \| "variance", "max_parallel_pairs": int }` |
| **MODEL-02** | Update Model Config | Update configurable parameters that govern Bayesian updates (priors, tie tolerance, stopping variance). | `PUT` | `/projects/{projectId}/model-config` | **Path**: `projectId`<br>**Body**: `{ "dimensions": { "complexity": { "prior_mean": float, "prior_variance": float, "logistic_scale": float, "target_variance": float, "tie_tolerance": float } }, "selection_strategy": "entropy" \| "variance", "max_parallel_pairs": int }` | **200 OK**: `{ "message": "Model config updated", "effective_from": "datetime" }`<br>**400 Bad Request** (invalid ranges) |
| **MODEL-03** | Preview Impact | Simulate the expected comparison counts/variance using a draft configuration without persisting it. | `POST` | `/projects/{projectId}/model-config/preview` | **Path**: `projectId`<br>**Body**: `{ "dimensions": { ... } }` | **200 OK**: `{ "complexity": { "expected_comparisons": int, "predicted_variance": float }, "value": { ... } }` |
| **MODEL-04** | Reset Model Config | Reset the project's model configuration back to system defaults. | `POST` | `/projects/{projectId}/model-config/reset` | **Path**: `projectId` | **200 OK**: `{ "message": "Model config reset", "defaults": { ... } }` |

## 9. Database Administration (Root Only)

| ID | Name | Description | Method | Endpoint | Parameters | Responses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DB-01** | Create Backup | Create a full database backup. Root access required. | `POST` | `/admin/database/backup` | None | **200 OK**: `{ "backup_id": "uuid", "filename": "string", "size_bytes": int, "created_at": "datetime" }` |
| **DB-02** | List Backups | Get all available database backups. Root access required. | `GET` | `/admin/database/backups` | None | **200 OK**: `[ { "backup_id": "uuid", "filename": "string", "size_bytes": int, "created_at": "datetime" } ]` |
| **DB-03** | Download Backup | Download a specific backup file. Root access required. | `GET` | `/admin/database/backups/{backupId}` | **Path**: `backupId` | **200 OK**: File download (SQLite database) |
| **DB-04** | Restore Backup | Restore database from a backup. Root access required. | `POST` | `/admin/database/restore` | **Body**: `{ "backup_id": "uuid" }` | **200 OK**: `{ "message": "Database restored", "restored_at": "datetime" }`<br>**503 Service Unavailable** (during restore) |
| **DB-05** | Get Database Stats | Get database health and size statistics. Root access required. | `GET` | `/admin/database/stats` | None | **200 OK**: `{ "size_bytes": int, "table_counts": { "users": int, "projects": int, "features": int, "comparisons": int }, "last_vacuum": "datetime", "integrity_ok": bool }` |
| **DB-06** | Run Maintenance | Run database maintenance (VACUUM, integrity check). Root access required. | `POST` | `/admin/database/maintenance` | **Body**: `{ "operation": "vacuum" \| "integrity_check" \| "optimize" }` | **200 OK**: `{ "message": "Maintenance completed", "duration_ms": int, "details": {} }` |
| **DB-07** | Bulk Data Export | Export all data for a project or entire system. Root access required. | `GET` | `/admin/database/export` | **Query**: `project_id` (optional uuid), `format` (json \| sql) | **200 OK**: File download (JSON or SQL dump) |
| **DB-08** | Bulk Data Import | Import data from a previous export. Root access required. | `POST` | `/admin/database/import` | **Body**: Multipart file upload | **200 OK**: `{ "message": "Import completed", "projects_imported": int, "features_imported": int }` |
