# API Reference

Base URL: `/api/v1`

All endpoints except authentication require a valid JWT token in the `Authorization` header: `Bearer <token>`

## Authentication

### Login

`POST /api/v1/auth/login`

OAuth2 compatible token login, get an access token for future requests.

**Request Body (Form Data):**
*   `username` (string, required): The user's email or username.
*   `password` (string, required): The user's password.

**Response (200 OK):**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

**Response (401 Unauthorized):**
*   Invalid credentials.

### Test Token

`POST /api/v1/auth/login/test-token`

Test access token. Returns the current user.

**Response (200 OK):**
*   Returns a [User](#user-object) object.

### Register

`POST /api/v1/auth/register`

Register a new user account.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

**Response (201 Created):**
*   Returns the created [User](#user-object) object.

**Response (400 Bad Request):**
*   Username or email already exists.

### Change Password

`POST /api/v1/auth/change-password`

Change the current user's password.

**Request Body:**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**Response (204 No Content):**
*   Password changed successfully.

**Response (400 Bad Request):**
*   Weak password.

**Response (401 Unauthorized):**
*   Wrong current password.

### Refresh Token

`POST /api/v1/auth/refresh`

Refresh the access token without requiring the user to log in again.

**When to Use:**
- When your access token is about to expire or has expired
- To maintain a seamless user experience without forcing re-authentication
- For long-running applications or sessions that exceed the token lifetime

Access tokens have a limited lifetime for security reasons. **In this backend, access tokens expire after 30 minutes.** When a token expires, API requests will return a 401 Unauthorized error. Instead of requiring users to log in again with their credentials, you can use the refresh token to obtain a new access token. This keeps your application secure while maintaining a smooth user experience.

**Best Practice:** Implement token refresh logic in your client application to automatically refresh tokens before they expire (e.g., refresh at 25 minutes to provide a buffer).

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

**Response (200 OK):**
```json
{
  "access_token": "string",
  "refresh_token": "string"
}
```

**Response (401 Unauthorized):**
*   Refresh token is invalid or expired. User must log in again.

### Get Current User

`GET /api/v1/auth/me`

Get the current authenticated user's profile.

**Response (200 OK):**
*   Returns a [User](#user-object) object.

### Update Profile

`PATCH /api/v1/auth/me`

Update the current user's profile.

**Request Body:**
```json
{
  "email": "string",
  "display_name": "string",
  "avatar_url": "string"
}
```

**Response (200 OK):**
*   Returns the updated [User](#user-object) object.

### Logout

`POST /api/v1/auth/logout`

Logout the current user.

**Response (204 No Content):**
*   Successfully logged out.

## Users

### Get Users

`GET /api/v1/users/`

Retrieve users. Requires superuser privileges.

**Parameters:**
*   `skip` (integer, optional, default=0): Number of records to skip.
*   `limit` (integer, optional, default=100): Maximum number of records to return.

**Response (200 OK):**
*   List of [User](#user-object) objects.

**Response (403 Forbidden):**
*   User does not have superuser privileges.

### Create User

`POST /api/v1/users/`

Create new user. Requires superuser privileges.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "is_active": true,
  "is_superuser": false
}
```

**Response (200 OK):**
*   Returns the created [User](#user-object) object.

### Get Current User

`GET /api/v1/users/me`

Get current user.

**Response (200 OK):**
*   Returns the current [User](#user-object) object.

### Update Current User

`PUT /api/v1/users/me`

Update own user.

**Request Body:**
```json
{
  "password": "string",
  "username": "string",
  "email": "string"
}
```

**Response (200 OK):**
*   Returns the updated [User](#user-object) object.

### Get User by ID

`GET /api/v1/users/{user_id}`

Get a specific user by id.

**Parameters:**
*   `user_id` (string, required): The UUID of the user.

**Response (200 OK):**
*   Returns a [User](#user-object) object.

**Response (404 Not Found):**
*   User not found.

### Update User

`PUT /api/v1/users/{user_id}`

Update a user. Requires superuser privileges.

**Parameters:**
*   `user_id` (string, required): The UUID of the user.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "is_active": true,
  "is_superuser": false
}
```

**Response (200 OK):**
*   Returns the updated [User](#user-object) object.

### Delete User

`DELETE /api/v1/users/{user_id}`

Delete a user. Requires superuser privileges.

**Parameters:**
*   `user_id` (string, required): The UUID of the user.
*   `transfer_to` (string, query, optional): UUID of user to transfer ownership to.

**Response (204 No Content):**
*   User deleted successfully.

**Response (404 Not Found):**
*   User not found.

### Assign Project to User

`POST /api/v1/users/{user_id}/assignments`

Assign a project to a user.

**Parameters:**
*   `user_id` (string, required): The UUID of the user.

**Request Body:**
```json
{
  "project_id": "uuid"
}
```

**Response (200 OK):**
*   Project assigned successfully.

**Response (404 Not Found):**
*   User or Project not found.

### Update User Role

`PATCH /api/v1/users/{user_id}/role`

Update a user's role. Requires superuser privileges.

**Parameters:**
*   `user_id` (string, required): The UUID of the user.

**Request Body:**
```json
{
  "role": "root" | "user"
}
```

**Response (200 OK):**
*   Returns the updated [User](#user-object) object.

**Response (403 Forbidden):**
*   Insufficient permissions.

### Get User Projects

`GET /api/v1/users/{user_id}/projects`

List all projects for a specific user.

**Parameters:**
*   `user_id` (string, required): The UUID of the user.

**Response (200 OK):**
*   List of [Project](#project-object) objects.

**Response (403 Forbidden):**
*   Insufficient permissions.

## Projects

### Get Projects

`GET /api/v1/projects/`

Retrieve projects for the current user.

**Parameters:**
*   `skip` (integer, optional, default=0)
*   `limit` (integer, optional, default=100)

**Response (200 OK):**
*   List of [Project](#project-object) objects.

### Create Project

`POST /api/v1/projects/`

Create new project.

**Request Body:**
```json
{
  "name": "string",
  "description": "string"
}
```

**Response (201 Created):**
*   Returns the created [Project](#project-object) object.

### Get Project

`GET /api/v1/projects/{id}`

Get project by ID.

**Parameters:**
*   `id` (string, required): The UUID of the project.

**Response (200 OK):**
*   Returns a [Project](#project-object) object.

**Response (404 Not Found):**
*   Project not found.

### Update Project

`PUT /api/v1/projects/{id}`

Update a project.

**Parameters:**
*   `id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "name": "string",
  "description": "string"
}
```

**Response (200 OK):**
*   Returns the updated [Project](#project-object) object.

### Delete Project

`DELETE /api/v1/projects/{id}`

Delete a project.

**Parameters:**
*   `id` (string, required): The UUID of the project.

**Response (204 No Content):**
*   Project deleted successfully.

### Get Project Summary

`GET /api/v1/projects/{id}/summary`

Get a summary of project statistics and progress.

**Parameters:**
*   `id` (string, required): The UUID of the project.

**Response (200 OK):**
```json
{
  "project": { ...Project Object... },
  "feature_count": 0,
  "comparison_count": 0,
  "progress": {
    "complexity": 0.0,
    "value": 0.0
  }
}
```

### Get Project Collaborators

`GET /api/v1/projects/{id}/collaborators`

List all collaborators for a project.

**Parameters:**
*   `id` (string, required): The UUID of the project.

**Response (200 OK):**
*   List of collaborator objects with user information and roles.

### Get Project Activity

`GET /api/v1/projects/{id}/activity`

Get activity log for a project.

**Parameters:**
*   `id` (string, required): The UUID of the project.
*   `page` (integer, query, optional): Page number.
*   `per_page` (integer, query, optional): Items per page.
*   `action_type` (string, query, optional): Filter by action type.

**Response (200 OK):**
```json
{
  "items": [
    {
      "action": "string",
      "timestamp": "datetime",
      "user_id": "uuid"
    }
  ],
  "total": 0,
  "page": 1,
  "per_page": 20
}
```

### Get Last Modified

`GET /api/v1/projects/{id}/last-modified`

Get the last modification timestamp for a project.

**Parameters:**
*   `id` (string, required): The UUID of the project.

**Response (200 OK):**
```json
{
  "last_modified": "datetime",
  "modified_by": "uuid"
}
```

### Get Comparison History

`GET /api/v1/projects/{id}/history`

Get complete audit trail of all comparisons made in a project, including both active and deleted comparisons. This provides a full history for auditing purposes.

**Parameters:**
*   `id` (string, required): The UUID of the project.

**Response (200 OK):**
```json
{
  "project": {
    "id": "uuid",
    "name": "string",
    "description": "string"
  },
  "comparisons": [
    {
      "id": "uuid",
      "feature_a": {
        "id": "uuid",
        "name": "string"
      },
      "feature_b": {
        "id": "uuid",
        "name": "string"
      },
      "choice": "feature_a" | "feature_b" | "tie",
      "dimension": "complexity" | "value",
      "user": {
        "id": "uuid",
        "username": "string"
      },
      "created_at": "datetime"
    }
  ],
  "deleted_comparisons": [
    {
      "id": "uuid",
      "feature_a": {
        "id": "uuid",
        "name": "string"
      },
      "feature_b": {
        "id": "uuid",
        "name": "string"
      },
      "choice": "string",
      "dimension": "string",
      "user": {
        "id": "uuid",
        "username": "string"
      },
      "created_at": "datetime",
      "deleted_at": "datetime",
      "deleted_by": {
        "id": "uuid",
        "username": "string"
      }
    }
  ]
}
```

**Response (404 Not Found):**
*   Project not found.

## Features

All feature endpoints are nested under projects: `/api/v1/projects/{project_id}/features`

### Get Features

`GET /api/v1/projects/{project_id}/features`

Retrieve features for a project.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `page` (integer, query, optional, default=1)
*   `per_page` (integer, query, optional, default=50)
*   `search` (string, query, optional): Search term to filter features.

**Response (200 OK):**
```json
{
  "items": [ ...Feature Objects... ],
  "total": 0,
  "page": 1,
  "per_page": 50
}
```

### Create Feature

`POST /api/v1/projects/{project_id}/features`

Create new feature in a project.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "name": "string",
  "description": "string",
  "tags": ["string"]
}
```

**Response (201 Created):**
*   Returns the created [Feature](#feature-object) object.

### Bulk Create Features

`POST /api/v1/projects/{project_id}/features/bulk`

Create multiple features at once.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "features": [
    {
      "name": "string",
      "description": "string",
      "tags": ["string"]
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "count": 0,
  "features": [ ...Feature Objects... ]
}
```

### Bulk Delete Features

`POST /api/v1/projects/{project_id}/features/bulk-delete`

Delete multiple features at once.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "feature_ids": ["uuid", "uuid"]
}
```

**Response (200 OK):**
```json
{
  "deleted_count": 0
}
```

### Get Feature

`GET /api/v1/projects/{project_id}/features/{feature_id}`

Get feature by ID.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `feature_id` (string, required): The UUID of the feature.

**Response (200 OK):**
*   Returns a [Feature](#feature-object) object.

**Response (404 Not Found):**
*   Feature not found.

### Update Feature

`PUT /api/v1/projects/{project_id}/features/{feature_id}`

Update a feature.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `feature_id` (string, required): The UUID of the feature.

**Request Body:**
```json
{
  "name": "string",
  "description": "string",
  "tags": ["string"]
}
```

**Response (200 OK):**
*   Returns the updated [Feature](#feature-object) object.

### Delete Feature

`DELETE /api/v1/projects/{project_id}/features/{feature_id}`

Delete a feature.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `feature_id` (string, required): The UUID of the feature.

**Response (204 No Content):**
*   Feature deleted successfully.

## Comparisons

All comparison endpoints are nested under projects: `/api/v1/projects/{project_id}/comparisons`

### Get Next Comparison Pair

`GET /api/v1/projects/{project_id}/comparisons/next`

Get the next pair of features to compare. This is the primary endpoint for the comparison workflow.

The endpoint uses a chain-building algorithm that leverages transitive closure for O(N log N) efficiency. When `target_certainty` is specified, the endpoint returns 204 once the transitive coverage reaches that threshold, enabling early stopping without exhaustive comparisons.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `dimension` (string, query, required): One of "complexity", "value".
*   `target_certainty` (number, query, optional, default=0.0): Target transitive coverage level (0.0-1.0). When set to a value > 0, the endpoint returns 204 No Content once transitive coverage reaches this threshold. Common values: 0.7 (70%), 0.8 (80%), 0.9 (90%). When set to 0.0 (default), comparisons continue until all orderings are known via transitivity.

**Response (200 OK):**
```json
{
  "comparison_id": "uuid",
  "feature_a": { ...Feature Object... },
  "feature_b": { ...Feature Object... },
  "dimension": "complexity" | "value"
}
```

**Response (204 No Content):**
*   Target certainty reached (when `target_certainty` > 0 and transitive coverage ≥ target), or
*   All orderings are known via transitive inference, or
*   No useful comparisons left to make.

**Usage Example:**
```
GET /api/v1/projects/{id}/comparisons/next?dimension=complexity&target_certainty=0.9
```
This requests the next comparison pair and will return 204 once 90% transitive coverage is achieved.

**Efficiency:**
With transitive closure optimization, reaching 90% certainty for N features typically requires approximately N × log₂(N) comparisons per dimension, rather than the theoretical maximum of N×(N-1)/2 pairwise comparisons.

### Get Comparisons

`GET /api/v1/projects/{project_id}/comparisons`

Retrieve comparison history for a project.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `dimension` (string, query, optional): Filter by dimension.
*   `page` (integer, query, optional)
*   `per_page` (integer, query, optional)

**Response (200 OK):**
```json
{
  "items": [ ...Comparison Objects... ],
  "total": 0,
  "page": 1,
  "per_page": 20
}
```

### Create Comparison

`POST /api/v1/projects/{project_id}/comparisons`

Submit a comparison result. This endpoint performs a Bayesian update to the feature rankings and returns the comparison along with current inconsistency statistics for immediate UI feedback.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "feature_a_id": "uuid",
  "feature_b_id": "uuid",
  "choice": "feature_a" | "feature_b" | "tie",
  "dimension": "complexity" | "value"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "feature_a": {
    "id": "uuid",
    "name": "string"
  },
  "feature_b": {
    "id": "uuid",
    "name": "string"
  },
  "choice": "feature_a" | "feature_b" | "tie",
  "dimension": "complexity" | "value",
  "created_at": "datetime",
  "inconsistency_stats": {
    "cycle_count": 0,
    "total_comparisons": 0,
    "inconsistency_percentage": 0.0,
    "dimension": "complexity" | "value"
  }
}
```

The `inconsistency_stats` object provides immediate feedback about the health of the comparison graph, allowing UIs to display warnings when inconsistencies are detected.

### Get Comparison Estimates

`GET /api/v1/projects/{project_id}/comparisons/estimates`

Get current estimates for all features based on comparisons made.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `dimension` (string, query, required): One of "complexity", "value".

**Response (200 OK):**
```json
{
  "dimension": "complexity" | "value",
  "estimates": [
    {
      "feature_id": "uuid",
      "estimate": 0.0,
      "variance": 0.0
    }
  ]
}
```

### Get Inconsistency Statistics

`GET /api/v1/projects/{project_id}/comparisons/inconsistency-stats`

Get a summary of inconsistency statistics without detailed cycle information. This lightweight endpoint is ideal for dashboard widgets, health checks, and polling for updates.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `dimension` (string, query, optional): Filter by dimension ("complexity" or "value"). If omitted, returns stats for both dimensions.

**Response (200 OK):**
```json
{
  "cycle_count": 0,
  "total_comparisons": 0,
  "inconsistency_percentage": 0.0,
  "dimension": "complexity" | "value"
}
```

**Use Cases:**
*   Dashboard widgets showing project health
*   Real-time polling for inconsistency alerts
*   Quick health checks without fetching full cycle details

### Get Inconsistencies

`GET /api/v1/projects/{project_id}/comparisons/inconsistencies`

Detect and return detailed information about inconsistent comparison cycles (e.g., A > B > C > A). This endpoint performs a depth-first search on the comparison graph to identify all cycles, which represent logical inconsistencies where the transitive property of comparisons is violated.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `dimension` (string, query, optional): Filter by dimension ("complexity" or "value"). If omitted, detects cycles in both dimensions.

**Response (200 OK):**
```json
{
  "cycles": [
    {
      "feature_ids": ["uuid", "uuid", "uuid"],
      "feature_names": ["Feature A", "Feature B", "Feature C"],
      "length": 3,
      "dimension": "complexity" | "value"
    }
  ],
  "count": 0,
  "message": "Found N inconsistency cycles"
}
```

**Algorithm:**
Uses depth-first search (DFS) with cycle detection. Time complexity: O(V + E) where V is the number of features and E is the number of comparisons. Typical performance: <1ms for 70 features.

**Cycle Interpretation:**
A cycle like [A, B, C] means: A > B > C > A, which is logically inconsistent. The cycle represents a sequence of comparisons where following the "winner" edges leads back to the starting feature.

### Get Resolution Pair

`GET /api/v1/projects/{project_id}/comparisons/resolve-inconsistency`

Get a specific pair of features to compare to resolve detected inconsistencies. Uses the "weakest link" strategy: identifies all cycles, examines pairs in those cycles, and suggests re-comparing the pair with the highest combined uncertainty (σ_i + σ_j). This approach targets the comparison most likely to be incorrect.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `dimension` (string, query, required): The dimension to check ("complexity" or "value").

**Response (200 OK):**
```json
{
  "comparison_id": null,
  "feature_a": {
    "id": "uuid",
    "name": "string",
    "description": "string"
  },
  "feature_b": {
    "id": "uuid",
    "name": "string",
    "description": "string"
  },
  "dimension": "complexity" | "value",
  "reason": "Weakest link in cycle: highest combined uncertainty",
  "combined_uncertainty": 2.5
}
```

**Response (204 No Content):**
*   No inconsistencies detected in the specified dimension.

**Strategy:**
The weakest link approach assumes that pairs with high uncertainty are more likely to have incorrect comparison results. By re-comparing these pairs, users can potentially break the cycle and restore consistency to the comparison graph.

### Get Comparison Progress

`GET /api/v1/projects/{project_id}/comparisons/progress`

Get progress metrics for comparisons in a project using a hybrid confidence model that combines transitive coverage, Bayesian confidence, and consistency scoring.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `dimension` (string, query, required): One of "complexity", "value".
*   `target_certainty` (number, query, optional, default=0.90): Target certainty level (0.0-1.0).

**Response (200 OK):**
```json
{
  "dimension": "complexity",
  "target_certainty": 0.90,
  
  "transitive_coverage": 0.85,
  "transitive_known_pairs": 34,
  "uncertain_pairs": 6,
  
  "direct_coverage": 0.45,
  "unique_pairs_compared": 18,
  "total_possible_pairs": 40,
  
  "coverage_confidence": 0.45,
  "bayesian_confidence": 0.72,
  "consistency_score": 1.0,
  "effective_confidence": 0.88,
  "progress_percent": 88.0,
  
  "total_comparisons_done": 22,
  "comparisons_remaining": 3,
  "theoretical_minimum": 22,
  "practical_estimate": 27,
  
  "current_avg_variance": 0.28,
  "comparisons_done": 22,
  "cycle_count": 0
}
```

**Key Fields:**
*   `transitive_coverage`: Fraction of pairs with known ordering (0.0-1.0), including those inferred via transitivity. **Primary progress metric.**
*   `effective_confidence`: Combined confidence score considering transitivity, Bayesian updates, and consistency.
*   `uncertain_pairs`: Number of pairs whose ordering is still unknown.
*   `theoretical_minimum`: Information-theoretic lower bound: ⌈log₂(N!)⌉
*   `practical_estimate`: Expected comparisons needed for target: ~0.77 × N × log₂(N) for 90% target.
*   `cycle_count`: Number of detected logical inconsistencies (A>B>C>A cycles).

### Reset Comparisons

`POST /api/v1/projects/{project_id}/comparisons/reset`

Reset all comparisons for a project or dimension.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "dimension": "complexity" | "value"
}
```

**Response (200 OK):**
```json
{
  "message": "string",
  "count": 0
}
```

### Undo Last Comparison

`POST /api/v1/projects/{project_id}/comparisons/undo`

Undo the last comparison made.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "dimension": "complexity" | "value"
}
```

**Response (200 OK):**
```json
{
  "undone_comparison_id": "uuid",
  "message": "string"
}
```

**Response (404 Not Found):**
*   No comparisons to undo.

### Skip Comparison

`POST /api/v1/projects/{project_id}/comparisons/skip`

Skip a comparison pair without recording a result.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "comparison_id": "uuid"
}
```

**Response (200 OK):**
```json
{
  "status": "skipped"
}
```

### Get Comparison

`GET /api/v1/projects/{project_id}/comparisons/{comparison_id}`

Get comparison by ID.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `comparison_id` (string, required): The UUID of the comparison.

**Response (200 OK):**
*   Returns a [Comparison](#comparison-object) object.

### Update Comparison

`PUT /api/v1/projects/{project_id}/comparisons/{comparison_id}`

Update a comparison result.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `comparison_id` (string, required): The UUID of the comparison.

**Request Body:**
```json
{
  "choice": "feature_a" | "feature_b" | "tie"
}
```

**Response (200 OK):**
*   Returns the updated [Comparison](#comparison-object) object.

### Delete Comparison

`DELETE /api/v1/projects/{project_id}/comparisons/{comparison_id}`

Delete a comparison.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `comparison_id` (string, required): The UUID of the comparison.

**Response (204 No Content):**
*   Comparison deleted successfully.

## Statistics

All statistics endpoints are nested under projects: `/api/v1/projects/{project_id}/statistics`

### Get Project Statistics

`GET /api/v1/projects/{project_id}/statistics`

Get comprehensive statistics for a project.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Response (200 OK):**
```json
{
  "feature_count": 0,
  "comparison_count": 0,
  "dimensions": {
    "complexity": {
      "comparisons": 0,
      "progress": 0.0
    },
    "value": {
      "comparisons": 0,
      "progress": 0.0
    }
  }
}
```

### Get Feature Scores

`GET /api/v1/projects/{project_id}/statistics/scores`

Get computed scores for all features in a project.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Response (200 OK):**
```json
[
  {
    "feature_id": "uuid",
    "feature_name": "string",
    "complexity_score": 0.0,
    "value_score": 0.0,
    "ratio": 0.0
  }
]
```

## Results

All results endpoints are nested under projects: `/api/v1/projects/{project_id}/results`

### Get Ranked Results

`GET /api/v1/projects/{project_id}/results`

Get ranked and scored results for all features.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `sort_by` (string, query, optional): One of "complexity", "value", "ratio".

**Response (200 OK):**
```json
[
  {
    "feature": { ...Feature Object... },
    "complexity": 0.0,
    "value": 0.0,
    "ratio": 0.0,
    "rank": 1
  }
]
```

### Get Quadrant Analysis

`GET /api/v1/projects/{project_id}/results/quadrants`

Get features organized into quadrants based on complexity and value.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Response (200 OK):**
```json
{
  "quick_wins": [ ...Feature Objects... ],
  "major_projects": [ ...Feature Objects... ],
  "fill_ins": [ ...Feature Objects... ],
  "thankless_tasks": [ ...Feature Objects... ]
}
```

### Export Results

`GET /api/v1/projects/{project_id}/results/export`

Export project results in various formats.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.
*   `format` (string, query, optional): One of "json", "csv". Default: "json".
*   `sort_by` (string, query, optional): One of "complexity", "value", "ratio".

**Response (200 OK):**
*   Content-Type: application/json or text/csv depending on format parameter.

## Model Configuration

All model configuration endpoints are nested under projects: `/api/v1/projects/{project_id}/model-config`

### Get Model Configuration

`GET /api/v1/projects/{project_id}/model-config`

Get the current model configuration for a project.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Response (200 OK):**
```json
{
  "model_type": "string",
  "num_features": 0,
  "selection_strategy": "string",
  "dimensions": {
    "complexity": {
      "prior_mean": 0.0,
      "prior_variance": 1.0,
      "target_variance": 0.1
    },
    "value": {
      "prior_mean": 0.0,
      "prior_variance": 1.0,
      "target_variance": 0.1
    }
  }
}
```

### Update Model Configuration

`PUT /api/v1/projects/{project_id}/model-config`

Update the model configuration for a project.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "model_type": "string",
  "selection_strategy": "string",
  "dimensions": {
    "complexity": {
      "prior_mean": 0.0,
      "prior_variance": 1.0,
      "target_variance": 0.1
    }
  }
}
```

**Response (200 OK):**
```json
{
  "model_type": "string",
  "num_features": 0,
  "selection_strategy": "string",
  "updated_at": "datetime"
}
```

**Response (400 Bad Request):**
*   Invalid configuration parameters.

### Preview Configuration Impact

`POST /api/v1/projects/{project_id}/model-config/preview`

Preview the impact of configuration changes without applying them.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Request Body:**
```json
{
  "dimensions": {
    "complexity": {
      "target_variance": 0.05
    }
  }
}
```

**Response (200 OK):**
```json
{
  "estimated_comparisons": 0,
  "current_variance": 0.0,
  "target_variance": 0.0
}
```

### Reset Model Configuration

`POST /api/v1/projects/{project_id}/model-config/reset`

Reset model configuration to default values.

**Parameters:**
*   `project_id` (string, required): The UUID of the project.

**Response (200 OK):**
```json
{
  "message": "Configuration reset to defaults",
  "config": { ...Config Object... }
}
```

## Admin

All admin endpoints require superuser privileges and are prefixed with `/api/v1/admin`

### Create Database Backup

`POST /api/v1/admin/database/backup`

Create a backup of the database.

**Response (200 OK):**
```json
{
  "backup_id": "string",
  "filename": "string",
  "size_bytes": 0,
  "created_at": "datetime"
}
```

### List Database Backups

`GET /api/v1/admin/database/backups`

List all available database backups.

**Response (200 OK):**
```json
[
  {
    "backup_id": "string",
    "filename": "string",
    "size_bytes": 0,
    "created_at": "datetime"
  }
]
```

### Download Backup

`GET /api/v1/admin/database/backups/{backup_id}`

Download a specific backup file.

**Parameters:**
*   `backup_id` (string, required): The ID of the backup.

**Response (200 OK):**
*   Content-Type: application/octet-stream
*   Binary backup file.

### Restore Database

`POST /api/v1/admin/database/restore`

Restore database from a backup.

**Request Body:**
```json
{
  "backup_id": "string"
}
```

**Response (200 OK):**
```json
{
  "message": "Database restored",
  "restored_at": "datetime"
}
```

**Response (503 Service Unavailable):**
*   Service temporarily unavailable during restore.

### Get Database Statistics

`GET /api/v1/admin/database/stats`

Get database statistics and health metrics.

**Response (200 OK):**
```json
{
  "size_bytes": 0,
  "table_counts": {
    "users": 0,
    "projects": 0,
    "features": 0,
    "comparisons": 0
  },
  "last_vacuum": "datetime",
  "integrity_ok": true
}
```

### Run Database Maintenance

`POST /api/v1/admin/database/maintenance`

Run database maintenance operations.

**Request Body:**
```json
{
  "operation": "vacuum" | "integrity_check" | "optimize"
}
```

**Response (200 OK):**
```json
{
  "operation": "string",
  "status": "completed",
  "duration_ms": 0
}
```

### Export Database

`GET /api/v1/admin/database/export`

Bulk export data from the database.

**Parameters:**
*   `project_id` (string, query, optional): Export specific project only.
*   `format` (string, query, optional): One of "json", "sql". Default: "json".

**Response (200 OK):**
*   Content-Type: application/json or application/sql depending on format.

### Import Database

`POST /api/v1/admin/database/import`

Bulk import data into the database.

**Request Body (multipart/form-data):**
*   `file` (file, required): The import file.

**Response (200 OK):**
```json
{
  "status": "completed",
  "records_imported": 0,
  "errors": []
}
```

---

## Data Objects

### User Object
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "is_active": true,
  "is_superuser": false,
  "role": "user" | "root",
  "display_name": "string",
  "avatar_url": "string"
}
```

### Project Object
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "created_at": "datetime",
  "owner_id": "uuid"
}
```

### Feature Object
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "tags": ["string"],
  "project_id": "uuid",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Comparison Object
```json
{
  "id": "uuid",
  "feature_a_id": "uuid",
  "feature_b_id": "uuid",
  "choice": "feature_a" | "feature_b" | "tie",
  "dimension": "complexity" | "value",
  "project_id": "uuid",
  "user_id": "uuid",
  "created_at": "datetime"
}
```

### ComparisonWithStats Object

Returned by the Create Comparison endpoint to provide immediate feedback about inconsistencies:

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "feature_a": {
    "id": "uuid",
    "name": "string"
  },
  "feature_b": {
    "id": "uuid",
    "name": "string"
  },
  "choice": "feature_a" | "feature_b" | "tie",
  "dimension": "complexity" | "value",
  "created_at": "datetime",
  "inconsistency_stats": {
    "cycle_count": 0,
    "total_comparisons": 0,
    "inconsistency_percentage": 0.0,
    "dimension": "complexity" | "value"
  }
}
```
