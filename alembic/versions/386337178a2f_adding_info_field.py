"""Adding info field

Revision ID: 386337178a2f
Revises: 51f3b3b5cd5d
Create Date: 2015-12-04 13:07:40.828736

"""

# revision identifiers, used by Alembic.
revision = '386337178a2f'
down_revision = '51f3b3b5cd5d'

from alembic import op
import sqlalchemy as sa

                               
def upgrade():
    op.add_column('users', sa.Column('info', sa.Text))    


def downgrade():
    op.drop_column('users', 'info')
