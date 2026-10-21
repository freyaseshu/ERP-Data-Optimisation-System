# Recorded verification evidence

These files are the outputs from the repair verification run documented in ../verification.md.

- test-results.xml: 115 tests, no failures/errors/skips.
- dataset-validation.json: actual demo row counts and integrity checks.
- recorded-benchmarks.json: actual recorded measurements, plans, variation and index-creation flags. Existing-index reruns are retained, including regressions.

The dataset is synthetic. No credentials, local database files, virtual environment or PostgreSQL binaries are included. These are historical verification results; rerun the tests and benchmarks to measure another environment.
