"""update role name '划分成员' to '项目经理'

Revision ID: e4a7b2c8d9f0
Revises: 9f5d213c162c
Create Date: 2026-07-10 09:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a7b2c8d9f0'
down_revision: Union[str, Sequence[str], None] = '9f5d213c162c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update existing user roles from '划分成员' to '项目经理'."""
    op.execute("UPDATE users SET role = '项目经理' WHERE role = '划分成员'")


def downgrade() -> None:
    """Revert role names back."""
    op.execute("UPDATE users SET role = '划分成员' WHERE role = '项目经理'")
