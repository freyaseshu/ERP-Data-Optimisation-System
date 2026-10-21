"""Capabilities and honest boundaries derived from shipped code; no invented test claims."""
from pathlib import Path

# Status describes implemented scope, not a claim of production readiness.
ITEMS = [
('Large Dataset Processing', 'Large tables increase latency and load.', 'Slow browsing and greater memory use.', 'Atomic small/medium/large dataset loader with scaling; paginated search.', 'Partially Implemented', 'Multi-million row workloads remain untested.'),
('Slow SQL Queries', 'Poor access paths and joins can be expensive.', 'Slower ERP reports.', 'PostgreSQL JSON EXPLAIN and EXPLAIN ANALYZE, filtered-scan candidates, measured index comparisons.', 'Implemented', 'Recommendations are heuristics; inspect actual plans before approval.'),
('Limited Automatic Optimisation', 'Arbitrary rewrites cannot be proven safe automatically.', 'Changed query meaning or extra indexes.', 'Pending recommendations, admin approval/rejection, transactional index application and full result multiset verification.', 'Partially Implemented', 'Automatic query rewriting is unavailable; projection suggestions require human selection.'),
('Database Dependency', 'Database syntax and drivers differ.', 'Setup can fail on the wrong engine.', 'Central PostgreSQL + psycopg configuration; connection status and explicit schema initialisation.', 'Implemented', 'Existing incompatible schemas need a reviewed migration.'),
('Hardware and Environment Dependency', 'Hardware, load and caches affect timing.', 'Results differ between machines.', 'Record OS, CPU count, PostgreSQL settings, warm-ups, repeated timings and standard deviation.', 'Implemented', 'No controlled cold-cache or hardware-isolated testing.'),
('Indexing Overhead', 'Indexes consume space and add write work.', 'Slower writes and greater storage use.', 'Show existing index size and scan counters; reject duplicate leading columns; require admin approval.', 'Partially Implemented', 'Write overhead is explained but not measured. No automatic removal or redundancy verdict.'),
('Limited Real-Time Monitoring', 'Manual analysis misses other database activity.', 'Some performance spikes go unrecorded.', 'Timestamped history, manual refresh and optional 30-second dashboard polling.', 'Partially Implemented', 'No continuous pg_stat_statements collector.'),
('Security and Data Privacy', 'SQL execution and credentials need protection.', 'Unauthorised data changes or disclosure.', 'Hashed passwords, role checks, JSON mutation checks, AST validation, ERP/function allowlists, read-only transactions and timeouts.', 'Partially Implemented', 'Local demo deployment; no MFA, login throttling, public hosting hardening. An optional independent read-only database role is configured locally.'),
('Synthetic Dataset Realism', 'Synthetic data differs from production ERP.', 'Index selectivity may be unrepresentative.', 'Seeded relational generator, decimal amounts, varied dates/categories/statuses, reserved synthetic email domains.', 'Partially Implemented', 'Production distributions and double-entry accounting are not modelled.'),
('Benchmark Reliability', 'Caching and small timing differences distort gains.', 'Misleading improvement claims.', 'Same snapshot and locked data, equal warm-ups, repeated EXPLAIN ANALYZE, result multiset hashes, honest regressions and existing-index labels.', 'Implemented', 'Row ordering is ignored in equivalence checks. Shared caches are not flushed; external system load still varies.'),
('Scalability and Concurrent Users', 'Many requests exhaust connections.', 'Latency and timeouts under load.', 'Bounded pool, server pagination and query timeouts; benchmark lock timeout.', 'Partially Implemented', 'Development Flask server; production-scale concurrency and load limits untested.'),
('Limited Predictive Capabilities', 'Past measurements do not predict future bottlenecks.', 'Growth-related slowdowns can be missed.', 'Persisted measurements, trend charts and configurable slow-query threshold.', 'Partially Implemented', 'Predictive analytics and machine learning are unavailable.'),
]

class LimitationsService:
    @classmethod
    def get_all_limitations(cls, status_filter='all'):
        items = [dict(id=i+1, name=row[0], problem=row[1], impact=row[2], solution=row[3], status=row[4], remaining_work=row[5],
                      test_evidence='See docs/verification.md and tests/ for executed checks and their scope.') for i, row in enumerate(ITEMS)]
        statuses = {'implemented': 'Implemented', 'partially_implemented': 'Partially Implemented', 'planned': 'Planned', 'blocked': 'Blocked'}
        allowed = ['all'] + list(statuses.values())
        if status_filter not in allowed:
            raise ValueError('Unknown limitation status.')
        counts = {k: sum(i['status'] == value for i in items) for k, value in statuses.items()}
        return {'success': True, 'limitations': [i for i in items if status_filter == 'all' or i['status'] == status_filter], 'counts': {'total': len(items), **counts}}
