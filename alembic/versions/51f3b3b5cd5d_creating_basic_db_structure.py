"""Creating basic DB structure

Revision ID: 51f3b3b5cd5d
Revises: None
Create Date: 2015-13-09 20:13:58.241566

"""

# revision identifiers, used by Alembic.
revision = '51f3b3b5cd5d'
down_revision = None

from alembic import op
import sqlalchemy as sa
import datetime

from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Date
from sqlalchemy_utils import URLType


def upgrade():
    op.create_table('users',
        sa.Column('orcid_id', sa.String(length=255), nullable=False),
        sa.Column('access_token', sa.String(length=255), nullable=True),
        sa.Column('created', sa.DateTime(), nullable=True, default=datetime.datetime.utcnow),
        sa.Column('updated', sa.DateTime(), nullable=True, default=datetime.datetime.utcnow),
        sa.Column('profile', sa.LargeBinary, nullable=True),
        sa.PrimaryKeyConstraint('orcid_id')
    )    

def downgrade():
    op.drop_table('users')