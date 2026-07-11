# SQL Queries for Inspection and Debugging

Useful queries for understanding what the system is doing. Use `psql` or the database client of your choice:

```bash
# Connect to the local development database
psql postgresql://ecom:change-me-local-only@localhost:5432/ecom
```

## Basic Candidate and Observation Status

```sql
-- All candidates with count of observations and facts
SELECT
    c.id,
    c.name,
    c.status,
    c.created_at,
    COUNT(DISTINCT ro.id) AS observation_count,
    COUNT(DISTINCT f.id) AS fact_count
FROM candidates c
LEFT JOIN raw_observations ro ON c.id = ro.candidate_id
LEFT JOIN facts f ON c.id = f.candidate_id
GROUP BY c.id, c.name, c.status, c.created_at
ORDER BY c.created_at DESC;

-- Observations for a specific candidate (replace UUID)
SELECT
    ro.id,
    ro.observation_type,
    ro.payload,
    ro.source_url,
    ro.fetched_at,
    ro.created_at
FROM raw_observations ro
WHERE ro.candidate_id = 'your-candidate-id'
ORDER BY ro.created_at DESC;
```

## Facts: Current Truth Values

```sql
-- All facts for a candidate, newest first
SELECT
    f.id,
    f.fact_type,
    f.value,
    f.observed_at,
    f.created_at
FROM facts f
WHERE f.candidate_id = 'your-candidate-id'
ORDER BY f.created_at DESC;

-- Latest fact of each type (the current truth)
WITH ranked_facts AS (
    SELECT
        fact_type,
        f.*,
        ROW_NUMBER() OVER (PARTITION BY fact_type ORDER BY created_at DESC) AS rn
    FROM facts f
    WHERE f.candidate_id = 'your-candidate-id'
)
SELECT fact_type, value, observed_at, created_at
FROM ranked_facts
WHERE rn = 1
ORDER BY fact_type;

-- Fact history for a specific type (e.g., sales_rank over time)
SELECT
    value->>'rank' AS rank,
    observed_at,
    created_at
FROM facts
WHERE candidate_id = 'your-candidate-id' AND fact_type = 'sales_rank'
ORDER BY created_at DESC;
```

## Signals: Detected Patterns

```sql
-- All signals for a candidate
SELECT
    s.id,
    s.signal_type,
    s.detector_version,
    s.confidence,
    s.computed_at,
    s.created_at
FROM signals s
WHERE s.candidate_id = 'your-candidate-id'
ORDER BY s.created_at DESC;

-- Signals by type across all candidates
SELECT
    signal_type,
    COUNT(*) AS count,
    AVG(confidence::float) AS avg_confidence,
    MAX(created_at) AS most_recent
FROM signals
GROUP BY signal_type
ORDER BY count DESC;

-- Candidates with a specific signal
SELECT DISTINCT
    c.id,
    c.name,
    s.signal_type,
    MAX(s.created_at) AS most_recent_signal
FROM signals s
JOIN candidates c ON s.candidate_id = c.id
WHERE s.signal_type = 'rank_improved'
GROUP BY c.id, c.name, s.signal_type
ORDER BY most_recent_signal DESC;
```

## Events: Audit Trail

```sql
-- All events for a candidate
SELECT
    e.id,
    e.event_type,
    e.payload,
    e.occurred_at,
    e.created_at
FROM events e
WHERE e.candidate_id = 'your-candidate-id'
ORDER BY e.created_at DESC;

-- Event timeline for a collection run
SELECT
    e.event_type,
    e.payload,
    e.occurred_at
FROM events e
WHERE e.run_id = 'your-run-id'
ORDER BY e.occurred_at;

-- Summary of events by type
SELECT
    event_type,
    COUNT(*) AS count,
    MAX(created_at) AS most_recent
FROM events
GROUP BY event_type
ORDER BY count DESC;

-- Failed collection runs with error details
SELECT
    cr.id,
    cr.source_id,
    cr.status,
    cr.error,
    COUNT(e.id) AS event_count
FROM collection_runs cr
LEFT JOIN events e ON cr.id = e.run_id
WHERE cr.status = 'failed'
GROUP BY cr.id, cr.source_id, cr.status, cr.error
ORDER BY cr.finished_at DESC;
```

## Data Integrity Checks

```sql
-- Verify append-only: facts should never be deleted or updated
-- (This should be enforced by the application layer, but can be verified)
SELECT COUNT(*) AS total_facts FROM facts;

-- Check for orphaned facts (observation deleted but fact remains)
SELECT COUNT(*) AS orphaned_facts
FROM facts f
WHERE f.source_observation_id IS NOT NULL
  AND f.source_observation_id NOT IN (SELECT id FROM raw_observations);

-- Check for orphaned signals
SELECT COUNT(*) AS orphaned_signals
FROM signals s
WHERE s.candidate_id NOT IN (SELECT id FROM candidates);

-- Verify fact_ids array in signals contains valid UUIDs
SELECT
    s.id,
    s.signal_type,
    s.fact_ids
FROM signals s
WHERE s.fact_ids != '[]'::jsonb
LIMIT 10;
```

## Source and Collection Status

```sql
-- All sources with count of collection runs
SELECT
    s.id,
    s.key,
    s.display_name,
    s.compliance,
    s.enabled,
    COUNT(cr.id) AS run_count,
    COUNT(CASE WHEN cr.status = 'succeeded' THEN 1 END) AS succeeded,
    COUNT(CASE WHEN cr.status = 'failed' THEN 1 END) AS failed
FROM sources s
LEFT JOIN collection_runs cr ON s.id = cr.source_id
GROUP BY s.id, s.key, s.display_name, s.compliance, s.enabled
ORDER BY run_count DESC;

-- Recent collection runs for a source (replace 'keepa' with source key)
SELECT
    cr.id,
    cr.candidate_id,
    cr.status,
    cr.error,
    cr.started_at,
    cr.finished_at
FROM collection_runs cr
JOIN sources s ON cr.source_id = s.id
WHERE s.key = 'keepa'
ORDER BY cr.created_at DESC
LIMIT 20;
```

## Performance and Growth

```sql
-- Database size by table
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Row counts by table
SELECT
    tablename,
    n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- Observations per day (last 30 days)
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS observation_count
FROM raw_observations
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## Notes

- Replace `'your-candidate-id'` with actual UUIDs (e.g., `'550e8400-e29b-41d4-a716-446655440000'`)
- Facts and Signals are append-only: new versions are added, old ones are never deleted
- The "current truth" for a fact type is always the newest fact of that type
- Signals are provider-agnostic (e.g., `rank_improved` can come from Keepa, AliExpress, etc.)
- Events are the audit trail and drive downstream systems (agents, dashboards)
