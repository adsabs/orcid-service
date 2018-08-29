"""Create profile table

Revision ID: 07c3fe07309c
Revises: 386337178a2f
Create Date: 2018-08-24 16:52:50.938617

"""

# revision identifiers, used by Alembic.
revision = '07c3fe07309c'
down_revision = '386337178a2f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import datetime


def upgrade():
    #with app.app_context() as c:
    #   db.session.add(Model())
    #   db.session.commit()

    op.create_table('profile',
                    sa.Column('orcid_id', sa.String(length=255), nullable=False),
                    sa.Column('created', sa.DateTime(), nullable=True, default=datetime.datetime.utcnow),
                    sa.Column('updated', sa.DateTime(), nullable=True, default=datetime.datetime.utcnow),
                    sa.Column('bibcode', postgresql.JSON(), nullable=True),
                    sa.PrimaryKeyConstraint('orcid_id')
                    )


def downgrade():
    op.drop_table('profile')
