"""add user_follows table

Revision ID: b33de7fbf839
Revises: 25e67424db01
Create Date: 2025-05-25 02:22:25.458151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b33de7fbf839'
down_revision: Union[str, None] = '25e67424db01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_follows',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('follower_id', sa.UUID(), nullable=False),
    sa.Column('followed_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['followed_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['follower_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('follower_id', 'followed_id', name='uq_follower_followed')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_follows')
    # ### end Alembic commands ###
