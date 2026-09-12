"""Establish the initial database migration baseline.

Revision ID: 0001_initial_baseline
Revises:
Create Date: 2026-09-12
"""

revision = "0001_initial_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the baseline revision without application tables.

    Domain schemas are introduced in later gates after their contracts are frozen.
    """
    pass


def downgrade() -> None:
    """Remove the baseline revision marker."""
    pass
