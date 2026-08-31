"""Establish the IP-SAKTI application schema.

Revision ID: 20260831_01
Revises:
"""

from alembic import op

import models  # noqa: F401
from database import Base

revision = "20260831_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # checkfirst keeps this baseline safe for pre-Alembic pilot databases.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Destructive downgrade is intentionally disabled for evidence/audit preservation.
    pass
