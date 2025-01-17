"""initial migration

Revision ID: c16d792bf227
Revises: 775de6b84ddf
Create Date: 2024-04-22 14:43:19.309492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c16d792bf227'
down_revision: Union[str, None] = '775de6b84ddf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('lol', sa.String(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'lol')
    # ### end Alembic commands ###
