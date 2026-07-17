"""0003_skill_daily

Revision ID: 95d3cc814e0a
Revises: 2e8fd90d43a4
Create Date: 2026-07-17 16:44:53.095851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95d3cc814e0a'
down_revision: Union[str, Sequence[str], None] = '2e8fd90d43a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
