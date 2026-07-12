"""add dingtalk_logs table and make users.phone required

Revision ID: f1a2b3c4d5e6
Revises: e4a7b2c8d9f0
Create Date: 2026-07-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e4a7b2c8d9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create dingtalk_logs table and make users.phone required."""
    # 1. Create dingtalk_logs table
    op.create_table('dingtalk_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=True, comment='关联商机'),
        sa.Column('recipient_ids', sa.String(length=500), nullable=True, comment='收件人ID（逗号分隔）'),
        sa.Column('msg_type', sa.String(length=20), nullable=False, comment='消息类型'),
        sa.Column('title', sa.String(length=300), nullable=True, comment='消息标题'),
        sa.Column('content', sa.Text(), nullable=True, comment='消息内容（Markdown）'),
        sa.Column('at_mobiles', sa.Text(), nullable=True, comment='的手机号列表（JSON数组）'),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=True, comment='状态：pending/sent/failed'),
        sa.Column('sent_at', sa.DateTime(), nullable=True, comment='发送时间'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='失败原因'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dingtalk_logs_opportunity_id', 'dingtalk_logs', ['opportunity_id'])
    op.create_index('ix_dingtalk_logs_status', 'dingtalk_logs', ['status'])

    # 2. Make users.phone required
    # First, set empty phone numbers to a placeholder to avoid constraint violation
    op.execute("UPDATE users SET phone = 'unknown' WHERE phone IS NULL OR phone = ''")
    # Then alter the column to not nullable
    op.alter_column('users', 'phone', nullable=False, comment='手机号（用于钉钉@）')


def downgrade() -> None:
    """Drop dingtalk_logs table and make users.phone optional again."""
    op.alter_column('users', 'phone', nullable=True, comment='手机号')
    op.drop_index('ix_dingtalk_logs_status')
    op.drop_index('ix_dingtalk_logs_opportunity_id')
    op.drop_table('dingtalk_logs')
