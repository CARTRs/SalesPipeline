"""add role_conflicts and timeline_analysis to ai_analysis_results

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'g2h3i4j5k6l7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role_conflicts and timeline_analysis columns to ai_analysis_results
    op.add_column('ai_analysis_results', sa.Column('role_conflicts', postgresql.JSONB(), comment='角色信息冲突列表'))
    op.add_column('ai_analysis_results', sa.Column('timeline_analysis', sa.Text(), comment='时间线分析'))


def downgrade() -> None:
    # Remove columns
    op.drop_column('ai_analysis_results', 'timeline_analysis')
    op.drop_column('ai_analysis_results', 'role_conflicts')
