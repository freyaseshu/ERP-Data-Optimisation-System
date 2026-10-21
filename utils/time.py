from datetime import datetime, timezone

def utc_now():
    """UTC stored in the project's PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
