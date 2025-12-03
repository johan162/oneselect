# Inconsistency Detection

## Overview

OneSelect includes cycle detection to identify logical inconsistencies in pairwise comparisons. These occur when comparison chains form cycles, such as:
- Feature A > Feature B
- Feature B > Feature C  
- Feature C > Feature A

While the Bayesian model handles probabilistic inconsistencies naturally (through variance), detecting hard logical cycles is valuable for identifying comparison pairs that may need re-evaluation.

## Algorithm

### On-Demand Cycle Detection

The implementation uses **on-demand cycle detection** with Depth-First Search (DFS):

1. **Graph Construction**: Build a directed graph from comparisons
   - Nodes = Features
   - Edges = Winner → Loser relationships
   - Ties are excluded (no directed edge)

2. **Cycle Detection**: Use DFS with recursion stack tracking
   - Time Complexity: O(V + E) where V = features, E = comparisons
   - Space Complexity: O(V) for recursion stack
   - Performance: < 1ms for typical 70-feature projects

3. **Cycle Normalization**: Normalize cycles to prevent duplicates
   - Start from lexicographically smallest node
   - Prevents [A,B,C] and [B,C,A] from being counted twice

### Design Rationale

**Why On-Demand?**
- No schema changes or migrations needed
- No persistent data structures to maintain
- No cache invalidation complexity
- Extremely fast for expected scale (70 features, ~100-500 comparisons)
- Cycles are rare in practice (Bayesian updates discourage them)

**Alternatives Considered:**
1. **Cached Graph Structure** - Rejected: adds complexity, cache invalidation issues
2. **Database Edge Table** - Rejected: over-engineered, requires triggers
3. **Materialized Paths** - Rejected: not needed for this scale

## API Endpoints

### POST `/projects/{project_id}/comparisons` (Enhanced)

Creates a comparison and **returns inconsistency statistics** in the response.

**Response includes:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "feature_a": { /* Feature object */ },
  "feature_b": { /* Feature object */ },
  "choice": "feature_a",
  "dimension": "complexity",
  "created_at": "2025-12-03T10:30:00Z",
  "inconsistency_stats": {
    "cycle_count": 2,
    "total_comparisons": 45,
    "inconsistency_percentage": 8.89,
    "dimension": "complexity"
  }
}
```

**Benefits:**
- Single HTTP request = faster UX
- Immediate feedback after user action
- Guaranteed consistency (same transaction)

### GET `/projects/{project_id}/comparisons/inconsistency-stats`

Get inconsistency statistics without creating a comparison.

**Use Cases:**
- Dashboard widgets showing inconsistency count
- Polling for updates without submitting comparisons
- Quick health checks of comparison quality

**Parameters:**
- `dimension` (optional): Filter by "complexity" or "value"

**Response:**
```json
{
  "cycle_count": 2,
  "total_comparisons": 45,
  "inconsistency_percentage": 8.89,
  "dimension": "complexity"
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/projects/{id}/comparisons/inconsistency-stats?dimension=complexity" \
  -H "Authorization: Bearer {token}"
```

### GET `/projects/{project_id}/comparisons/inconsistencies`

Returns **detailed cycle information** with feature names and IDs.

**Parameters:**
- `dimension` (optional): Filter by "complexity" or "value"

**Response:**
```json
{
  "cycles": [
    {
      "feature_ids": ["uuid1", "uuid2", "uuid3", "uuid1"],
      "feature_names": ["Feature A", "Feature B", "Feature C", "Feature A"],
      "length": 3,
      "dimension": "complexity"
    }
  ],
  "count": 1,
  "message": "Found 1 logical inconsistencies"
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8000/api/v1/projects/{id}/comparisons/inconsistencies?dimension=complexity" \
  -H "Authorization: Bearer {token}"
```

### GET `/projects/{project_id}/comparisons/resolve-inconsistency`

Suggests a comparison pair to help resolve detected inconsistencies.

**Strategy:** Finds the "weakest link" in detected cycles - the comparison where the Bayesian model has highest combined uncertainty (σ_i + σ_j). Re-comparing this pair can help break the cycle.

**Parameters:**
- `dimension` (required): "complexity" or "value"

**Response:**
- `200 OK`: Returns a comparison pair to re-evaluate
- `204 No Content`: No inconsistencies detected

```json
{
  "comparison_id": null,
  "feature_a": { /* Feature object */ },
  "feature_b": { /* Feature object */ },
  "dimension": "complexity",
  "reason": "This pair is involved in a logical cycle and has high uncertainty...",
  "combined_uncertainty": 1.85
}
```

## UI Integration Strategy

### Hybrid Approach: Embedded Stats + Dedicated Endpoint

The implementation uses a **hybrid approach** combining the benefits of both patterns:

#### 1. Embedded Stats (POST `/comparisons` response)
**When:** After user submits a comparison
**Benefit:** Immediate feedback without extra HTTP request

```javascript
// Frontend: Submit comparison
const response = await api.createComparison(projectId, comparisonData);
// Response includes inconsistency stats immediately
updateInconsistencyBadge(response.inconsistency_stats);
```

#### 2. Dedicated Endpoint (GET `/inconsistency-stats`)
**When:** 
- Dashboard loads
- Polling/refresh without submitting comparisons
- Health checks

```javascript
// Frontend: Dashboard widget
const stats = await api.getInconsistencyStats(projectId, dimension);
displayStats(stats.cycle_count, stats.inconsistency_percentage);
```

### Performance Characteristics
- **Calculation time**: < 1ms for 70 features
- **Response overhead**: ~50 bytes additional JSON
- **Network impact**: Eliminates one round-trip for common case

### UI Display Recommendations

**Inconsistency Badge:**
```
⚠️ 2 cycles (8.9% of comparisons)
```

**Color Coding:**
- Green (0%): No inconsistencies
- Yellow (< 10%): Minor inconsistencies
- Orange (10-20%): Moderate inconsistencies  
- Red (> 20%): Significant inconsistencies

**When to Show:**
- After every comparison (updated automatically)
- In project summary dashboard
- Before exporting final rankings

## Integration with Bayesian Model

The cycle detection complements the Bayesian Bradley-Terry model:

1. **Probabilistic Inconsistencies**: Handled naturally by variance updates
   - Model becomes less confident when it sees surprising outcomes
   - Variance (σ) reflects this uncertainty

2. **Logical Inconsistencies**: Detected by cycle algorithm
   - Hard cycles (A>B>C>A) indicate potential user error or changing opinions
   - System suggests re-evaluating the most uncertain comparison in the cycle

3. **Resolution Strategy**:
   - Identify cycles with `GET /inconsistencies`
   - Get weakest link with `GET /resolve-inconsistency`
   - Re-compare the suggested pair
   - New comparison updates Bayesian scores and may break the cycle

## Performance Characteristics

### Scalability
- **70 features**: < 1ms detection time
- **2,415 possible pairs**: Worst case ~500-1000 actual comparisons
- **Graph traversal**: O(V + E) = O(70 + 500) = negligible

### Memory Usage
- **Transient graph**: Built in memory only during request
- **No persistent storage**: No database overhead
- **Recursion stack**: Max depth = cycle length (typically 3-5)

### When to Check
- After every 10-20 comparisons
- Before exporting final rankings
- When progress endpoint shows high variance despite many comparisons
- On user request via UI

## Testing

Comprehensive unit tests verify:
- Simple 3-node cycles (A>B>C>A)
- Acyclic graphs (proper rankings)
- Multiple independent cycles
- Complex cycles with branches
- Performance with 70-node graphs

Run tests:
```bash
pytest tests/test_cycle_detection.py -v
```

## Implementation Summary

### Endpoints Provided

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|---------------|
| `/comparisons` | POST | Create comparison + get stats | < 2ms |
| `/comparisons/inconsistency-stats` | GET | Get stats only | < 1ms |
| `/comparisons/inconsistencies` | GET | Get detailed cycles | < 1ms |
| `/comparisons/resolve-inconsistency` | GET | Get resolution suggestion | < 1ms |

### Data Flow

```
User submits comparison
        ↓
POST /comparisons
        ↓
[Bayesian update] + [Stats calculation]
        ↓
Response with comparison + inconsistency_stats
        ↓
UI updates badge: "⚠️ 2 cycles (8.9%)"
```

### Response Schema

**ComparisonWithStats:**
```typescript
{
  id: UUID,
  project_id: UUID,
  feature_a: Feature,
  feature_b: Feature,
  choice: "feature_a" | "feature_b" | "tie",
  dimension: "complexity" | "value",
  created_at: DateTime,
  inconsistency_stats: {
    cycle_count: number,          // Number of detected cycles
    total_comparisons: number,    // Total comparisons for dimension
    inconsistency_percentage: number,  // Percentage with 2 decimals
    dimension: string             // "complexity", "value", or "all"
  }
}
```

### Performance Benchmarks

- **70 features**, **500 comparisons**: < 1ms cycle detection
- **Response overhead**: ~50 bytes JSON
- **Memory usage**: Transient (no persistent storage)
- **Database impact**: None (uses existing comparison data)

## Future Enhancements

Potential improvements (not currently needed):
1. **Cycle severity scoring**: Weight cycles by combined uncertainty
2. **Transitive inconsistency detection**: Check if A>B>C but model says A<C
3. **Cycle history tracking**: Log when cycles appear/disappear
4. **Batch resolution**: Suggest multiple pairs to resolve all cycles efficiently
5. **Redis caching**: Cache stats for high-traffic projects (premature optimization)
6. **WebSocket notifications**: Real-time updates for collaborative sessions
