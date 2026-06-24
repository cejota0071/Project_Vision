"""Namespace bridge package.

The actual application modules live directly under this folder (config.py,
database.py, models.py, schemas.py, auth.py, router_auth.py, etc.).

This package exists so imports like `from backend.config import settings`
resolve correctly during local dev and in containers (Railway).
"""

